
from abc import abstractmethod
from typing import Optional
from ndstructs.utils.json_serializable import JsonObject, JsonValue
from webilastik.ui.applet import Applet, UserPrompt
from webilastik.ui.usage_error import UsageError


class WsApplet(Applet):
    @abstractmethod
    def _get_json_state(self) -> JsonValue:
        pass

    @abstractmethod
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        ...
