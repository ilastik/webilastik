import Boost.Python

def pLSA(*args, **kwargs) -> Any: ...
def principalComponents(*args, **kwargs) -> Any: ...

class RF3_MTRY_SWITCH(Boost.Python.enum):
    RF3_MTRY_ALL: Any = ...
    RF3_MTRY_LOG: Any = ...
    RF3_MTRY_SQRT: Any = ...
    names: Any = ...
    values: Any = ...
    __slots__: Any = ...

class RF_MTRY_SWITCH(Boost.Python.enum):
    RF_MTRY_ALL: Any = ...
    RF_MTRY_LOG: Any = ...
    RF_MTRY_SQRT: Any = ...
    names: Any = ...
    values: Any = ...
    __slots__: Any = ...

class RF_OnlinePredictionSet(Boost.Python.instance):
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def get_worsed_tree(self, *args, **kwargs) -> Any: ...
    @classmethod
    def invalidateTree(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...

class RandomForest(Boost.Python.instance):
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def featureCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def labelCount(self, *args, **kwargs) -> Any: ...
    def learnRF(self, *args, **kwargs) -> float: ...
    @classmethod
    def learnRFWithFeatureSelection(self, *args, **kwargs) -> Any: ...
    @classmethod
    def onlineLearn(self, *args, **kwargs) -> Any: ...
    @classmethod
    def predictLabels(self, *args, **kwargs) -> Any: ...
    @classmethod
    def predictProbabilities(self, *args, **kwargs) -> Any: ...
    @classmethod
    def reLearnTree(self, *args, **kwargs) -> Any: ...
    @classmethod
    def treeCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def writeHDF5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...

class RandomForest3(Boost.Python.instance):
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def featureCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def labelCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def predictLabels(self, *args, **kwargs) -> Any: ...
    @classmethod
    def predictProbabilities(self, *args, **kwargs) -> Any: ...
    @classmethod
    def treeCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def writeHDF5(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...

class RandomForestOld(Boost.Python.instance):
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def featureCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def labelCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def predictLabels(self, *args, **kwargs) -> Any: ...
    @classmethod
    def predictProbabilities(self, *args, **kwargs) -> Any: ...
    @classmethod
    def treeCount(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...
