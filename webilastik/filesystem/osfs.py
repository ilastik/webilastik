import os

from fs.osfs import OSFS

from webilastik.filesystem import Filesystem
from webilastik.server.rpc.dto import OsfsDto



class OsFs(OSFS, Filesystem):
    def __init__(self, root_path: str) -> None:
        if(os.environ.get("WEBILASTIK_ALLOW_OSFS", "false") != "true"):
            raise Exception("Not allowed to open local filesystem")
        super().__init__(
            root_path,
            expand_vars=False
        )

    def __getstate__(self) -> OsfsDto:
        return self.to_message()

    def to_message(self) -> OsfsDto:
        return OsfsDto(path=self.root_path)

    @staticmethod
    def from_message(message: OsfsDto) -> "OsFs":
        return OsFs(message.path)

    def __setstate__(self, message: OsfsDto):
        self.__init__(message.path)