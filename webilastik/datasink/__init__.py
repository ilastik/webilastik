from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from fs.base import FS as FileSystem

from ndstructs import Point5D, Shape5D, Interval5D, Array5D


class DataSink(ABC):
    def __init__(
        self,
        *,
        tile_shape: Shape5D,
        interval: Interval5D,
        path: Path,
        filesystem: FileSystem,
        dtype: np.dtype,
        location: Point5D = Point5D.zero(),
    ):
        self.tile_shape = tile_shape
        self.interval = interval
        self.path = path
        self.filesystem = filesystem
        self.dtype = dtype
        self.location = location

    @abstractmethod
    def write(self, data: Array5D) -> None:
        pass
