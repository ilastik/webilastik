# pyright: strict

from pathlib import Path
from typing import Dict, Optional, Sequence, Union
from urllib.parse import parse_qs
# import functools
from ndstructs.utils.json_serializable import ensureJsonIntTripplet

from webilastik.datasource import DataSource, SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo
from webilastik.libebrains.user_token import UserToken
from webilastik.ui.filesystem import try_filesystem_from_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url, Protocol



def try_load_datasource_from_url(
    *,
    url: Url,
    ebrains_user_token: Optional[UserToken],
    allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
) -> Union[DataSource, UsageError]:
    fs_url = url.parent
    ds_path = Path(url.path.name)
    hash_params: Dict[str, str]
    if url.hash_ is None:
        hash_params = {}
    else:
        hash_params: Dict[str, str] = {
            k: (v[-1] if v else "")
            for k, v in parse_qs(url.hash_, keep_blank_values=True, strict_parsing=True, encoding='utf-8').items()
        }

    filesystem = try_filesystem_from_url(url=fs_url, allowed_protocols=allowed_protocols, ebrains_user_token=ebrains_user_token)
    if not filesystem:
        return UsageError(f"Can't retrieve data from {fs_url}")

    # At least for now, these normal formats must have their formats in the url, just like a file extension
    if ds_path.suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        return SkimageDataSource(
            path=ds_path,
            filesystem=filesystem,
        )

    # Precomputed chunks URL should point to the top level folder and have a resolution=x_y_z hash (not query!) parameter
    precomp_info = PrecomputedChunksInfo.tryLoad(filesystem=filesystem, path=ds_path.joinpath("info"))
    if precomp_info:
        resolution_options = ["_".join(map(str, scale.resolution)) for scale in precomp_info.scales]
        try:
            resolution = ensureJsonIntTripplet(tuple(int(axis) for axis in hash_params["resolution"].split("_")))
        except KeyError:
            return UsageError(f"Missing 'resolution' hash param in url: {url}. Options are {resolution_options}")
        except ValueError:
            return UsageError(f"Bad 'resolution' tripplet in url: {url}. Options are {resolution_options}")
        return PrecomputedChunksDataSource(
            filesystem=filesystem,
            path=ds_path,
            resolution=resolution,
        )
    return UsageError(f"Could not open {url}")