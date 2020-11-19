from typing import Sequence, Optional
from abc import ABC, abstractmethod

from ndstructs import Array5D
from ndstructs.datasource import DataSource, DataSourceSlice

from webilastik.ui.applet import Applet, Slot, CONFIRMER
from webilastik.ui.applet.data_selection_applet import ILane
from webilastik.operator import Operator


class Array5DViewer(Applet, ABC):
    def __init__(self, source: Slot[Operator], lanes: Slot[Sequence[ILane]]):
        self._in_source = source
        self._in_lanes = lanes
        self.current_lane_index = Slot[int](
            owner=self,
            refresher=self._refresh_current_lane_index
        )
        super().__init__()

    def switch_to_lane(self, lane_index: int):
        lanes = self._in_lanes() or []
        if lane_index >= len(lanes):
            raise ValueError(f"Can't switch to lane {lane_index}. There are currently {len(lanes)} lanes")
        self.current_lane_index.set_value(lane_index, confirmer=lambda msg: True)

    def _refresh_current_lane_index(self, confirmer: CONFIRMER) -> Optional[int]:
        lanes = self._in_lanes()
        if lanes is None:
            return None
        if len(lanes) == 0:
            return None
        return min(len(lanes), (self.current_lane_index() or 0))

    def post_refresh(self, confirmer: CONFIRMER):
        lanes = self._in_lanes()
        if lanes is None:
            return
        lane = lanes[self.current_lane_index() or 0]
        op = self._in_source()
        if op is None:
            return
        self.draw(op, lane.get_raw_data())

    @abstractmethod
    def draw(self, operator: Operator, datasource: DataSource):
        pass

class GimpArray5DViewer(Array5DViewer):
    def draw(self, operator: Operator, datasource: DataSource):
        data = operator.compute(DataSourceSlice(datasource))
        data.show_channels()