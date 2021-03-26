import Boost.Python
averagingKernel: Any
binomialKernel: Any
burtFilterKernel: Any
discreteGaussianKernel: Any
diskKernel2D: Any
explictKernel: Any
explictKernel2D: Any
gaussianDerivative: Any
gaussianDerivativeKernel: Any
gaussianKernel: Any
gaussianKernel2D: Any
hessianOfGaussianEigenvalues: Any
optimalFirstDerivative5Kernel: Any
optimalFirstDerivativeSmoothing3Kernel: Any
optimalFirstDerivativeSmoothing5Kernel: Any
optimalSecondDerivative5Kernel: Any
optimalSecondDerivativeSmoothing3Kernel: Any
optimalSecondDerivativeSmoothing5Kernel: Any
optimalSmoothing3Kernel: Any
optimalSmoothing5Kernel: Any
secondDifference3Kernel: Any
separableKernel2D: Any
structureTensorEigenvalues: Any
symmetricDifferenceKernel: Any

def boundaryDistanceTransform(*args, **kwargs) -> Any: ...
def boundaryTensor2D(*args, **kwargs) -> Any: ...
def boundaryVectorDistanceTransform(*args, **kwargs) -> Any: ...
def convolve(*args, **kwargs) -> Any: ...
def convolveOneDimension(*args, **kwargs) -> Any: ...
def discClosing(*args, **kwargs) -> Any: ...
def discDilation(*args, **kwargs) -> Any: ...
def discErosion(*args, **kwargs) -> Any: ...
def discMedian(*args, **kwargs) -> Any: ...
def discOpening(*args, **kwargs) -> Any: ...
def discRankOrderFilter(*args, **kwargs) -> Any: ...
def discRankOrderFilterWithMask(*args, **kwargs) -> Any: ...
def distanceTransform(*args, **kwargs) -> Any: ...
def distanceTransform2D(*args, **kwargs) -> Any: ...
def eccentricityCenters(*args, **kwargs) -> Any: ...
def eccentricityTransform(*args, **kwargs) -> Any: ...
def eccentricityTransformWithCenters(*args, **kwargs) -> Any: ...
def gaussianDivergence(*args, **kwargs) -> Any: ...
def gaussianGradient(*args, **kwargs) -> Any: ...
def gaussianGradientMagnitude(*args, **kwargs) -> Any: ...
def gaussianSharpening2D(*args, **kwargs) -> Any: ...
def gaussianSmoothing(*args, **kwargs) -> Any: ...
def hessianOfGaussian(*args, **kwargs) -> Any: ...
def hourGlassFilter2D(*args, **kwargs) -> Any: ...
def laplacianOfGaussian(*args, **kwargs) -> Any: ...
def multiBinaryClosing(*args, **kwargs) -> Any: ...
def multiBinaryDilation(*args, **kwargs) -> Any: ...
def multiBinaryErosion(*args, **kwargs) -> Any: ...
def multiBinaryOpening(*args, **kwargs) -> Any: ...
def multiGrayscaleClosing(*args, **kwargs) -> Any: ...
def multiGrayscaleDilation(*args, **kwargs) -> Any: ...
def multiGrayscaleErosion(*args, **kwargs) -> Any: ...
def multiGrayscaleOpening(*args, **kwargs) -> Any: ...
def nonLocalMean2d(*args, **kwargs) -> Any: ...
def nonLocalMean3d(*args, **kwargs) -> Any: ...
def nonLocalMean4d(*args, **kwargs) -> Any: ...
def nonlinearDiffusion(*args, **kwargs) -> Any: ...
def normalizedConvolveImage(*args, **kwargs) -> Any: ...
def radialSymmetryTransform2D(*args, **kwargs) -> Any: ...
def recursiveFilter2D(*args, **kwargs) -> Any: ...
def recursiveGaussianSmoothing2D(*args, **kwargs) -> Any: ...
def recursiveGradient2D(*args, **kwargs) -> Any: ...
def recursiveLaplacian2D(*args, **kwargs) -> Any: ...
def recursiveSmooth2D(*args, **kwargs) -> Any: ...
def rieszTransformOfLOG2D(*args, **kwargs) -> Any: ...
def shockFilter(*args, **kwargs) -> Any: ...
def simpleSharpening2D(*args, **kwargs) -> Any: ...
def skeletonizeImage(*args, **kwargs) -> Any: ...
def structureTensor(*args, **kwargs) -> Any: ...
def symmetricGradient(*args, **kwargs) -> Any: ...
def tensorDeterminant(*args, **kwargs) -> Any: ...
def tensorEigenRepresentation2D(*args, **kwargs) -> Any: ...
def tensorEigenvalues(*args, **kwargs) -> Any: ...
def tensorTrace(*args, **kwargs) -> Any: ...
def totalVariationFilter(*args, **kwargs) -> Any: ...
def vectorDistanceTransform(*args, **kwargs) -> Any: ...
def vectorToTensor(*args, **kwargs) -> Any: ...

class BorderTreatmentMode(Boost.Python.enum):
    BORDER_TREATMENT_AVOID: Any = ...
    BORDER_TREATMENT_CLIP: Any = ...
    BORDER_TREATMENT_REFLECT: Any = ...
    BORDER_TREATMENT_REPEAT: Any = ...
    BORDER_TREATMENT_WRAP: Any = ...
    names: Any = ...
    values: Any = ...
    __slots__: Any = ...

class Kernel1D(Boost.Python.instance):
    __instance_size__: Any = ...
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def borderTreatment(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initAveraging(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initBinomial(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initBurtFilter(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initDiscreteGaussian(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initExplicitly(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initGaussian(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initGaussianDerivative(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalFirstDerivative5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalFirstDerivativeSmoothing3(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalFirstDerivativeSmoothing5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalSecondDerivative5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalSecondDerivativeSmoothing3(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalSecondDerivativeSmoothing5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalSmoothing3(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initOptimalSmoothing5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initSecondDifference3(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initSymmetricDifference(self, *args, **kwargs) -> Any: ...
    @classmethod
    def left(self, *args, **kwargs) -> Any: ...
    @classmethod
    def norm(self, *args, **kwargs) -> Any: ...
    @classmethod
    def normalize(self, *args, **kwargs) -> Any: ...
    @classmethod
    def right(self, *args, **kwargs) -> Any: ...
    @classmethod
    def setBorderTreatment(self, *args, **kwargs) -> Any: ...
    @classmethod
    def size(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __getitem__(self, index) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...
    @classmethod
    def __setitem__(self, index, object) -> Any: ...

class Kernel2D(Boost.Python.instance):
    __instance_size__: Any = ...
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def borderTreatment(self, *args, **kwargs) -> Any: ...
    @classmethod
    def height(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initDisk(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initExplicitly(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initGaussian(self, *args, **kwargs) -> Any: ...
    @classmethod
    def initSeparable(self, *args, **kwargs) -> Any: ...
    @classmethod
    def lowerRight(self, *args, **kwargs) -> Any: ...
    @classmethod
    def norm(self, *args, **kwargs) -> Any: ...
    @classmethod
    def normalize(self, *args, **kwargs) -> Any: ...
    @classmethod
    def setBorderTreatment(self, *args, **kwargs) -> Any: ...
    @classmethod
    def upperLeft(self, *args, **kwargs) -> Any: ...
    @classmethod
    def width(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __getitem__(self, index) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...
    @classmethod
    def __setitem__(self, index, object) -> Any: ...

class NormPolicy(Boost.Python.instance):
    __instance_size__: Any = ...
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def __reduce__(self) -> Any: ...
    @property
    def meanDist(self) -> Any: ...
    @meanDist.setter
    def meanDist(self, val: Any) -> None: ...
    @property
    def sigma(self) -> Any: ...
    @sigma.setter
    def sigma(self, val: Any) -> None: ...
    @property
    def varRatio(self) -> Any: ...
    @varRatio.setter
    def varRatio(self, val: Any) -> None: ...

class RatioPolicy(Boost.Python.instance):
    __instance_size__: Any = ...
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def __reduce__(self) -> Any: ...
    @property
    def epsilon(self) -> Any: ...
    @epsilon.setter
    def epsilon(self, val: Any) -> None: ...
    @property
    def meanRatio(self) -> Any: ...
    @meanRatio.setter
    def meanRatio(self, val: Any) -> None: ...
    @property
    def sigma(self) -> Any: ...
    @sigma.setter
    def sigma(self, val: Any) -> None: ...
    @property
    def varRatio(self) -> Any: ...
    @varRatio.setter
    def varRatio(self, val: Any) -> None: ...
