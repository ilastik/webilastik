from typing import List, Sequence, TypeVar
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from pathlib import Path

from fs.osfs import OSFS
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

Lane = TypeVar("Lane", bound=ILane)
class DataSelectionApplet(SequenceProviderApplet[Lane]):
    @property
    def lanes(self) -> Slot[Sequence[Lane]]:
        return self.items