from typing import Optional
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonBoolean
from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import PropagationOk, PropagationResult, UserPrompt
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError


class WsBrushingApplet(WsApplet, BrushingApplet):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.brushing_enabled = False

    def _get_json_state(self) -> JsonValue:
        return {
            "annotations": tuple(annotation.to_json_data() for annotation in self.annotations()),
            "brushing_enabled": self.brushing_enabled,
        }

    def set_brushing_enabled(self, enabled: bool) -> PropagationResult:
        self.brushing_enabled = enabled
        return PropagationOk()

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if method_name == "brushing_enabled":
            enabled = ensureJsonBoolean(arguments.get("enabled"))
            return UsageError.check(self.set_brushing_enabled(enabled=enabled))

        raw_annotations = ensureJsonArray(arguments.get("annotations"))
        annotations = [Annotation.from_json_value(raw_annotation) for raw_annotation in raw_annotations]

        if method_name == "add_annotations":
            return UsageError.check(self.add_annotations(user_prompt, annotations))
        if method_name == "remove_annotations":
            return UsageError.check(self.remove_annotations(user_prompt, annotations))

        raise ValueError(f"Invalid method name: '{method_name}'")
