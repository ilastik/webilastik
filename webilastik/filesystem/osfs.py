from fs.osfs import OSFS

from webilastik.filesystem import Filesystem
from webilastik.server.message_schema import OsfsMessage



class OsFs(OSFS, Filesystem):
    def __getstate__(self) -> OsfsMessage:
        return self.to_message()

    def to_message(self) -> OsfsMessage:
        return OsfsMessage(path=self.root_path)

    @staticmethod
    def from_message(message: OsfsMessage) -> "OsFs":
        return OsFs(message.path)

    def __setstate__(self, message: OsfsMessage):
        self.__init__(message.path)