# pyright: reportUnusedCallResult=false
# pyright: strict

from concurrent.futures import Executor
from pathlib import PurePosixPath
from typing import Callable, Mapping
import io

import h5py
from ndstructs.utils.json_serializable import JsonObject

from webilastik.datasource import FsDataSource
from webilastik.filesystem import JsonableFilesystem
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet.pixel_predictions_export_applet import WsPixelClassificationExportApplet
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet import UserPrompt
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.applet.ws_feature_selection_applet import WsFeatureSelectionApplet
from webilastik.ui.applet.ws_brushing_applet import WsBrushingApplet
from webilastik.ui.applet.ws_pixel_classification_applet import WsPixelClassificationApplet
from webilastik.libebrains.user_token import UserToken
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup



class PixelClassificationWorkflow:
    def __init__(
        self,
        *,
        ebrains_user_token: UserToken,
        on_async_change: Callable[[], None],
        executor: Executor,
        priority_executor: PriorityExecutor,
    ):
        super().__init__()
        UserToken.login_globally(ebrains_user_token)

        self.brushing_applet = WsBrushingApplet("brushing_applet")
        self.feature_selection_applet = WsFeatureSelectionApplet("feature_selection_applet", datasources=self.brushing_applet.datasources)

        self.pixel_classifier_applet = WsPixelClassificationApplet(
            "pixel_classification_applet",
            feature_extractors=self.feature_selection_applet.feature_extractors,
            annotations=self.brushing_applet.annotations,
            executor=executor,
            on_async_change=on_async_change,
        )

        self.export_applet = WsPixelClassificationExportApplet(
            name="export_applet",
            priority_executor=priority_executor,
            operator=self.pixel_classifier_applet.pixel_classifier,
            datasource_suggestions=self.brushing_applet.datasources.transformed_with(
                lambda datasources: tuple(ds for ds in datasources if isinstance(ds, FsDataSource))
            ),
            on_async_change=on_async_change,
        )

        self.wsapplets : Mapping[str, WsApplet] = {
            self.feature_selection_applet.name: self.feature_selection_applet,
            self.brushing_applet.name: self.brushing_applet,
            self.pixel_classifier_applet.name: self.pixel_classifier_applet,
            self.export_applet.name: self.export_applet,
        }

    def to_ilp_workflow_group(self) -> IlpPixelClassificationWorkflowGroup:
        return IlpPixelClassificationWorkflowGroup.create(
            feature_extractors=self.feature_selection_applet.feature_extractors() or [],
            annotations=self.brushing_applet.annotations() or [],
            classifier=self.pixel_classifier_applet.pixel_classifier(),
        )

    def get_ilp_contents(self) -> bytes:
        backing_buffer = io.BytesIO()
        f = h5py.File(backing_buffer, "w")
        root_group = f["/"]
        assert isinstance(root_group, h5py.Group)
        self.to_ilp_workflow_group().populate_group(root_group)
        f.close()
        _ = backing_buffer.seek(0)
        return backing_buffer.read()

    def save_project(self, fs: JsonableFilesystem, path: PurePosixPath) -> int:
        with fs.openbin(path.as_posix(), "w") as f:
            return f.write(self.get_ilp_contents())

    def run_rpc(self, *, user_prompt: UserPrompt, applet_name: str, method_name: str, arguments: JsonObject) -> "UsageError | None":
        return self.wsapplets[applet_name].run_rpc(method_name=method_name, arguments=arguments, user_prompt=user_prompt)

    def get_json_state(self) -> JsonObject:
        return {name: applet._get_json_state() for name, applet in self.wsapplets.items()} #pyright: ignore [reportPrivateUsage]
