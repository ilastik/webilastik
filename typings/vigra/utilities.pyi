import Boost.Python

class ChangeablePriorityQueueFloat32Min(Boost.Python.instance):
    __instance_size__: Any = ...
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def contains(vigra, std, int) -> Any: ...
    @classmethod
    def deleteItem(vigra, std, int) -> Any: ...
    @classmethod
    def pop(vigra, std) -> Any: ...
    @classmethod
    def push(vigra, std, int, float) -> Any: ...
    @classmethod
    def top(vigra, std) -> Any: ...
    @classmethod
    def topPriority(vigra, std) -> Any: ...
    @classmethod
    def __empty__(vigra, std) -> Any: ...
    @classmethod
    def __len__(vigra, std) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...
