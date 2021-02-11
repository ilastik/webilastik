from ndstructs.datasource import DataSource, PrecomputedChunksDataSource
from urllib.parse import urlparse
from pathlib import Path

from webilastik.filesystem import HttpPyFs

def datasource_from_url(url: str) -> DataSource:
    parsed_url = urlparse(url.lstrip("precomputed://"))
    pathless_url = parsed_url.scheme + "://" + parsed_url.netloc

    if parsed_url.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL: {url}")

    fs = HttpPyFs(pathless_url)
    path = Path(parsed_url.path)

    if url.startswith("precomputed://"):
        return PrecomputedChunksDataSource(path, filesystem=fs)

    return DataSource.create(path, filesystem=fs)
