# pyright: strict

from typing import Dict, List, Sequence, Set, Tuple

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonString
import numpy as np

from webilastik.datasource import DataSource
from webilastik.annotations.annotation import Annotation, Color
from webilastik.ui.applet import Applet, PropagationError, PropagationOk, PropagationResult, UserPrompt, applet_output, user_interaction
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

class Label:
    def __init__(self, *, name: str, color: Color, annotations: Sequence[Annotation]) -> None:
        self.name = name
        self.color = color
        self.annotations = list(annotations)
        super().__init__()

    def to_json_value(self) -> JsonObject:
        return {
            "name": self.name,
            "color": self.color.to_json_data(),
            "annotations": tuple(annotation.to_json_data() for annotation in self.annotations),
        }

    def clone(self) -> "Label":
        return Label(name=self.name, color=self.color, annotations=list(self.annotations))

    def is_empty(self) -> bool:
        return len(self.annotations) == 0

class BrushingApplet(Applet):
    def __init__(self, name: str, labels: Sequence[Label]):
        if len(labels) < 2:
            raise ValueError(f"Must have at least 2 labels")
        self._labels: List[Label] = list(labels)
        super().__init__(name=name)

    def take_snapshot(self) -> List[Label]:
        return [label.clone() for label in self._labels]

    def restore_snaphot(self, snapshot: List[Label]) -> None:
        self._labels = snapshot

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return PropagationOk()

    @applet_output
    def label_classes(self) -> Dict[Color, Tuple[Annotation, ...]]:
        return {label.color: tuple(label.annotations) for label in self._labels}

    @applet_output
    def labels(self) -> Sequence[Label]:
        return [label.clone() for label in self._labels]

    @applet_output
    def datasources(self) -> Set[DataSource]:
        return {a.raw_data for label in self._labels for a in label.annotations}

    @applet_output
    def label_colors(self) -> Sequence[Color]:
        return [label.color for label in self._labels]

    @applet_output
    def label_names(self) -> Sequence[str]:
        return [label.name for label in self._labels]

    def get_label(self, label_name: str) -> "Label | None":
        for label in self._labels:
            if label.name == label_name:
                return label

    @user_interaction(refresh_self=False)
    def create_label(self, user_prompt: UserPrompt, label_name: str, color: Color) -> PropagationResult:
        for label in self._labels:
            if label.name == label_name:
                return PropagationError(f"A label with name {label_name} already exists")
            if label.color == color:
                return PropagationError(f"A label with color {color.hex_code} already exists: {label.name}")
        self._labels.append(Label(name=label_name, color=color, annotations=[]))
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def remove_label(self, user_prompt: UserPrompt, label_name: str) -> PropagationResult:
        self._labels = [label for label in self._labels if label.name != label_name]
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def add_annotation(self, user_prompt: UserPrompt, label_name: str, annotation: Annotation) -> PropagationResult:
        label = self.get_label(label_name)
        if label is None:
            return PropagationError(f"No label with name {label_name}")
        label.annotations.append(annotation)
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def remove_annotation(self, user_prompt: UserPrompt, label_name: str, annotation: Annotation) -> PropagationResult:
        label = self.get_label(label_name)
        if label is None:
            return PropagationError(f"No label with name {label_name}")
        label.annotations = [a for a in label.annotations if a != annotation]
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def recolor_label(self, user_prompt: UserPrompt, label_name: str, new_color: Color) -> PropagationResult:
        label = self.get_label(label_name)
        if label is None:
            return PropagationError(f"No label named {label_name}")
        if new_color in self.label_colors():
            return PropagationError(f"Label with color {new_color.hex_code} already exists")
        label.color = new_color
        return PropagationOk()

    @user_interaction(refresh_self=False)
    def rename_label(self, user_prompt: UserPrompt, old_name: str, new_name: str) -> PropagationResult:
        target_label = self.get_label(old_name)
        if target_label is None:
            return PropagationError(f"No label named {old_name}")
        homonym_label = self.get_label(new_name)
        if homonym_label is not None and homonym_label is not target_label:
            return PropagationError(f"There is already a label named '{new_name}'")
        target_label.name = new_name
        return PropagationOk()


class WsBrushingApplet(WsApplet, BrushingApplet):
    @classmethod
    def initial(cls, name: str) -> "WsBrushingApplet":
        return WsBrushingApplet(name=name, labels=[
            Label(
                name="Foreground",
                color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
                annotations=[]
            ),
            Label(
                name="Background",
                color=Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0)),
                annotations=[]
            ),
        ])

    def _get_json_state(self) -> JsonValue:
        return {
            "labels": tuple(label.to_json_value() for label in self._labels),
        }

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> "UsageError | None":
        if method_name == "recolor_label":
            return UsageError.check(self.recolor_label(
                user_prompt,
                label_name=ensureJsonString(arguments.get("label_name")),
                new_color=Color.from_json_data(arguments.get("new_color"))
            ))

        if method_name == "rename_label":
            return UsageError.check(self.rename_label(
                user_prompt,
                old_name=ensureJsonString(arguments.get("old_name")),
                new_name=ensureJsonString(arguments.get("new_name"))
            ))

        if method_name == "create_label":
            return UsageError.check(self.create_label(
                user_prompt=user_prompt,
                label_name=ensureJsonString(arguments.get("label_name")),
                color=Color.from_json_data(arguments.get("color")),
            ))

        if method_name == "remove_label":
            return UsageError.check(self.remove_label(
                user_prompt=user_prompt,
                label_name=ensureJsonString(arguments.get("label_name")),
            ))

        if method_name == "add_annotation":
            return UsageError.check(self.add_annotation(
                user_prompt,
                label_name=ensureJsonString(arguments.get("label_name")),
                annotation=Annotation.from_json_value(arguments.get("annotation")),
            ))
        if method_name == "remove_annotation":
            return UsageError.check(self.remove_annotation(
                user_prompt,
                label_name=ensureJsonString(arguments.get("label_name")),
                annotation=Annotation.from_json_value(arguments.get("annotation")),
            ))

        raise ValueError(f"Invalid method name: '{method_name}'")
