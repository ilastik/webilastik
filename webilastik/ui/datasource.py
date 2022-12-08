# pyright: strict

from typing import Optional, Sequence, Union, Tuple

from webilastik.datasource import FsDataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.filesystem import FsFileNotFoundException, create_filesystem_from_url
from webilastik.libebrains.user_token import UserToken
from webilastik.ui import parse_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url


def try_get_datasources_from_url(
    *,
    url: Union[Url, str],
    ebrains_user_token: Optional[UserToken] = None,
) -> "FsDataSource | Tuple[FsDataSource, ...] | None | Exception":
    if isinstance(url, str):
        parsing_result = parse_url(url)
        if isinstance(parsing_result, UsageError):
            return parsing_result
        url = parsing_result

    fs_result = create_filesystem_from_url(url=url)
    if isinstance(fs_result, Exception):
        return fs_result
    fs, path = fs_result

    datasources_result: "FsDataSource | Sequence[FsDataSource] | None | Exception"
    if SkimageDataSource.supports_path(path):
        datasources_result = SkimageDataSource.try_open(fs=fs, path=path)
    else:
        resolution_result = PrecomputedChunksDataSource.get_resolution_from_url(url)
        if isinstance(resolution_result, Exception):
            return resolution_result
        datasources_result = PrecomputedChunksDataSource.try_open_scales(fs=fs, path=path, resolution=resolution_result)
        if isinstance(datasources_result, (PrecomputedChunksDataSource, tuple)):
            return datasources_result
        if not isinstance(datasources_result, FsFileNotFoundException):
            return datasources_result
        # try opening as precomputed, even without the prefix
        return PrecomputedChunksDataSource.try_open_as_scale_path(fs=fs, path=path)
