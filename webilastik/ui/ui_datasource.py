# pyright: strict

import re
from pathlib import Path
from typing import Optional, Sequence, Union
from typing_extensions import Final
import uuid
import functools

from webilastik.datasource import DataSource, PrecomputedChunksDataSource, SkimageDataSource, N5DataSource

from webilastik.utility.url import DataScheme, Url, Protocol

class UiDataSource:
    datasource: Final[DataSource]
    name: Final[str]
    url: Final[Url]

    # private init?
    def __init__(
        self,
        *,
        datasource: DataSource,
        url: Url,
        name: Optional[str],
    ):
        self.datasource = datasource
        self.name = name or url.path.name
        self.url = url

    @classmethod
    @functools.lru_cache()
    def from_url(
        cls, *, url: Union[Url, str], name: Optional[str] = None, allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
    ) -> "UiDataSource":
        parsed_url = Url.parse(url) if isinstance(url, str) else url
        if parsed_url not in allowed_protocols:
            raise ValueError(f"Disallowed protocol '{parsed_url.protocol}'' in url '{url}'")

        path = Path(parsed_url.path)
        if parsed_url.datascheme == DataScheme.PRECOMPUTED:
            # expect a resolution query param determining which scale to use: e.g.: ?precomputed_scale_resolution=10_20_30
            resolution_param_name = "precomputed_scale_resolution"
            raw_resolution = parsed_url.search.get(resolution_param_name)
            if raw_resolution is None:
                raise ValueError(f"Missing '{resolution_param_name}' query parameter")
            resolution = tuple(int(axis) for axis in raw_resolution.split("_"))
            if len(raw_resolution) != 3:
                raise ValueError(f"Bad '{resolution_param_name}': {raw_resolution}")
            parsed_url = parsed_url.updated_with(
                search={k: v for k, v in parsed_url.search.items() if k != resolution_param_name}
            )
            fs = parsed_url.get_filesystem()
            datasource = PrecomputedChunksDataSource(path=path, filesystem=fs, resolution=(resolution[0], resolution[1], resolution[2]))
        elif re.search(r'\.(jpe?g|png|bmp)$', parsed_url.path.name, re.IGNORECASE):
            datasource = SkimageDataSource(path=path, filesystem=parsed_url.get_filesystem())
        elif re.search(r'\.n5\b', parsed_url.path.as_posix(), re.IGNORECASE):
            datasource = N5DataSource(path=path, filesystem=parsed_url.get_filesystem())
        else:
            raise ValueError(f"Could not open url {url}")

        return UiDataSource(
            datasource=datasource,
            url=parsed_url,
            name=str(uuid.uuid4()) if name is None else name, # FIXME: handle name better
        )
