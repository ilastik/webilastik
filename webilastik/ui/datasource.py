# pyright: strict

from typing import Optional, Sequence, Union

from webilastik.datasource import FsDataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.libebrains.user_token import UserToken
from webilastik.ui import parse_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url, Protocol



def try_get_datasources_from_url(
    *,
    url: Union[Url, str],
    ebrains_user_token: Optional[UserToken] = None,
    allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
) -> "Sequence[FsDataSource] | Exception":
    if isinstance(url, str):
        parsing_result = parse_url(url)
        if isinstance(parsing_result, UsageError):
            return parsing_result
        url = parsing_result

    if url.protocol not in allowed_protocols:
        return Exception(f"Disallowed protocol: {url.protocol} in {url}")

    if SkimageDataSource.supports_url(url):
        return SkimageDataSource.from_url(url)
    if PrecomputedChunksDataSource.supports_url(url):
        return PrecomputedChunksDataSource.from_url(url)
    return Exception(f"Could not open url {url}")