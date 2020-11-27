from typing import List, Sequence, TypeVar, Type
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from pathlib import Path

import uuid
import numpy as np
from fs.osfs import OSFS
import vigra
from ndstructs.datasource import DataSource, SkimageDataSource, PrecomputedChunksDataSource

from webilastik.ui.applet import Applet, SequenceProviderApplet, Slot, CONFIRMER
from webilastik.filesystem import HttpPyFs



def url_to_datasource(url: str) -> DataSource:
    parsed_url = urlparse(url.lstrip("precomputed://"))
    if parsed_url.scheme in ("http", "https"):
        fs = HttpPyFs(parsed_url._replace(path="/").geturl())
    else:
        fs = OSFS("/")

    if url.startswith("precomputed://"):
        return PrecomputedChunksDataSource(
            path=Path(parsed_url.path),
            filesystem=fs
        )
    return DataSource.create(path=Path(parsed_url.path), filesystem=fs)


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
    def ilp_data(self):
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
class DataSelectionApplet(SequenceProviderApplet[Lane]):
    @property
    def lanes(self) -> Slot[Sequence[Lane]]:
        return self.items

    def get_ilp_data(self, lane_type: Type[ILane]) -> dict:
        return {
            "Role Names": np.asarray([name.encode('utf8') for name in lane_type.get_role_names()]),
            "StorageVersion": "0.2",
            "infos": {f"lane{lane_idx:04d}": lane.ilp_data for lane_idx, lane in enumerate(self.items() or [])},
            "local_data": {},
        }
