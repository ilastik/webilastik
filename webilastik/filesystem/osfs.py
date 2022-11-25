from fs.osfs import OSFS

from webilastik.filesystem import Filesystem
from webilastik.server.rpc.dto import OsfsDto
from webilastik.config import WorkflowConfig



class OsFs(OSFS, Filesystem):
    def __init__(self, root_path: str) -> None:
        if(not WorkflowConfig.get().allow_local_fs): #FIXME: move this to from_dto so we can return Exception?
            raise Exception("Not allowed to open local filesystem")
        super().__init__(
            root_path,
            expand_vars=False
        )

    def __getstate__(self) -> OsfsDto:
        return self.to_dto()

    def to_dto(self) -> OsfsDto:
        return OsfsDto(path=self.root_path)

    @staticmethod
    def from_dto(message: OsfsDto) -> "OsFs":
        return OsFs(message.path)

    def __setstate__(self, message: OsfsDto):
        self.__init__(message.path)