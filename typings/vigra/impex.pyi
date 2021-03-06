import Boost.Python
readHDF5: Any
writeHDF5: Any

def isImage(filename) -> bool: ...
def listExtensions(*args, **kwargs) -> Any: ...
def listFormats(*args, **kwargs) -> Any: ...
def numberImages(filename) -> int: ...
def readImage(filename, dtype = ..., index = ..., order = ...) -> Image: ...
def readVolume(filename, dtype = ..., order = ...) -> Volume: ...
def writeImage(image, filename, dtype = ..., compression = ..., mode = ...) -> Any: ...
def writeVolume(volume, filename_base, filename_ext, dtype = ..., compression = ...) -> Any: ...

class ImageInfo(Boost.Python.instance):
    @classmethod
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def getAxisTags(self, *args, **kwargs) -> Any: ...
    @classmethod
    def getDtype(self, *args, **kwargs) -> Any: ...
    @classmethod
    def getShape(self, *args, **kwargs) -> Any: ...
    @classmethod
    def __reduce__(self) -> Any: ...
