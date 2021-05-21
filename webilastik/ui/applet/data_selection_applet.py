from typing import Any, Mapping, Sequence, TypeVar, Type, Generic, Optional, Sequence
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from pathlib import Path

import uuid
import numpy as np
from fs.osfs import OSFS
import vigra
from ndstructs.datasource import DataSource, PrecomputedChunksDataSource

from webilastik.ui.applet import Applet, Slot, ValueSlot, CONFIRMER
from webilastik.filesystem import HttpPyFs


def create_precomputed_chunks_datasource(url: str) -> PrecomputedChunksDataSource:
    parsed_url = urlparse(url.lstrip("precomputed://"))
    return PrecomputedChunksDataSource(
        path=Path(parsed_url.path),
        filesystem=HttpPyFs(parsed_url._replace(path="/").geturl())
    )


class ILane(ABC):
    @abstractmethod
    def get_raw_data(self) -> DataSource:
        pass

    @classmethod
    @abstractmethod
    def get_role_names(cls) -> Sequence[str]:
        pass

    @property
    @abstractmethod
    def ilp_data(self) -> Any:
        pass

    @classmethod
    def datasource_to_ilp_data(cls, datasource: DataSource):
        url = datasource.url
        return {
            "allowLabels": True,
            "axisorder": datasource.axiskeys.encode("utf8"),
            "axistags": vigra.defaultAxistags(datasource.axiskeys).toJSON().encode("utf8"),
            "datasetId": str(uuid.uuid1()).encode("utf8"),
            "dtype": str(datasource.dtype).encode("utf8"),
            "filePath": url.encode("utf8"),
            "fromstack": False,  # FIXME
            "location": "FileSystem".encode("utf8"), #FIXME
            "nickname": datasource.name.encode("utf8"), #FIXME
            "shape": datasource.shape.to_tuple(datasource.axiskeys),
            "display_mode": "default".encode('utf8'), #FIXME
            "normalizeDisplay": True, #FIXME
            "drange": None, #FIXME
        }

Lane = TypeVar("Lane", bound=ILane)
class DataSelectionApplet(Applet, Generic[Lane]):
    def __init__(self, name: str):
        self.lanes = ValueSlot[Sequence[Lane]](owner=self, refresher=self._refresh_lanes)
        super().__init__(name=name)

    def _refresh_lanes(self, confirmer: CONFIRMER) -> Optional[Sequence[Lane]]:
        return self.lanes.get() or None # foce empty lanes to be None instead of []

    def get_ilp_data(self, lane_type: Type[ILane]) -> Mapping[str, Any]:
        return {
            "Role Names": np.asarray([name.encode('utf8') for name in lane_type.get_role_names()]),
            "StorageVersion": "0.2",
            "infos": {f"lane{lane_idx:04d}": lane.ilp_data for lane_idx, lane in enumerate(self.lanes() or [])},
            "local_data": {},
        }
