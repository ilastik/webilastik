from abc import abstractmethod
from typing import Optional


from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonFloat, ensureJsonObject, ensureJsonString

from webilastik.datasource import DataRoi, DataSource
from webilastik.features.channelwise_fastfilters import (
    Axis2D, ChannelwiseFastFilter, DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues,
    LaplacianOfGaussian, PresmoothedFilter, StructureTensorEigenvalues, get_axis_2d
)
from .feature_extractor import FeatureData, JsonableFeatureExtractor
from webilastik.operator import Operator, OpRetriever


class IlpFilter(PresmoothedFilter, JsonableFeatureExtractor):
    def to_json_value(self) -> JsonObject:
        return {
            "ilp_scale": self.ilp_scale,
            "axis_2d": self.axis_2d,
            "__class__": self.__class__.__name__,
        }

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return self.op.is_applicable_to(datasource)

    @property
    def channel_multiplier(self) -> int:
        return self.op.channel_multiplier

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "IlpFilter":
        value_obj = ensureJsonObject(value)
        class_name = ensureJsonString(value_obj.get("__class__"))
        ilp_scale = ensureJsonFloat(value_obj.get("ilp_scale"))
        axis_2d = get_axis_2d(value_obj.get("axis_2d"))

        if class_name == IlpGaussianSmoothing.__name__:
            return IlpGaussianSmoothing(ilp_scale=ilp_scale, axis_2d=axis_2d)
        if class_name == IlpLaplacianOfGaussian.__name__:
            return IlpLaplacianOfGaussian(ilp_scale=ilp_scale, axis_2d=axis_2d)
        if class_name == IlpGaussianGradientMagnitude.__name__:
            return IlpGaussianGradientMagnitude(ilp_scale=ilp_scale, axis_2d=axis_2d)
        if class_name == IlpDifferenceOfGaussians.__name__:
            return IlpDifferenceOfGaussians(ilp_scale=ilp_scale, axis_2d=axis_2d)
        if class_name == IlpStructureTensorEigenvalues.__name__:
            return IlpStructureTensorEigenvalues(ilp_scale=ilp_scale, axis_2d=axis_2d)
        if class_name == IlpHessianOfGaussianEigenvalues.__name__:
            return IlpHessianOfGaussianEigenvalues(ilp_scale=ilp_scale, axis_2d=axis_2d)
        raise Exception(f"Bad __class__ name: {class_name}")

    @property
    @abstractmethod
    def op(self) -> ChannelwiseFastFilter:
        pass

    def __call__(self, /, roi: DataRoi) -> FeatureData:
        return self.op(roi)

class IlpGaussianSmoothing(IlpFilter):
    def __init__(self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever()):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = GaussianSmoothing(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @property
    def op(self) -> GaussianSmoothing:
        return self._op

class IlpLaplacianOfGaussian(IlpFilter):
    def __init__(self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever()):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = LaplacianOfGaussian(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @property
    def op(self) -> LaplacianOfGaussian:
        return self._op

class IlpGaussianGradientMagnitude(IlpFilter):
    def __init__(self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever()):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = GaussianGradientMagnitude(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @property
    def op(self) -> GaussianGradientMagnitude:
        return self._op

class IlpDifferenceOfGaussians(IlpFilter):
    def __init__(self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever()):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        capped_scale = min(ilp_scale, 1.0)
        self._op = DifferenceOfGaussians(
            preprocessor=self.presmoother,
            sigma0=capped_scale,
            sigma1=capped_scale * 0.66,
            axis_2d=axis_2d,
        )

    @property
    def op(self) -> DifferenceOfGaussians:
        return self._op

class IlpStructureTensorEigenvalues(IlpFilter):
    def __init__(
        self, *, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever()
    ):
        super().__init__(ilp_scale=ilp_scale, preprocessor=preprocessor, axis_2d=axis_2d)
        capped_scale = min(ilp_scale, 1.0)
        self._op = StructureTensorEigenvalues(
            innerScale=capped_scale,
            outerScale=0.5 * capped_scale,
            axis_2d=axis_2d,
            preprocessor=self.presmoother,
        )

    @property
    def op(self) -> StructureTensorEigenvalues:
        return self._op

class IlpHessianOfGaussianEigenvalues(IlpFilter):
    def __init__(self, ilp_scale: float, axis_2d: Optional[Axis2D]):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d)
        self._op = HessianOfGaussianEigenvalues(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @property
    def op(self) -> HessianOfGaussianEigenvalues:
        return self._op