from abc import ABC, abstractmethod

import numpy as np

from ndstructs.datasource import DataSourceSlice, DataSource
from ndstructs import Array5D, Slice5D


class DataSourceOperator(DataSource):
    def __init__(self, operator: "Operator", raw_datasource: DataSource):
        expected_roi = operator.get_expected_roi(raw_datasource.roi)
        super().__init__(
            url=f"{operator} < {raw_datasource.url}",
            tile_shape=raw_datasource.tile_shape,
            dtype=operator.get_expected_dtype(input_dtype=raw_datasource.dtype),
            name=f"{operator} < {raw_datasource}",
            shape=expected_roi.shape,
            location=expected_roi.start,
        )
        self.operator = operator
        self.raw_datasource = raw_datasource

    def _get_tile(self, tile: Slice5D) -> Array5D:
        raw_slice = tile.with_coord(c=self.raw_datasource.roi.c)
        data_slice = DataSourceSlice(datasource=self.raw_datasource, **raw_slice.to_dict())
        return self.operator.compute(data_slice)



class Operator(ABC):
    @abstractmethod
    def compute(self, roi: DataSourceSlice) -> Array5D:
        pass

    @abstractmethod
    def get_expected_roi(self, data_slice: Slice5D) -> Slice5D:
        pass

    @abstractmethod
    def get_expected_dtype(self, input_dtype: np.dtype) -> np.dtype:
        pass

    def as_datasource(self, datasource: DataSource) -> DataSource:
        return DataSourceOperator(operator=self, raw_datasource=datasource)