from typing import Generic, Mapping, Optional, Sequence, Dict, Any, Iterator, Tuple, TypeVar
import textwrap

from webilastik.datasource import DataRoi
import numpy as np

from webilastik.ui.applet  import Applet, AppletOutput, PropagationOk, PropagationResult, UserPrompt, applet_output
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.annotations.annotation import Annotation, Color
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import Predictions, VigraPixelClassifier


DEFAULT_ILP_CLASSIFIER_FACTORY = textwrap.dedent(
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

Classifier = VigraPixelClassifier[IlpFilter]
ColorMap = Dict[Color, np.uint8]

class PixelClassificationApplet(Applet):
    def __init__(
        self,
        name: str,
        *,
        feature_extractors: AppletOutput[Sequence[IlpFilter]],
        annotations: AppletOutput[Sequence[Annotation]],
    ):
        self._in_feature_extractors = feature_extractors
        self._in_annotations = annotations
        self._pixel_classifier: Optional[Classifier] = None
        self._color_map: Optional[ColorMap] = None
        super().__init__(name=name)

    def take_snapshot(self) -> Tuple[Optional[Classifier], Optional[ColorMap]]:
        return (self._pixel_classifier, self._color_map)

    def restore_snaphot(self, snapshot: Tuple[Optional[Classifier], Optional[ColorMap]]) -> None:
        self._pixel_classifier = snapshot[0]
        self._color_map = snapshot[1]

    @applet_output
    def pixel_classifier(self) -> Optional[VigraPixelClassifier[IlpFilter]]:
        return self._pixel_classifier

    @applet_output
    def color_map(self) -> Optional[Dict[Color, np.uint8]]:
        return self._color_map

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        print(f"[DEBUG] Running refresh on pixel classification applet")
        annotations = self._in_annotations()
        feature_extractors = self._in_feature_extractors()
        if not annotations or not feature_extractors:
            self._pixel_classifier = None
            self._color_map = None
        else:
            self._pixel_classifier = VigraPixelClassifier[IlpFilter].train(
                annotations=annotations,
                feature_extractors=feature_extractors
            )
            self._color_map = Color.create_color_map([a.color for a in annotations])
            _ = self._pixel_classifier.__getstate__() #warm up pickle cache?
        return PropagationOk()




    # def get_ilp_classifier_feature_names(self) -> Iterator[bytes]:
    #     # FIXME: annotations can be empty!
    #     num_input_channels = self._in_annotations()[0].raw_data.shape.c #FIXME: all lanes always have same c?
    #     for fe in sorted(self._in_feature_extractors(), key=lambda ex: FeatureSelectionApplet.ilp_feature_names.index(ex.__class__.__name__)):
    #         for c in range(num_input_channels * fe.channel_multiplier):
    #             name_and_channel = fe.ilp_name + f" [{c}]"
    #             yield name_and_channel.encode("utf8")

    # def get_classifier_ilp_data(self) -> Mapping[str, Any]:
    #     classifier = self._pixel_classifier
    #     if classifier is None:
    #         return {} # FIXME
    #     out = classifier.get_forest_data()
    #     feature_names: Iterator[bytes] = self.get_ilp_classifier_feature_names()
    #     out["feature_names"] = np.asarray(list(feature_names))
    #     out[
    #         "pickled_type"
    #     ] = b"clazyflow.classifiers.parallelVigraRfLazyflowClassifier\nParallelVigraRfLazyflowClassifier\np0\n."
    #     out["known_labels"] = np.asarray(classifier.classes).astype(np.uint32)
    #     return out

    # @property
    # def ilp_data(self) -> Dict[str, Any]:
    #     out = {
    #         "Bookmarks": {"0000": []},
    #         "StorageVersion": "0.1",
    #         "ClassifierFactory": DEFAULT_ILP_CLASSIFIER_FACTORY,
    #     }
    #     classifier_forests = self.get_classifier_ilp_data()
    #     if classifier_forests:
    #         out["ClassifierForests"] = classifier_forests

    #     out["LabelSets"] = labelSets = {"labels000": {}}  # empty labels still produce this in classic ilastik
    #     color_map = self.color_map()
    #     datasources = {a.raw_data for a in self._in_annotations()} # FIXME: is order important?
    #     for lane_idx, datasource in enumerate(datasources):
    #         lane_annotations = [annot for annot in self._in_annotations() if annot.raw_data == datasource]
    #         label_data = Annotation.dump_as_ilp_data(lane_annotations, color_map=color_map)
    #         labelSets[f"labels{lane_idx:03d}"] = label_data
    #     out["LabelColors"] = np.asarray([color.rgba[:-1] for color in color_map.keys()], dtype=np.int64)
    #     out["PmapColors"] = out["LabelColors"]
    #     out["LabelNames"] = np.asarray([color.name.encode("utf8") for color in color_map.keys()])
    #     return out
