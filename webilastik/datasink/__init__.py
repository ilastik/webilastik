from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from ndstructs import Point5D, Shape5D, Interval5D, Array5D


class DataSink(ABC):
    def __init__(
        self,
        *,
        tile_shape: Shape5D,
        interval: Interval5D,
        path: Path,
        dtype: np.dtype, #type: ignore
        location: Point5D = Point5D.zero(),
    ):
        self.tile_shape = tile_shape
        self.interval = interval
        self.path = path
        self.dtype = dtype # type: ignore
        self.location = location

    @abstractmethod
    def write(self, data: Array5D) -> None:
        pass
