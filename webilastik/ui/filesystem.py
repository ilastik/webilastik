from typing import Sequence, Optional

from webilastik.filesystem import JsonableFilesystem
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.http_fs import HttpFs
from webilastik.filesystem.osfs import OsFs
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Url, Protocol
from webilastik.libebrains.user_token import UserToken


def try_filesystem_from_url(
    url: Url,
    allowed_protocols: Sequence[Protocol] = (Protocol.HTTPS, Protocol.HTTP),
    ebrains_user_token: Optional[UserToken] = None,
) -> "JsonableFilesystem | UsageError":
    if url.protocol not in allowed_protocols:
        raise ValueError(f"Disallowed protocol '{url.protocol}' in url '{url}'")
    if url.protocol == Protocol.FILE:
        return OsFs(url.path.parent.as_posix())
    if url.raw.startswith(BucketFs.API_URL.raw):
        return BucketFs.try_from_url(url=url, ebrains_user_token=ebrains_user_token)
    return HttpFs.try_from_url(url)
