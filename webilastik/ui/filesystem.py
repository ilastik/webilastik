from typing import Sequence, Optional

from webilastik.filesystem import JsonableFilesystem
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.http_fs import HttpFs
from webilastik.filesystem.osfs import OsFs
from webilastik.utility.url import Url, Protocol
from webilastik.libebrains.user_token import UserToken


def try_filesystem_from_url(
    url: Url,
    allowed_protocols: Sequence[Protocol],
    ebrains_user_token: Optional[UserToken] = None,
) -> Optional[JsonableFilesystem]:
    if url.protocol not in allowed_protocols:
        raise ValueError(f"Disallowed protocol '{url.protocol}' in url '{url}'")
    filesystem: Optional[JsonableFilesystem] = None
    if url.protocol == Protocol.FILE:
        filesystem = OsFs(url.path.parent.as_posix())
    if filesystem is None and ebrains_user_token is not None:
        filesystem = BucketFs.try_from_url(url=url, ebrains_user_token=ebrains_user_token)
    if filesystem is None:
        filesystem = HttpFs.try_from_url(url)
    return filesystem
