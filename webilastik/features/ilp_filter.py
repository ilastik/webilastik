from abc import abstractmethod
from typing import Optional, Literal


from ndstructs.array5D import Array5D
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonFloat, ensureJsonObject, ensureJsonString

from webilastik.datasource import DataRoi, DataSource
from webilastik.features.channelwise_fastfilters import (
    Axis2D, ChannelwiseFastFilter, DifferenceOfGaussians, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues,
    LaplacianOfGaussian, PresmoothedFilter, StructureTensorEigenvalues, get_axis_2d
)
from .feature_extractor import FeatureData, JsonableFeatureExtractor
from webilastik.operator import Operator, OpRetriever
from webilastik.server.message_schema import IlpFeatureExtractorMessage

IlpFilterName = Literal[
    "Gaussian Smoothing",
    "Laplacian of Gaussian",
    "Gaussian Gradient Magnitude",
    "Difference of Gaussians",
    "Structure Tensor Eigenvalues",
    "Hessian of Gaussian Eigenvalues"
]

class IlpFilter(PresmoothedFilter):
    def to_message(self) -> IlpFeatureExtractorMessage:
        return IlpFeatureExtractorMessage(
            ilp_scale=self.ilp_scale,
            axis_2d=self.axis_2d,
            class_name=self.ilp_name(),
        )

    def is_applicable_to(self, datasource: DataSource) -> bool:
        return self.op.is_applicable_to(datasource)

    @property
    def channel_multiplier(self) -> int:
        return self.op.channel_multiplier

    @classmethod
    def from_message(cls, value: IlpFeatureExtractorMessage) -> "IlpFilter":
        class_name = value.class_name

        if class_name == IlpGaussianSmoothing.ilp_name():
            return IlpGaussianSmoothing(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpLaplacianOfGaussian.ilp_name():
            return IlpLaplacianOfGaussian(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpGaussianGradientMagnitude.ilp_name():
            return IlpGaussianGradientMagnitude(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpDifferenceOfGaussians.ilp_name():
            return IlpDifferenceOfGaussians(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpStructureTensorEigenvalues.ilp_name():
            return IlpStructureTensorEigenvalues(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        if class_name == IlpHessianOfGaussianEigenvalues.ilp_name():
            return IlpHessianOfGaussianEigenvalues(ilp_scale=value.ilp_scale, axis_2d=value.axis_2d)
        raise Exception(f"Bad class_name for IlpFilter: {class_name}")

    @property
    @abstractmethod
    def op(self) -> ChannelwiseFastFilter:
        pass

    @classmethod
    @abstractmethod
    def ilp_name(cls) -> IlpFilterName:
        pass

    def __call__(self, /, roi: DataRoi) -> FeatureData:
        return self.op(roi)

class IlpGaussianSmoothing(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = GaussianSmoothing(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Gaussian Smoothing"]:
        return "Gaussian Smoothing"

    @property
    def op(self) -> GaussianSmoothing:
        return self._op

class IlpLaplacianOfGaussian(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = LaplacianOfGaussian(
            preprocessor=self.presmoother,
            scale=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Laplacian of Gaussian"]:
        return "Laplacian of Gaussian"

    @property
    def op(self) -> LaplacianOfGaussian:
        return self._op

class IlpGaussianGradientMagnitude(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        self._op = GaussianGradientMagnitude(
            preprocessor=self.presmoother,
            sigma=min(ilp_scale, 1.0),
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Gaussian Gradient Magnitude"]:
        return "Gaussian Gradient Magnitude"

    @property
    def op(self) -> GaussianGradientMagnitude:
        return self._op

class IlpDifferenceOfGaussians(IlpFilter):
    def __init__(
        self, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, axis_2d=axis_2d, preprocessor=preprocessor)
        capped_scale = min(ilp_scale, 1.0)
        self._op = DifferenceOfGaussians(
            preprocessor=self.presmoother,
            sigma0=capped_scale,
            sigma1=capped_scale * 0.66,
            axis_2d=axis_2d,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Difference of Gaussians"]:
        return "Difference of Gaussians"

    @property
    def op(self) -> DifferenceOfGaussians:
        return self._op

class IlpStructureTensorEigenvalues(IlpFilter):
    def __init__(
        self, *, ilp_scale: float, axis_2d: Optional[Axis2D], preprocessor: Operator[DataRoi, Array5D] = OpRetriever(axiskeys_hint="ctzyx")
    ):
        super().__init__(ilp_scale=ilp_scale, preprocessor=preprocessor, axis_2d=axis_2d)
        capped_scale = min(ilp_scale, 1.0)
        self._op = StructureTensorEigenvalues(
            innerScale=capped_scale,
            outerScale=0.5 * capped_scale,
            axis_2d=axis_2d,
            preprocessor=self.presmoother,
        )

    @classmethod
    def ilp_name(cls) -> Literal["Structure Tensor Eigenvalues"]:
        return "Structure Tensor Eigenvalues"

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

    @classmethod
    def ilp_name(cls) -> Literal["Hessian of Gaussian Eigenvalues"]:
        return "Hessian of Gaussian Eigenvalues"

    @property
    def op(self) -> HessianOfGaussianEigenvalues:
        return self._op