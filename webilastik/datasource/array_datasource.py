from typing import Optional, Tuple

from ndstructs.point5D import Shape5D, Interval5D
from ndstructs.array5D import Array5D

from webilastik.datasource import DataSource

class ArrayDataSource(DataSource):
    """A DataSource backed by an Array5D"""

    def __init__(
        self,
        *,
        data: Array5D,
        tile_shape: Optional[Shape5D] = None,
        spatial_resolution: Optional[Tuple[int, int, int]] = None,
    ):
        self._data = data
        if tile_shape is None:
            tile_shape = Shape5D.hypercube(256).to_interval5d().clamped(self._data.shape).shape
        super().__init__(
            dtype=self._data.dtype, #type: ignore
            tile_shape=tile_shape,
            interval=self._data.interval,
            spatial_resolution=spatial_resolution,
        )

    def __hash__(self) -> int:
        return hash((self._data, self.tile_shape))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ArrayDataSource) and
            super().__eq__(other) and
            self._data == other._data
        )

    def _get_tile(self, tile: Interval5D) -> Array5D:
        return self._data.cut(tile, copy=True)