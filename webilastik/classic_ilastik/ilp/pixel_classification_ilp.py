# pyright: strict

from pathlib import Path, PurePosixPath
from typing import Callable, ClassVar, Mapping, Optional, Dict, Sequence, Any, List, Tuple, Type
from datetime import datetime
import textwrap
import pickle
import io

import h5py
import numpy as np
import vigra
from numpy import ndarray, dtype, int64
from vigra.vigranumpycore import AxisTags
from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Shape5D
from vigra.learning import RandomForest as VigraRandomForest

from webilastik.annotations.annotation import Color
from webilastik.classic_ilastik.ilp import (
    IlpDatasetInfo,
    IlpFeatureSelectionsGroup,
    IlpInputDataGroup,
    IlpLane,
    IlpParsingError,
    IlpProject,
    ensure_bytes,
    ensure_color_list,
    ensure_dataset,
    ensure_encoded_string,
    ensure_encoded_string_list,
    ensure_group, ensure_int
)
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians, IlpGaussianGradientMagnitude, IlpGaussianSmoothing,
    IlpHessianOfGaussianEigenvalues, IlpLaplacianOfGaussian, IlpStructureTensorEigenvalues,
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.datasource import DataSource, FsDataSource
from webilastik.annotations import Annotation
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier, dump_to_temp_file, vigra_forest_to_h5_bytes
from webilastik.filesystem import IFilesystem
from webilastik.libebrains.user_credentials import EbrainsUserCredentials

from webilastik.ui.applet.brushing_applet import Label

VIGRA_ILP_CLASSIFIER_FACTORY = textwrap.dedent(
        """
        ccopy_reg
        _reconstructor
        p0
        (clazyflow.classifiers.parallelVigraRfLazyflowClassifier
        ParallelVigraRfLazyflowClassifierFactory
        p1
        c__builtin__
        object
        p2
        Ntp3
        Rp4
        (dp5
        VVERSION
        p6
        I2
        sV_num_trees
        p7
        I100
        sV_label_proportion
        p8
        NsV_variable_importance_path
        p9
        NsV_variable_importance_enabled
        p10
        I00
        sV_kwargs
        p11
        (dp12
        sV_num_forests
        p13
        I8
        sb."""[
            1:
        ]
    ).encode("utf8")


class IlpPixelClassificationGroup:
    feature_name_to_class: ClassVar[Mapping[str, Type[IlpFilter]]] = {
        "Gaussian Smoothing": IlpGaussianSmoothing,
        "Laplacian of Gaussian": IlpLaplacianOfGaussian,
        "Gaussian Gradient Magnitude": IlpGaussianGradientMagnitude,
        "Difference of Gaussians": IlpDifferenceOfGaussians,
        "Structure Tensor Eigenvalues": IlpStructureTensorEigenvalues,
        "Hessian of Gaussian Eigenvalues": IlpHessianOfGaussianEigenvalues,
    }
    class_to_feature_name: ClassVar[Mapping[Type[IlpFilter], str]] = {v: k for k, v in feature_name_to_class.items()}
    feature_names: ClassVar[Sequence[str]] = list(feature_name_to_class.keys())
    feature_classes: ClassVar[Sequence[Type[IlpFilter]]] = list(feature_name_to_class.values())

    @classmethod
    def make_feature_ilp_name(cls, feature_extractor: IlpFilter, channel_index: int) -> str:
        name = f"{cls.class_to_feature_name[feature_extractor.__class__]} (σ={feature_extractor.ilp_scale})"
        name += " in 2D" if feature_extractor.axis_2d is not None else " in 3D"
        name += f" [{channel_index}]"
        return name

    @classmethod
    def ilp_filters_and_expected_num_channels_from_names(cls, feature_names: Sequence[str]) -> Tuple[Sequence[IlpFilter], int]:
        out: List[IlpFilter] = []

        expected_num_channels = 0
        for name in feature_names:
            parts = name.split()
            channel_index = int(parts[-1][1:-1]) # strip square brackets off of something like '[3]'
            in_2D = parts[-2] == "2D"
            ilp_scale = float(parts[-4][3:-1]) # read number from something like '(σ=0.3)'
            ilp_classifier_feature_name = " ".join(parts[:-4]) # drops the 4 last items, that look like '(σ=0.3) in 2D [0]'

            filter_class = cls.feature_name_to_class.get(ilp_classifier_feature_name)
            if filter_class is None:
                raise IlpParsingError(f"Bad ilp filter name: {ilp_classifier_feature_name}")
            ilp_filter = filter_class(
                ilp_scale=ilp_scale, axis_2d= "z" if in_2D else None # FIXME: is axis_2d always 'z'?
            )
            expected_num_channels = max(expected_num_channels, channel_index // ilp_filter.channel_multiplier)
            if len(out) == 0 or out[-1] != ilp_filter:
                out.append(ilp_filter)
        return (out, expected_num_channels)


    def __init__(
        self,
        *,
        classifier: Optional[VigraPixelClassifier[IlpFilter]],
        labels: Sequence[Label],
    ) -> None:
        self.classifier = classifier
        self.labels = labels

        if not all(isinstance(annotation.raw_data, FsDataSource) for label in labels for annotation in label.annotations):
            # FIXME: autocontext?
            raise ValueError(f"For now, all annotations must be on datasources present in the fylesystem in order to be saved")
        super().__init__()

    def populate_group(self, group: h5py.Group):
        LabelColors: "ndarray[Any, dtype[int64]]"  = np.asarray([label.color.rgba for label in self.labels], dtype=int64)

        # expected group keys to look like this:
        # ['Bookmarks', 'ClassifierFactory', 'LabelColors', 'LabelNames', 'PmapColors', 'StorageVersion', 'LabelSets', 'ClassifierForests']>
        bookmark = group.create_group("Bookmarks").create_dataset("0000", data=np.void(pickle.dumps([], 0))) # empty value is [], serialized with SerialPickleableSlot
        bookmark.attrs["version"] = 1
        group["ClassifierFactory"] = VIGRA_ILP_CLASSIFIER_FACTORY
        group["LabelColors"] = LabelColors
        group["LabelColors"].attrs["isEmpty"] = False
        group["LabelNames"] = [label.name.encode("utf8") for label in self.labels]
        group["LabelNames"].attrs["isEmpty"] = False
        group["PmapColors"] = LabelColors
        group["PmapColors"].attrs["isEmpty"] = False
        group["StorageVersion"] = "0.1".encode("utf8")

        merged_annotation_tiles: Dict[DataSource, Dict[Interval5D, Array5D]] = {}
        for label_class, label in enumerate(self.labels, start=1):
            for annotation in label.annotations:
                datasource = annotation.raw_data
                merged_tiles = merged_annotation_tiles.setdefault(datasource, {})

                for interval in annotation.interval.get_tiles(
                    tile_shape=datasource.tile_shape.updated(c=1), tiles_origin=datasource.interval.start.updated(c=0)
                ):
                    annotation_tile = annotation.cut(interval.clamped(annotation.interval))
                    tile = merged_tiles.setdefault(interval, Array5D.allocate(interval=interval, value=0, dtype=np.dtype("uint8")))
                    tile.set(annotation_tile.colored(np.uint8(label_class)), mask_value=0)

        LabelSets = group.create_group("LabelSets")
        for lane_index, (lane_datasource, blocks) in enumerate(merged_annotation_tiles.items()):
            assert isinstance(lane_datasource, FsDataSource) #FIXME? how do autocontext annotations work? They wouldn't be on FsDataSource
            axiskeys = lane_datasource.c_axiskeys_on_disk
            label_set = LabelSets.create_group(f"labels{lane_index:03}")
            for block_index, block in enumerate(blocks.values()):
                labels_dataset = label_set.create_dataset(f"block{block_index:04d}", data=block.raw(axiskeys))
                labels_dataset.attrs["blockSlice"] = "[" + ",".join(f"{slc.start}:{slc.stop}" for slc in block.interval.updated(c=0).to_slices(axiskeys)) + "]"
                labels_dataset.attrs["axistags"] = vigra.defaultAxistags(axiskeys).toJSON()
        if len(LabelSets.keys()) == 0:
            _ = LabelSets.create_group("labels000")  # empty labels still produce this in classic ilastik

        if self.classifier:
            # ['Forest0000', ..., 'Forest000N', 'feature_names', 'known_labels', 'pickled_type']
            ClassifierForests = group.create_group("ClassifierForests")

            feature_names: List[bytes] = []
            get_feature_extractor_order: Callable[[IlpFilter], int] = lambda ex: self.feature_classes.index(ex.__class__)
            for fe in sorted(self.classifier.feature_extractors, key=get_feature_extractor_order):
                for c in range(self.classifier.num_input_channels * fe.channel_multiplier):
                    feature_names.append(self.make_feature_ilp_name(fe, channel_index=c).encode("utf8"))

            for forest_index, forest_bytes in enumerate(self.classifier.forest_h5_bytes):
                forests_h5_path = dump_to_temp_file(forest_bytes)
                with h5py.File(forests_h5_path, "r") as f:
                    forest_group = f["/"]
                    assert isinstance(forest_group, h5py.Group)
                    ClassifierForests.copy(forest_group, f"Forest{forest_index:04}") # 'Forest0000', ..., 'Forest000N'

            ClassifierForests["feature_names"] = feature_names
            ClassifierForests["known_labels"] = np.asarray(self.classifier.classes).astype(np.uint32)
            ClassifierForests["pickled_type"] = b"clazyflow.classifiers.parallelVigraRfLazyflowClassifier\nParallelVigraRfLazyflowClassifier\np0\n."

    @classmethod
    def parse(cls, group: h5py.Group, raw_data_sources: Mapping[int, "FsDataSource | None"]) -> "IlpPixelClassificationGroup":
        LabelColors = ensure_color_list(group, "LabelColors")
        LabelNames = ensure_encoded_string_list(group, "LabelNames")
        class_to_color: Mapping[np.uint8, Color] = {np.uint8(i): color for i, color in enumerate(LabelColors, start=1)}

        label_classes: Dict[Color, Label] = {color: Label(name=name, color=color, annotations=[]) for name, color in zip(LabelNames, LabelColors)}
        LabelSets = ensure_group(group, "LabelSets")
        for lane_key in LabelSets.keys():
            if not lane_key.startswith("labels"):
                continue
            lane_index = int(lane_key.replace("labels", ""))
            lane_label_blocks = ensure_group(LabelSets, lane_key)
            if len(lane_label_blocks.keys()) == 0:
                continue
            raw_data = raw_data_sources.get(lane_index)
            if raw_data is None:
                raise IlpParsingError(f"No datasource for lane {lane_index:03d}")
            for block_name in lane_label_blocks.keys():
                if not block_name.startswith("block"):
                    continue
                block = ensure_dataset(lane_label_blocks, block_name)
                block_data = block[()]
                if not isinstance(block_data, np.ndarray):
                    raise IlpParsingError("Expected annotation block to contain a ndarray")

                raw_axistags = block.attrs.get("axistags")
                if not isinstance(raw_axistags, str):
                    raise IlpParsingError(f"Expected axistags to be a str, found {raw_axistags}")
                axistags = AxisTags.fromJSON(raw_axistags)
                axiskeys = "".join(axistags.keys())

                if "blockSlice" not in block.attrs:
                    raise IlpParsingError(f"Expected 'blockSlice' in attrs from {block.name}")
                blockSlice = block.attrs["blockSlice"]
                if not isinstance(blockSlice, str):
                    raise IlpParsingError(f"Expected 'blockSlice'' to be a str, found {blockSlice}")
                # import pydevd; pydevd.settrace()
                blockSpans: Sequence[List[str]] = [span_str.split(":") for span_str in blockSlice[1:-1].split(",")]
                blockInterval = Interval5D.zero(**{
                    key: (int(span[0]), int(span[1]))
                    for key, span in zip(axiskeys, blockSpans)
                })

                block_5d = Array5D(block_data, axiskeys=axiskeys)
                for color_5d in block_5d.unique_colors().split(shape=Shape5D(x=1, c=block_5d.shape.c)):
                    color_index = np.uint8(color_5d.raw("c")[0])
                    if color_index == np.uint8(0): # background
                        continue
                    color = class_to_color.get(color_index)
                    if color is None:
                        raise IlpParsingError(f"Could not find a label color for index {color_index}")
                    annotation_data: "np.ndarray[Any, np.dtype[np.uint8]]" = block_5d.color_filtered(color=color_5d).raw(axiskeys)
                    annotation_data_5d: Array5D = Array5D(
                        annotation_data.astype(np.dtype(bool)),
                        location=blockInterval.start,
                        axiskeys=axiskeys, # FIXME: what if the user changed the axiskeys in the data source?
                    ).contracted_to_non_zero()
                    annotation = Annotation(
                        annotation_data_5d.raw(annotation_data_5d.axiskeys),
                        location=annotation_data_5d.location,
                        axiskeys=annotation_data_5d.axiskeys,
                        raw_data=raw_data,
                    )

                    label_classes[color].annotations.append(annotation)



        ClassifierFactory = ensure_bytes(group, "ClassifierFactory")
        if ClassifierFactory != VIGRA_ILP_CLASSIFIER_FACTORY:
            raise IlpParsingError(f"Expecting ClassifierFactory to be pickled ParallelVigraRfLazyflowClassifierFactory, found {ClassifierFactory}")
        if "ClassifierForests" in group:
            ClassifierForests = ensure_group(group, "ClassifierForests")
            forests: List[VigraRandomForest] = []
            for forest_key in sorted(ClassifierForests.keys()):
                if not forest_key.startswith("Forest"):
                    continue
                forest = VigraRandomForest(group.file.filename, f"{ClassifierForests.name}/{forest_key}")
                # forest_bytes = ensure_bytes(ClassifierForests, forest_key)
                # forest = h5_bytes_to_vigra_forest(h5_bytes=VigraForestH5Bytes(forest_bytes))
                forests.append(forest)

            feature_names = ensure_encoded_string_list(ClassifierForests, "feature_names")
            feature_extractors, expected_num_channels = cls.ilp_filters_and_expected_num_channels_from_names(feature_names)

            classifier = VigraPixelClassifier(
                feature_extractors=feature_extractors,
                forest_h5_bytes=[vigra_forest_to_h5_bytes(forest) for forest in forests],
                num_classes=len([label for label in label_classes.values() if not label.is_empty()]),
                num_input_channels=expected_num_channels,
            )
        else:
            classifier = None

        return IlpPixelClassificationGroup(
            classifier=classifier,
            labels=list(label_classes.values()),
        )


class IlpPixelClassificationWorkflowGroup(IlpProject):
    def __init__(
        self,
        *,
        Input_Data: IlpInputDataGroup,
        FeatureSelections: IlpFeatureSelectionsGroup,
        PixelClassification: IlpPixelClassificationGroup,
        currentApplet: "int | None" = None,
        ilastikVersion: "str | None" = None,
        time: "datetime | None" = None,
    ):
        super().__init__(
            workflowName="Pixel Classification", currentApplet=currentApplet, ilastikVersion=ilastikVersion, time=time
        )
        self.Input_Data = Input_Data
        self.FeatureSelections = FeatureSelections
        self.PixelClassification = PixelClassification

    @staticmethod
    def create(
        *,
        feature_extractors: Sequence[IlpFilter],
        labels: Sequence[Label],
        classifier: "VigraPixelClassifier[IlpFilter] | None",
        currentApplet: "int | None" = None,
        ilastikVersion: "str | None" = None,
        time: "datetime | None" = None,
    ):
        datasources = {annotation.raw_data for label in labels for annotation in label.annotations}
        return IlpPixelClassificationWorkflowGroup(
            Input_Data = IlpInputDataGroup(lanes=[
                IlpLane(roles={
                    "Raw Data": IlpDatasetInfo.from_datasource(datasource=ds),
                    "Prediction Mask": None
                })
                for ds in datasources
                if isinstance(ds, FsDataSource) #FIXME
            ]),
            FeatureSelections=IlpFeatureSelectionsGroup(feature_extractors=feature_extractors),
            PixelClassification=IlpPixelClassificationGroup(
                labels=labels,
                classifier=classifier,
            ),
            currentApplet=currentApplet,
            ilastikVersion=ilastikVersion,
            time=time,
        )

    def populate_group(self, group: h5py.Group):
        super().populate_group(group)
        self.Input_Data.populate_group(group.create_group("Input Data"))
        self.FeatureSelections.populate_group(group.create_group("FeatureSelections"))
        self.PixelClassification.populate_group(group.create_group("PixelClassification"))

        Prediction_Export = group.create_group("Prediction Export")
        Prediction_Export["OutputFilenameFormat"] = "{dataset_dir}/{nickname}_{result_type}".encode("utf8")
        Prediction_Export["OutputFormat"] = "hdf5".encode("utf8")
        Prediction_Export["OutputInternalPath"] = "exported_data".encode("utf8")
        Prediction_Export["StorageVersion"] = "0.1".encode("utf8")

    @classmethod
    def parse(
        cls,
        group: h5py.Group,
        ilp_fs: IFilesystem,
        ebrains_user_credentials: Optional[EbrainsUserCredentials]
    ) -> "IlpPixelClassificationWorkflowGroup | Exception":
        workflowname = ensure_encoded_string(group, "workflowName")
        if workflowname != "Pixel Classification":
            raise IlpParsingError(f"Unexpected workflow name: {workflowname}")

        Input_Data = IlpInputDataGroup.parse(ensure_group(group, "Input Data"))
        raw_data_datasources_result = Input_Data.try_to_datasources(
            role_name="Raw Data",
            ilp_fs=ilp_fs,
            ilp_path=PurePosixPath(Path(group.file.filename).absolute()), #FIXME: will this work on windows? Probably not
            ebrains_user_credentials=ebrains_user_credentials,
        )
        if isinstance(raw_data_datasources_result, Exception):
            return raw_data_datasources_result

        PixelClassification = IlpPixelClassificationGroup.parse(
            group=ensure_group(group, "PixelClassification"),
            raw_data_sources=raw_data_datasources_result,
        )

        return IlpPixelClassificationWorkflowGroup(
            Input_Data=Input_Data,
            FeatureSelections=IlpFeatureSelectionsGroup.parse(ensure_group(group, "FeatureSelections")),
            PixelClassification=PixelClassification,
            currentApplet=ensure_int(group, "currentApplet"),
            ilastikVersion=ensure_encoded_string(group, "ilastikVersion"),
            time=datetime.strptime(ensure_encoded_string(group, "time"), "%a %b %d %H:%M:%S %Y"),
        )

    def to_h5_file_bytes(self) -> bytes:
        backing_buffer = io.BytesIO()
        f = h5py.File(backing_buffer, "w")
        root_group = f["/"]
        assert isinstance(root_group, h5py.Group)
        self.populate_group(root_group)
        f.close()
        _ = backing_buffer.seek(0)
        return backing_buffer.read()
