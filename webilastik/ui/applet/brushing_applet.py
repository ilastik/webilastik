# pyright: strict

from typing import Sequence, Tuple

from webilastik.datasource import DataSource

from webilastik.annotations.annotation import Annotation
from webilastik.ui.applet import Applet, PropagationOk, PropagationResult, UserPrompt, applet_output, user_interaction


class BrushingApplet(Applet):
    def __init__(self, name: str):
        self._annotations: Tuple[Annotation, ...] = ()
        super().__init__(name=name)

    def take_snapshot(self) -> Tuple[Annotation, ...]:
        return self._annotations

    def restore_snaphot(self, snapshot: Tuple[Annotation, ...]) -> None:
        self._annotations = snapshot

    def on_dependencies_changed(self, user_prompt: UserPrompt) -> PropagationResult:
        return PropagationOk()

    @applet_output
    def annotations(self) -> Sequence[Annotation]:
        return self._annotations

    @applet_output
    def datasources(self) -> Tuple[DataSource, ...]:
        return tuple(a.raw_data for a in self._annotations)

    @user_interaction
    def add_annotations(self, user_prompt: UserPrompt, annotations: Sequence[Annotation]) -> PropagationResult:
        self._annotations = self._annotations + tuple(annotations)
        return PropagationOk()

    @user_interaction
    def remove_annotations(self, user_prompt: UserPrompt, annotations: Sequence[Annotation]) -> PropagationResult:
        self._annotations = tuple(a for a in self._annotations if a not in annotations)
        return PropagationOk()

