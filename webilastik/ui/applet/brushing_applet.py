# pyright: strict

from typing import Dict, List, Sequence, Set, Tuple

from ndstructs.utils.json_serializable import JsonObject, JsonValue
import numpy as np

from webilastik.datasource import DataSource
from webilastik.annotations.annotation import Annotation, Color
from webilastik.ui.applet import Applet, PropagationError, PropagationOk, PropagationResult, UserPrompt, applet_output, user_interaction
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError


class BrushingApplet(Applet):
    def __init__(self, name: str, colors: Sequence[Color]):
        if len(colors) < 2:
            raise ValueError(f"Must have at least 2 labels")
        self._labels: Dict[Color, List[Annotation]] = {color: [] for color in colors}
        super().__init__(name=name)

    def take_snapshot(self) -> Dict[Color, List[Annotation]]:
        return {k: v[:] for k, v in self._labels.items()}

    def restore_snaphot(self, snapshot: Dict[Color, List[Annotation]]) -> None:
        self._labels = snapshot

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return PropagationOk()

    @applet_output
    def label_classes(self) -> Dict[Color, Tuple[Annotation, ...]]:
        return {k: tuple(v) for k, v in self._labels.items()}

    @applet_output
    def datasources(self) -> Set[DataSource]:
        return {a.raw_data for annotations in self._labels.values() for a in annotations}

    @user_interaction(refresh_self=False)
    def create_label(self, user_prompt: UserPrompt, color: Color) -> PropagationResult:
        if color in self._labels:
            return PropagationError(f"A label with color {color.hex_code} already exists")
        self._labels[color] = []
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def add_annotation(self, user_prompt: UserPrompt, color: Color, annotation: Annotation) -> PropagationResult:
        if color not in self._labels:
            return PropagationError(f"No label with color {color.hex_code}")
        self._labels[color].append(annotation)
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def remove_annotation(self, user_prompt: UserPrompt, color: Color, annotation: Annotation) -> PropagationResult:
        if color not in self._labels:
            return PropagationError(f"No label with color {color.hex_code}")
        self._labels[color] = [a for a in self._labels[color] if a != annotation]
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def recolor_label(self, user_prompt: UserPrompt, old_color: Color, new_color: Color) -> PropagationResult:
        if old_color not in self._labels:
            return PropagationError(f"No label colored with {old_color.hex_code}")
        if new_color in self._labels:
            return PropagationError(f"Label with color {old_color.hex_code} already exists")
        self._labels = {
            color if color != old_color else new_color: annotations for color, annotations in self._labels.items()
        }
        return PropagationOk()

class WsBrushingApplet(WsApplet, BrushingApplet):
    @classmethod
    def initial(cls, name: str) -> "WsBrushingApplet":
        return WsBrushingApplet(name=name, colors=[
            Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
            Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0))
        ])

    def _get_json_state(self) -> JsonValue:
        return {
            "labels": tuple(
                {
                    "color": color.to_json_data(),
                    "annotations": tuple(annotation.to_json_data() for annotation in annotations)
                }
                for color, annotations in self._labels.items()
            ),
        }

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> "UsageError | None":
        if method_name == "recolor_label":
            return UsageError.check(self.recolor_label(
                user_prompt,
                old_color=Color.from_json_data(arguments.get("old_color")),
                new_color=Color.from_json_data(arguments.get("new_color"))
            ))

        if method_name == "create_label":
            return UsageError.check(self.create_label(
                user_prompt=user_prompt,
                color=Color.from_json_data(arguments.get("color")),
            ))

        if method_name == "add_annotation":
            return UsageError.check(self.add_annotation(
                user_prompt,
                color=Color.from_json_data(arguments.get("color")),
                annotation=Annotation.from_json_value(arguments.get("annotation")),
            ))
        if method_name == "remove_annotation":
            return UsageError.check(self.remove_annotation(
                user_prompt,
                color=Color.from_json_data(arguments.get("color")),
                annotation=Annotation.from_json_value(arguments.get("annotation")),
            ))

        raise ValueError(f"Invalid method name: '{method_name}'")
