from typing import Optional
from webilastik.ui.applet import PropagationError, PropagationResult


class UsageError(Exception):
    pass

    @classmethod
    def check(cls, result: PropagationResult) -> Optional["UsageError"]:
        if isinstance(result, PropagationError):
            return UsageError(result.message)
        return None