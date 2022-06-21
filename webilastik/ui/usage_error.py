from typing import Optional
from ndstructs.utils.json_serializable import JsonObject
from webilastik.ui.applet import CascadeError, CascadeResult


class UsageError(Exception):
    pass

    @classmethod
    def check(cls, result: CascadeResult) -> Optional["UsageError"]:
        if isinstance(result, CascadeError):
            return UsageError(result.message)
        return None

    def to_json_value(self) -> JsonObject:
        return {
            "message": str(self),
            "__class__": self.__class__.__name__
        }