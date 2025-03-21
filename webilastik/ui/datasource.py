# pyright: strict

from collections.abc import Mapping
from typing import Optional, Tuple
from base64 import b64decode
import json

from aiohttp import web

from webilastik.datasource import FsDataSource
from webilastik.server.rpc.dto import parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_
from webilastik.datasource import FsDataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.deep_zoom_datasource import DziLevelDataSource
from webilastik.filesystem import FsFileNotFoundException, create_filesystem_from_url
from webilastik.libebrains.user_token import AccessToken

from webilastik.utility.url import Url

def _ensure_none(value: None):
    pass

def get_encoded_datasource_from_url(match_info_key: str, request: web.Request) -> "FsDataSource | Exception":
    encoded_datasource = request.match_info.get(match_info_key)
    if not encoded_datasource:
        return Exception("Missing path segment: datasource=...")
    decoded_datasource = b64decode(encoded_datasource, altchars=b'-_').decode('utf8')
    datasource_json_value = json.loads(decoded_datasource)
    datasource_dto = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(datasource_json_value)
    if isinstance(datasource_dto, Exception):
        return datasource_dto
    return FsDataSource.try_from_message(datasource_dto)

def try_get_datasources_from_url(
    *,
    url: Url,
    ebrains_user_token: Optional[AccessToken] = None,
) -> "Tuple[FsDataSource, ...] | None | Exception":
    fs_result = create_filesystem_from_url(url=url)
    if isinstance(fs_result, Exception):
        return fs_result
    fs, path = fs_result

    dzi_datasources = DziLevelDataSource.try_load(filesystem=fs, path=path)
    if isinstance(dzi_datasources, Exception):
        return dzi_datasources
    if isinstance(dzi_datasources, Mapping):
        dzi_level_result = DziLevelDataSource.get_level_from_url(url)
        if isinstance(dzi_level_result, Exception):
            return dzi_level_result
        if dzi_level_result is None:
            out = tuple(dzi_datasources.values())
        else:
            out = tuple(ds for level, ds in dzi_datasources.items() if level == dzi_level_result)
        if len(out) == 0:
            return Exception(f"No dzi levels found for {url.raw}")
        return out
    _ensure_none(dzi_datasources)

    skimage_datasource = SkimageDataSource.try_open(fs=fs, path=path)
    if isinstance(skimage_datasource, Exception):
        return skimage_datasource
    if isinstance(skimage_datasource, SkimageDataSource):
        return (skimage_datasource, )
    _ensure_none(skimage_datasource)

    precomp_chunks_resolution_result = PrecomputedChunksDataSource.get_resolution_from_url(url)
    if isinstance(precomp_chunks_resolution_result, Exception):
        return precomp_chunks_resolution_result
    precomp_datasources_result = PrecomputedChunksDataSource.try_open_scales(fs=fs, path=path, resolution=precomp_chunks_resolution_result)
    if isinstance(precomp_datasources_result, tuple):
        return precomp_datasources_result
    if not isinstance(precomp_datasources_result, FsFileNotFoundException):
        return precomp_datasources_result

    # try opening as precomputed, even without the prefix
    precomp_scale_ds = PrecomputedChunksDataSource.try_open_as_scale_path(fs=fs, scale_path=path)
    if isinstance(precomp_scale_ds, (Exception, type(None))):
        return precomp_scale_ds
    return (precomp_scale_ds, )
