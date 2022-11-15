# pyright: strict

from typing import Union

from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.server.message_schema import BucketFSMessage, HttpFsMessage#, OsfsMessage
# from webilastik.filesystem.osfs import OsFs
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.http_fs import HttpFs


def fs_from_message(message: Union[HttpFsMessage, BucketFSMessage]) -> Union[BucketFs, HttpFs]: #Union[OsFs, BucketFs, HttpFs]:
    # if isinstance(message, OsfsMessage):
    #     return OsFs.from_message(message)
    if isinstance(message, BucketFSMessage):
        return BucketFs.from_message(message)
    return HttpFs.from_message(message)
