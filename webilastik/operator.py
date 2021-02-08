from abc import ABC, abstractmethod
from typing import Callable, Optional, TypeVar

import numpy as np

from ndstructs.datasource import DataRoi, DataSource
from ndstructs import Array5D, Shape5D

class Operator(ABC):
    @abstractmethod
    def compute(self, roi: DataRoi) -> Array5D:
        """Perform this operator's computaion and returns its result"""
        pass

    # for data-dependant Operators like ConnectedComponents this can't be done in any sensible way =/
    # @abstractmethod
    # def get_expected_output_shape(self, input_shape: Shape5D) -> Shape5D:
    #     pass

    # and because get_expected_output_shape can be done in a sensible
    # def to_datasource(self, input: DataSource) -> DataSource:
    #     pass

    def get_tile_shape_hint(self, datasource: DataSource) -> Shape5D:
        """Returns a sensible tile shape to be used when processing 'datasource'"""
        #defaults to processing tiles with all channels all channels when predicting
        return datasource.tile_shape.updated(c=datasource.shape.c)

        return datasource.shape

class NoopOperator(Operator):
    def compute(self, roi: DataRoi) -> Array5D:
        return roi.retrieve()
