# pyright: strict

from pathlib import PurePosixPath
from typing import Dict, List, Optional, Sequence, Union
from urllib.parse import parse_qs
# import functools
from ndstructs.utils.json_serializable import ensureJsonIntTripplet

from webilastik.datasource import FsDataSource
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo
from webilastik.libebrains.user_token import UserToken
from webilastik.ui import parse_url
from webilastik.ui.filesystem import try_filesystem_from_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url, Protocol



def try_get_datasources_from_url(
    *,
    url: Union[Url, str],
    ebrains_user_token: Optional[UserToken] = None,
    allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
) -> "List[FsDataSource] | UsageError":
    if isinstance(url, str):
        parsing_result = parse_url(url)
        if isinstance(parsing_result, UsageError):
            return parsing_result
        url = parsing_result
    fs_url = url.parent.schemeless()
    ds_path = PurePosixPath(url.path.name)
    hash_params: Dict[str, str]
    if url.hash_ is None:
        hash_params = {}
    else:
        hash_params: Dict[str, str] = {
            k: (v[-1] if v else "")
            for k, v in parse_qs(url.hash_, keep_blank_values=True, strict_parsing=True, encoding='utf-8').items()
        }

    filesystem_result = try_filesystem_from_url(url=fs_url, allowed_protocols=allowed_protocols, ebrains_user_token=ebrains_user_token)
    if isinstance(filesystem_result, UsageError):
        return filesystem_result
    filesystem = filesystem_result

    try:
        # FIXME: At least for now, these normal formats must have their formats in the url, just like a file extension
        if ds_path.suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
            return [SkimageDataSource(
                path=ds_path,
                filesystem=filesystem,
            )]

        # Precomputed chunks URL should point to the top level folder and have a resolution=x_y_z hash (not query!) parameter
        precomp_info_result = PrecomputedChunksInfo.tryLoad(filesystem=filesystem, path=ds_path.joinpath("info"))
        if isinstance(precomp_info_result, Exception):
            return UsageError(str(precomp_info_result))
        else:
            precomp_info = precomp_info_result
            try:
                resolution = ensureJsonIntTripplet(tuple(int(axis) for axis in hash_params["resolution"].split("_")))
            except KeyError:
                # No 'resolution' hash param in url
                return [
                    PrecomputedChunksDataSource(
                        filesystem=filesystem,
                        path=ds_path,
                        resolution=scale.resolution,
                    )
                    for scale in precomp_info.scales
                ]
            except ValueError:
                resolution_options = ["_".join(map(str, scale.resolution)) for scale in precomp_info.scales]
                return UsageError(f"Bad 'resolution' tripplet in url: {url}. Options are {resolution_options}")
            return [PrecomputedChunksDataSource(
                filesystem=filesystem,
                path=ds_path,
                resolution=resolution,
            )]
        return UsageError(f"Could not open {url}")
    except Exception as e:
        return UsageError(f"Could not open {url}: {e}")