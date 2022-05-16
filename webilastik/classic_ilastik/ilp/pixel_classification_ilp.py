from pathlib import Path
from typing import Mapping, Optional, Sequence, Any, Dict, List
from datetime import datetime
import textwrap
import pickle
import h5py

import numpy as np
import vigra
from numpy import ndarray, dtype, int64
from vigra.vigranumpycore import AxisTags
from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D, Shape5D
from vigra.learning import RandomForest as VigraRandomForest

from webilastik.annotations.annotation import Color
from webilastik.classic_ilastik.ilp import IlpAttrDataset, IlpDatasetInfo, IlpFeatureSelectionsGroup, IlpGroup, IlpInputDataGroup, IlpLane, IlpParsingError, IlpProject, IlpValue, ensure_bytes, ensure_color_list, ensure_dataset, ensure_encoded_string, ensure_encoded_string_list, ensure_group, ensure_int, ensure_ndarray
from webilastik.features.ilp_filter import IlpFilter
from webilastik.datasource import DataSource, FsDataSource
from webilastik.annotations import Annotation
from webilastik.classifiers.pixel_classifier import VigraForestH5Bytes, VigraPixelClassifier, dump_to_temp_file, h5_bytes_to_vigra_forest, vigra_forest_to_h5_bytes
from webilastik.filesystem import JsonableFilesystem
from webilastik.utility.url import Protocol


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
    def __init__(
        self,
        *,
        annotations: Sequence[Annotation],
        classifier: Optional[VigraPixelClassifier[IlpFilter]],
    ) -> None:
        self.annotations = annotations
        self.classifier = classifier

        if not all(isinstance(a.raw_data, FsDataSource) for a in annotations):
            # FIXME: autocontext?
            raise ValueError(f"For now, all annotations must be on datasources present in the fylesystem in order to be saved")
        super().__init__()

    def populate_group(self, group: h5py.Group):
        if self.classifier:
            color_map = self.classifier.color_map
        else:
            color_map = Color.create_color_map([ # default ilastik labels: yellow and blue
                Color(r=np.uint8(255), g=np.uint8(255), b=np.uint8(25)),
                Color(r=np.uint8(0), g=np.uint8(130), b=np.uint8(200))
            ])

        LabelColors: "ndarray[Any, dtype[int64]]"  = np.asarray([color.rgba[:-1] for color in color_map.keys()], dtype=int64)

        # expected group keys to look like this:
        # ['Bookmarks', 'ClassifierFactory', 'LabelColors', 'LabelNames', 'PmapColors', 'StorageVersion', 'LabelSets', 'ClassifierForests']>
        bookmark = group.create_group("Bookmarks").create_dataset("0000", data=np.void(pickle.dumps([], 0))) # empty value is [], serialized with SerialPickleableSlot
        bookmark.attrs["version"] = 1
        group["ClassifierFactory"] = VIGRA_ILP_CLASSIFIER_FACTORY
        group["LabelColors"] = LabelColors
        group["LabelColors"].attrs["isEmpty"] = False
        group["LabelNames"] = np.asarray([color.name.encode("utf8") for color in color_map.keys()])
        group["LabelNames"].attrs["isEmpty"] = False
        group["PmapColors"] = LabelColors
        group["PmapColors"].attrs["isEmpty"] = False
        group["StorageVersion"] = "0.1".encode("utf8")

        merged_annotation_tiles: Dict[DataSource, Dict[Interval5D, Array5D]] = {}
        for annotation in self.annotations:
            datasource = annotation.raw_data
            merged_tiles = merged_annotation_tiles.setdefault(datasource, {})

            for interval in annotation.interval.get_tiles(tile_shape=datasource.tile_shape, tiles_origin=datasource.interval.start):
                annotation_tile = annotation.cut(interval.clamped(annotation.interval))
                tile = merged_tiles.setdefault(interval, Array5D.allocate(interval=interval, value=0, dtype=np.dtype("uint8")))
                tile.set(annotation_tile.colored(color_map[annotation.color]), mask_value=0)

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
            get_feature_extractor_order = lambda ex: IlpFeatureSelectionsGroup.feature_classes.index(ex.__class__)
            for fe in sorted(self.classifier.feature_extractors, key=get_feature_extractor_order):
                for c in range(self.classifier.num_input_channels * fe.channel_multiplier):
                    feature_names.append(fe.to_ilp_classifier_feature_entry(c).encode("utf8"))

            for forest_index, forest_bytes in enumerate(self.classifier.forest_h5_bytes):
                forests_h5_path = dump_to_temp_file(forest_bytes)
                with h5py.File(forests_h5_path, "r") as f:
                    forest_group = f["/"]
                    assert isinstance(forest_group, h5py.Group)
                    ClassifierForests.copy(forest_group, f"Forest{forest_index:04}") # 'Forest0000', ..., 'Forest000N'

            ClassifierForests["feature_names"] = np.asarray(feature_names)
            ClassifierForests["known_labels"] = np.asarray(self.classifier.classes).astype(np.uint32)
            ClassifierForests["pickled_type"] = b"clazyflow.classifiers.parallelVigraRfLazyflowClassifier\nParallelVigraRfLazyflowClassifier\np0\n."

    @classmethod
    def parse(cls, group: h5py.Group, raw_data_sources: Mapping[int, "FsDataSource | None"]) -> "IlpPixelClassificationGroup":
        annotations: List[Annotation] = []
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

                blockSlice = block.attrs.get("blockSlice")
                if not isinstance(blockSlice, str):
                    raise IlpParsingError(f"Expected 'blockSlice'' to be a str, found {blockSlice}")
                blockSpans: Sequence[List[str]] = [span_str.split(":") for span_str in blockSlice.split(",")]
                blockInterval = Interval5D.zero(**{
                    key: (int(span[0]), int(span[1]))
                    for key, span in zip(axiskeys, blockSpans)
                })

                block_5d = Array5D(block_data, axiskeys=axiskeys)
                for color_5d in block_5d.unique_colors().split(shape=Shape5D(x=1, c=block_5d.shape.c)):
                    raw_color = color_5d.raw("c")
                    annotation = Annotation(
                        block_5d.color_filtered(color=color_5d).raw(axiskeys),
                        location=blockInterval.start,
                        axiskeys=axiskeys, # FIXME: what if the user changed the axiskeys in the data source?
                        raw_data=raw_data,
                        color=Color(r=np.uint8(raw_color[0]), g=np.uint8(raw_color[1]), b=np.uint8(raw_color[2])),
                    )
                    annotations.append(annotation)

        LabelColors = ensure_color_list(group, "LabelColors")
        color_map = Color.create_color_map(LabelColors)

        ClassifierFactory = ensure_bytes(group, "ClassifierFactory")
        if ClassifierFactory != VIGRA_ILP_CLASSIFIER_FACTORY:
            raise IlpParsingError(f"Expecting ClassifierFactory to be pickled ParallelVigraRfLazyflowClassifierFactory, found {ClassifierFactory}")
        ClassifierForests = ensure_group(group, "ClassifierForests")
        forests: List[VigraRandomForest] = []
        for forest_key in sorted(ClassifierForests.keys()):
            if not forest_key.startswith("Forest"):
                continue
            forest_bytes = ensure_bytes(ClassifierForests, forest_key)
            forest = h5_bytes_to_vigra_forest(h5_bytes=VigraForestH5Bytes(forest_bytes))
            forests.append(forest)

        feature_names = ensure_encoded_string_list(ClassifierForests, "feature_names")
        feature_extractors_result = IlpFilter.from_ilp_classifier_feature_entries(feature_names)
        if isinstance(feature_extractors_result, Exception):
            raise IlpParsingError(str(feature_extractors_result))

        # FIXME: make feature extractors aware of which channel they handle
        num_input_channels = max(int(fn.split()[-1][1:-1]) for fn in feature_names) + 1

        classifier = VigraPixelClassifier(
            feature_extractors=feature_extractors_result,
            forest_h5_bytes=[vigra_forest_to_h5_bytes(forest) for forest in forests],
            color_map=color_map,
            classes=list(color_map.values()),
            num_input_channels=num_input_channels,
        )

        return IlpPixelClassificationGroup(annotations=annotations, classifier=classifier)


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
        annotations: Sequence[Annotation],
        classifier: "VigraPixelClassifier[IlpFilter] | None",
        currentApplet: "int | None" = None,
        ilastikVersion: "str | None" = None,
        time: "datetime | None" = None,
    ):
        datasources = {a.raw_data for a in annotations} #FIXME
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
                annotations=annotations,
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
        ilp_fs: JsonableFilesystem,
        ilp_path: Path,
        allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
    ) -> "IlpPixelClassificationWorkflowGroup | ValueError":
        workflowname = ensure_encoded_string(group, "workflowName")
        if workflowname != "Pixel Classification":
            raise IlpParsingError(f"Unexpected workflow name: {workflowname}")

        Input_Data = IlpInputDataGroup.parse(ensure_group(group, "Input Data"))
        raw_data_datasources_result = Input_Data.try_to_datasources(
            role_name="Raw Data", ilp_fs=ilp_fs, ilp_path=ilp_path, allowed_protocols=allowed_protocols
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