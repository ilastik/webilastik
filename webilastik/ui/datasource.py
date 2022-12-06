# pyright: strict

from typing import Optional, Sequence, Union, Dict

from webilastik.datasource import FsDataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.libebrains.user_token import UserToken
from webilastik.ui import parse_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url


_datasource_cache: Dict[Url, Sequence[FsDataSource]] = {}

def try_get_datasources_from_url(
    *,
    url: Union[Url, str],
    ebrains_user_token: Optional[UserToken] = None,
) -> "Sequence[FsDataSource] | None | Exception":
    if isinstance(url, str):
        parsing_result = parse_url(url)
        if isinstance(parsing_result, UsageError):
            return parsing_result
        url = parsing_result

    cached_datasources = _datasource_cache.get(url)
    if cached_datasources is not None:
        return cached_datasources

    hashless_url = url.updated_with(hash_="")
    cached_datasources = _datasource_cache.get(hashless_url)
    for ds in cached_datasources or ():
        if ds.url == url:
            out = [ds]
            _datasource_cache[hashless_url] = out
            return out

    if SkimageDataSource.supports_url(url):
        datasources = SkimageDataSource.from_url(url)
    elif PrecomputedChunksDataSource.supports_url(url):
        datasources = PrecomputedChunksDataSource.from_url(url)
    else:
        # try opening as precomputed, even without the prefix
        datasources = PrecomputedChunksDataSource.from_url(url.updated_with(datascheme="precomputed"))
    if not isinstance(datasources, Exception):
        _datasource_cache[url] = datasources
    return datasources
