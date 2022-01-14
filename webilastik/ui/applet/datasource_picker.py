from typing import Optional, Sequence
import json

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonString, toJsonValue

from webilastik.libebrains.user_token import UserToken
from webilastik.ui import parse_url
from webilastik.ui.applet import InertApplet, NoSnapshotApplet, PropagationError, PropagationOk, PropagationResult, UserPrompt, applet_output, user_interaction
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.datasource import  try_get_datasources_from_url
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Protocol, Url
from webilastik.datasource import DataSource


class DataSourcePicker(InertApplet, NoSnapshotApplet):
    def __init__(
        self,
        *,
        name: str,
        ebrains_user_token: UserToken,
        allowed_protocols: Sequence[Protocol],
    ) -> None:
        self.ebrains_user_token = ebrains_user_token
        self.allowed_protocols = allowed_protocols

        self._datasource_url: Optional[Url] = None
        self._datasource_choices: Optional[Sequence[DataSource]] = None
        self._datasource: Optional[DataSource] = None
        super().__init__(name)

    @applet_output
    def datasource(self) -> Optional[DataSource]:
        return self._datasource

    @user_interaction
    def set_url(self, user_prompt: UserPrompt, url: Url) -> PropagationResult:
        datasource_result = try_get_datasources_from_url(
            url=url,
            ebrains_user_token=self.ebrains_user_token,
            allowed_protocols=self.allowed_protocols
        )
        if isinstance(datasource_result, UsageError):
            return PropagationError(str(datasource_result))
            self._datasource_url = None
        self._datasource_url = url
        self._datasource_choices = datasource_result
        if len(self._datasource_choices) == 1:
            self._datasource = self._datasource_choices[0]
        return PropagationOk()

    @user_interaction
    def pick_datasource(self, user_prompt: UserPrompt, datasource_index: int) -> PropagationResult:
        if self._datasource_choices is None:
            return PropagationError("No DataSource choices available")
        num_datasources = len(self._datasource_choices)
        if  num_datasources <= datasource_index:
            return PropagationError("Bad datasource choice index: {datasource_index}. Must be smaller than {num_datasources}")
        self._datasource = self._datasource_choices[datasource_index]
        return PropagationOk()


class WsDataSourcePicker(WsApplet, DataSourcePicker):
    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "set_url":
            url_result = parse_url(ensureJsonString(arguments.get("url")))
            if isinstance(url_result, UsageError):
                return url_result
            rpc_result = self.set_url(
                user_prompt=user_prompt,
                url=url_result
            )
            if isinstance(rpc_result, PropagationError):
                return UsageError(rpc_result.message)
            return

        if method_name == "pick_datasource":
            datasource_index = ensureJsonInt(arguments.get("datasource_index"))
            rpc_result = self.pick_datasource(user_prompt, datasource_index=datasource_index)
            if isinstance(rpc_result, PropagationError):
                return UsageError(rpc_result.message)
            return

        return UsageError(f"Method not found: {method_name}")

    def _get_json_state(self) -> JsonValue:
        return {
            "datasource_url": toJsonValue(self._datasource_url),
            "datasource_choices": toJsonValue(tuple(self._datasource_choices or ()) or None),
            "datasource": toJsonValue(self._datasource),
        }