from typing import Optional, Sequence, Any, Dict, List
from datetime import datetime
import textwrap
import pickle
import time

import numpy as np
import vigra
from numpy import ndarray, dtype, int64
from ndstructs.array5D import Array5D
from ndstructs.point5D import Interval5D
from webilastik.annotations.annotation import Color

from webilastik.classic_ilastik.ilp import IlpAttrDataset, IlpDataSource, IlpFeatureSelectionsGroup, IlpGroup, IlpInputDataGroup, IlpLane, IlpProject, IlpValue
from webilastik.features.ilp_filter import IlpFilter
from webilastik.datasource import DataSource, FsDataSource
from webilastik.annotations import Annotation
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier


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
        feature_extractors: Sequence[IlpFilter],
        annotations: Sequence[Annotation],
        classifier: Optional[VigraPixelClassifier[IlpFilter]],
    ) -> None:
        self.feature_extractors = feature_extractors
        self.annotations = annotations
        self.classifier = classifier

        if not all(isinstance(a.raw_data, FsDataSource) for a in annotations):
            # FIXME: autocontext?
            raise ValueError(f"For now, all annotations must be on datasources present in the fylesystem in order to be saved")

    def to_ilp_data(self) -> Dict[str, Any]:
        if self.classifier:
            color_map = self.classifier.color_map
        else:
            color_map = Color.create_color_map([ # default ilastik labels: yellow and blue
                Color(r=np.uint8(255), g=np.uint8(255), b=np.uint8(25)),
                Color(r=np.uint8(0), g=np.uint8(130), b=np.uint8(200))
            ])

        LabelColors: "ndarray[Any, dtype[int64]]"  = np.asarray([color.rgba[:-1] for color in color_map.keys()], dtype=int64)

        # expected group keys to look like this:
        # ['Bookmarks', 'ClassifierFactory', 'ClassifierForests', 'LabelColors', 'LabelNames', 'LabelSets', 'PmapColors', 'StorageVersion']>
        out: Dict[str, IlpValue] = {
            "Bookmarks": {
                "0000": np.void(pickle.dumps([], 0)) # empty value is [], serialized with SerialPickleableSlot
            },
            "ClassifierFactory": VIGRA_ILP_CLASSIFIER_FACTORY,
            # ClassifierForests set later
            "LabelColors": LabelColors,
            "LabelNames": np.asarray([color.name.encode("utf8") for color in color_map.keys()]),
            # LabelSets set later
            "PmapColors": LabelColors,
            "StorageVersion": "0.1",
        }

        if self.classifier:
            Forests: IlpGroup = self.classifier.to_ilp_forests() if self.classifier is not None else {}

            feature_names: List[bytes] = []
            get_feature_extractor_order = lambda ex: IlpFeatureSelectionsGroup.all_feature_names.index(ex.__class__.__name__)
            for fe in sorted(self.feature_extractors, key=get_feature_extractor_order):
                for c in range(self.classifier.num_input_channels * fe.channel_multiplier):
                    feature_names.append(fe.get_ilp_name(c).encode("utf8"))

            # ['Forest0000', ..., 'Forest000N', 'feature_names', 'known_labels', 'pickled_type']
            out["ClassifierForests"] = {
                **Forests,
                "feature_names": np.asarray(feature_names),
                "known_labels": np.asarray(self.classifier.classes).astype(np.uint32),
                "pickled_type": b"clazyflow.classifiers.parallelVigraRfLazyflowClassifier\nParallelVigraRfLazyflowClassifier\np0\n.",
            }

        merged_annotation_tiles: Dict[DataSource, Dict[Interval5D, Array5D]] = {}
        for annotation in self.annotations:
            datasource = annotation.raw_data
            merged_tiles = merged_annotation_tiles.setdefault(datasource, {})

            for interval in annotation.interval.get_tiles(tile_shape=datasource.tile_shape, tiles_origin=datasource.interval.start):
                annotation_tile = annotation.cut(interval.clamped(annotation.interval))
                tile = merged_tiles.setdefault(interval, Array5D.allocate(interval=interval, value=0, dtype=np.dtype("uint8")))
                tile.set(annotation_tile.colored(color_map[annotation.color]), mask_value=0)

        LabelSets: Dict[str, Dict[str, IlpAttrDataset]] = {"labels000": {}}  # empty labels still produce this in classic ilastik
        for lane_index, (lane_datasource, blocks) in enumerate(merged_annotation_tiles.items()):
            assert isinstance(lane_datasource, FsDataSource)
            axiskeys = lane_datasource.c_axiskeys_on_disk
            LabelSets[f"labels{lane_index:03}"] = {
                f"block{block_index:04d}": IlpAttrDataset(
                    block.raw(axiskeys),
                    attrs={
                        "blockSlice": "[" + ",".join(f"{slc.start}:{slc.stop}" for slc in block.interval.updated(c=0).to_slices(axiskeys)) + "]",
                        "axistags": vigra.defaultAxistags("xyz").toJSON()
                    },
                )
                for block_index, block in enumerate(blocks.values())
            }
        out["LabelSets"] = LabelSets

        return out


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
                    "Raw Data": IlpDataSource(datasource=ds)
                })
                for ds in datasources
                if isinstance(ds, FsDataSource) #FIXME
            ]),
            FeatureSelections=IlpFeatureSelectionsGroup(feature_extractors=feature_extractors),
            PixelClassification=IlpPixelClassificationGroup(
                feature_extractors=feature_extractors,
                annotations=annotations,
                classifier=classifier,
            ),
            currentApplet=currentApplet,
            ilastikVersion=ilastikVersion,
            time=time,
        )


    def to_ilp_data(self) -> IlpGroup:
        return {
            "Input Data": self.Input_Data.to_ilp_data(),
            "FeatureSelections": self.FeatureSelections.to_ilp_data(),
            "PixelClassification": self.PixelClassification.to_ilp_data(),
            "Prediction Export": {
                "OutputFilenameFormat": "{dataset_dir}/{nickname}_{result_type}",
                "OutputFormat": "hdf5",
                "OutputInternalPath": "exported_data",
                "StorageVersion": "0.1",
            },
            "currentApplet": 0,
            "ilastikVersion": b"1.3.2post1",  # FIXME
            "time": time.ctime().encode("utf-8"),  # FIXME
            "workflowName": b"Pixel Classification",
        }
