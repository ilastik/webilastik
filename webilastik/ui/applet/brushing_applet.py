# pyright: strict

from typing import Dict, List, Sequence, Set, Tuple

from webilastik.serialization.json_serialization import JsonObject, JsonValue
import numpy as np

from webilastik.datasource import DataSource
from webilastik.annotations.annotation import Annotation, Color
from webilastik.server.rpc.dto import (
    AddPixelAnnotationParams, BrushingAppletStateDto, CreateLabelParams, LabelHeaderDto, LabelDto, MessageParsingError, RecolorLabelParams, RemoveLabelParams, RemovePixelAnnotationParams, RenameLabelParams
)
from webilastik.ui.applet import Applet, CascadeError, CascadeOk, CascadeResult, UserPrompt, applet_output, cascade
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

class Label:
    def __init__(self, *, name: str, color: Color, annotations: Sequence[Annotation]) -> None:
        self.name = name
        self.color = color
        self.annotations = list(annotations)
        super().__init__()

    def to_messsage(self) -> LabelDto:
        return LabelDto(
            name=self.name,
            color=self.color.to_message(),
            annotations=tuple(annotation.to_message() for annotation in self.annotations),
        )

    def to_header_message(self) -> LabelHeaderDto:
        return LabelHeaderDto(
            name=self.name,
            color=self.color.to_message()
        )

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

    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        return CascadeOk()

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

    @cascade(refresh_self=False)
    def create_label(self, user_prompt: UserPrompt, label_name: str, color: Color) -> CascadeResult:
        for label in self._labels:
            if label.name == label_name:
                return CascadeError(f"A label with name {label_name} already exists")
            if label.color == color:
                return CascadeError(f"A label with color {color.hex_code} already exists: {label.name}")
        self._labels.append(Label(name=label_name, color=color, annotations=[]))
        return CascadeOk()

    @cascade(refresh_self=False)
    def remove_label(self, user_prompt: UserPrompt, label_name: str) -> CascadeResult:
        self._labels = [label for label in self._labels if label.name != label_name]
        return CascadeOk()

    @cascade(refresh_self=False)
    def add_annotation(self, user_prompt: UserPrompt, label_name: str, annotation: Annotation) -> CascadeResult:
        target_label = self.get_label(label_name)
        if target_label is None:
            return CascadeError(f"No label with name {label_name}")
        for label in self._labels:
            fixed_annotations: List[Annotation] = []
            for a in label.annotations:
                if a.raw_data != annotation.raw_data or a.interval.intersection(annotation.interval) is None:
                    fixed_annotations.append(a)
                else:
                    a.clear_collision(annotation=annotation)
                    if not a.is_blank():
                        fixed_annotations.append(a)
            label.annotations = fixed_annotations
        target_label.annotations.append(annotation)
        return CascadeOk()

    @cascade(refresh_self=False)
    def remove_annotation(self, user_prompt: UserPrompt, label_name: str, annotation: Annotation) -> CascadeResult:
        label = self.get_label(label_name)
        if label is None:
            return CascadeError(f"No label with name {label_name}")
        label.annotations = [a for a in label.annotations if a != annotation]
        return CascadeOk()

    @cascade(refresh_self=False)
    def recolor_label(self, user_prompt: UserPrompt, label_name: str, new_color: Color) -> CascadeResult:
        label = self.get_label(label_name)
        if label is None:
            return CascadeError(f"No label named {label_name}")
        if new_color in self.label_colors():
            return CascadeError(f"Label with color {new_color.hex_code} already exists")
        label.color = new_color
        return CascadeOk()

    @cascade(refresh_self=False)
    def rename_label(self, user_prompt: UserPrompt, old_name: str, new_name: str) -> CascadeResult:
        target_label = self.get_label(old_name)
        if target_label is None:
            return CascadeError(f"No label named {old_name}")
        homonym_label = self.get_label(new_name)
        if homonym_label is not None and homonym_label is not target_label:
            return CascadeError(f"There is already a label named '{new_name}'")
        target_label.name = new_name
        return CascadeOk()


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
        return BrushingAppletStateDto(
            labels=tuple(label.to_messsage() for label in self._labels),
        ).to_json_value() # FIXME: move to_json() outside

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> "UsageError | None":
        if method_name == "recolor_label":
            recolor_label_params = RecolorLabelParams.from_json_value(arguments)
            if isinstance(recolor_label_params, MessageParsingError):
                return UsageError(str(recolor_label_params)) # FIXME: this would be a bug, not an usage error
            return UsageError.check(self.recolor_label(
                user_prompt,
                label_name=recolor_label_params.label_name,
                new_color=Color(
                    r=np.uint8(recolor_label_params.new_color.r),
                    g=np.uint8(recolor_label_params.new_color.g),
                    b=np.uint8(recolor_label_params.new_color.b),
                )
            ))

        if method_name == "rename_label":
            rename_label_params = RenameLabelParams.from_json_value(arguments)
            if isinstance(rename_label_params, MessageParsingError):
                return UsageError(str(rename_label_params)) # FIXME: this would be a bug, not an usage error
            return UsageError.check(self.rename_label(
                user_prompt,
                old_name=rename_label_params.old_name,
                new_name=rename_label_params.new_name,
            ))

        if method_name == "create_label":
            create_label_params = CreateLabelParams.from_json_value(arguments)
            if isinstance(create_label_params, MessageParsingError):
                return UsageError(str(create_label_params)) # FIXME: this would be a bug, not an usage error
            return UsageError.check(self.create_label(
                user_prompt=user_prompt,
                label_name=create_label_params.label_name,
                color=Color(
                    r=np.uint8(create_label_params.color.r),
                    g=np.uint8(create_label_params.color.g),
                    b=np.uint8(create_label_params.color.b),
                ),
            ))

        if method_name == "remove_label":
            remove_label_params = RemoveLabelParams.from_json_value(arguments)
            if isinstance(remove_label_params, MessageParsingError):
                return UsageError(str(remove_label_params)) # FIXME: this would be a bug, not an usage error
            return UsageError.check(self.remove_label(
                user_prompt=user_prompt,
                label_name=remove_label_params.label_name,
            ))

        if method_name == "add_annotation":
            add_pixel_annotation_params = AddPixelAnnotationParams.from_json_value(arguments)
            if isinstance(add_pixel_annotation_params, MessageParsingError):
                return UsageError(str(add_pixel_annotation_params)) # FIXME: this would be a bug, not an usage error
            annotation_result = Annotation.from_message(add_pixel_annotation_params.pixel_annotation)
            if isinstance(annotation_result, Exception):
                return UsageError(str(annotation_result)) # FIXME: this would be a bug, not an usage error
            return UsageError.check(self.add_annotation(
                user_prompt,
                label_name=add_pixel_annotation_params.label_name,
                annotation=annotation_result,
            ))
        if method_name == "remove_annotation":
            remove_pixel_annotation_params = RemovePixelAnnotationParams.from_json_value(arguments)
            if isinstance(remove_pixel_annotation_params, MessageParsingError):
                return UsageError(str(remove_pixel_annotation_params)) # FIXME: this would be a bug, not an usage error
            annotation_result = Annotation.from_message(remove_pixel_annotation_params.pixel_annotation)
            if isinstance(annotation_result, Exception):
                return UsageError(str(annotation_result)) # FIXME: this would be a bug, not an usage error
            return UsageError.check(self.remove_annotation(
                user_prompt,
                label_name=remove_pixel_annotation_params.label_name,
                annotation=annotation_result,
            ))
        raise ValueError(f"Invalid method name: '{method_name}'")
