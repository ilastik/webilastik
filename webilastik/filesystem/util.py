# pyright: strict

from typing import Union

from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.server.rpc.dto import BucketFSDto, HttpFsDto#, OsfsDto
# from webilastik.filesystem.osfs import OsFs
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.http_fs import HttpFs


def fs_from_message(message: Union[HttpFsDto, BucketFSDto]) -> Union[BucketFs, HttpFs]: #Union[OsFs, BucketFs, HttpFs]:
    # if isinstance(message, OsfsDto):
    #     return OsFs.from_dto(message)
    if isinstance(message, BucketFSDto):
        return BucketFs.from_dto(message)
    return HttpFs.from_dto(message)
