# pyright: strict

from concurrent.futures import Executor
import os
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, Optional, Sequence, Set
import tempfile

import h5py
import numpy as np

from ndstructs.utils.json_serializable import JsonObject
from webilastik.annotations.annotation import Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier

from webilastik.datasource import FsDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem import IFilesystem
from webilastik.filesystem.os_fs import OsFs
from webilastik.libebrains.user_credentials import EbrainsUserCredentials
from webilastik.scheduling.job import PriorityExecutor
from webilastik.ui.applet.brushing_applet import Label, WsBrushingApplet
from webilastik.ui.applet.feature_selection_applet import WsFeatureSelectionApplet
from webilastik.ui.applet.pixel_predictions_export_applet import WsPixelClassificationExportApplet
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet import UserPrompt
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.applet.ws_pixel_classification_applet import WsPixelClassificationApplet
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup
from webilastik.utility.url import Url



class PixelClassificationWorkflow:
    def __init__(
        self,
        *,
        on_async_change: Callable[[], None],
        executor: Executor,
        priority_executor: PriorityExecutor,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],

        feature_extractors: "Set[IlpFilter] | None" = None,
        labels: Sequence[Label] = (),
        pixel_classifier: "VigraPixelClassifier[IlpFilter] | None" = None,
    ):
        super().__init__()

        self.executor = executor
        self.priority_executor = priority_executor
        self.on_async_change = on_async_change

        self.brushing_applet = WsBrushingApplet(
            name="brushing_applet",
            ebrains_user_credentials=ebrains_user_credentials,
            labels=labels if len(labels) > 0 else [
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
        self.feature_selection_applet = WsFeatureSelectionApplet(
            name="feature_selection_applet",
            feature_extractors=feature_extractors,
            datasources=self.brushing_applet.datasources,
        )

        self.pixel_classifier_applet = WsPixelClassificationApplet(
            "pixel_classification_applet",
            ebrains_user_credentials=ebrains_user_credentials,
            feature_extractors=self.feature_selection_applet.feature_extractors,
            label_classes=self.brushing_applet.label_classes,
            executor=priority_executor,
            on_async_change=on_async_change,
            pixel_classifier=pixel_classifier,
        )

        self.export_applet = WsPixelClassificationExportApplet(
            name="export_applet",
            ebrains_user_credentials=ebrains_user_credentials,
            priority_executor=priority_executor,
            operator=self.pixel_classifier_applet.pixel_classifier,
            datasource_suggestions=self.brushing_applet.datasources.transformed_with(
                lambda datasources: tuple(ds for ds in datasources if isinstance(ds, FsDataSource))
            ),
            populated_labels=self.brushing_applet.labels.transformed_with(lambda labels: [l for l in labels if len(l.annotations) > 0]),
            on_async_change=on_async_change,
        )

        self.wsapplets: Dict[str, WsApplet] = {
            self.feature_selection_applet.name: self.feature_selection_applet,
            self.brushing_applet.name: self.brushing_applet,
            self.pixel_classifier_applet.name: self.pixel_classifier_applet,
            self.export_applet.name: self.export_applet,
        }

    @classmethod
    def from_ilp(
        cls,
        *,
        ilp_path: Path,
        on_async_change: Callable[[], None],
        executor: Executor,
        priority_executor: PriorityExecutor,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],
    ) -> "PixelClassificationWorkflow | Exception":
        fs_result = OsFs.create()
        if isinstance(fs_result, Exception):
            return fs_result
        with h5py.File(ilp_path, "r") as f:
            parsing_result = IlpPixelClassificationWorkflowGroup.parse(
                group=f,
                ilp_fs=fs_result,
                ebrains_user_credentials=ebrains_user_credentials,
            )
            if isinstance(parsing_result, Exception):
                return parsing_result

            return PixelClassificationWorkflow(
                on_async_change=on_async_change,
                executor=executor,
                priority_executor=priority_executor,
                ebrains_user_credentials=ebrains_user_credentials,

                feature_extractors=set(parsing_result.FeatureSelections.feature_extractors),
                labels=parsing_result.PixelClassification.labels,
                pixel_classifier=parsing_result.PixelClassification.classifier,
            )

    @classmethod
    def from_ilp_bytes(
        cls,
        *,
        ilp_bytes: bytes,
        on_async_change: Callable[[], None],
        executor: Executor,
        priority_executor: PriorityExecutor,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],
    ) -> "PixelClassificationWorkflow | Exception":
        tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5") # FIXME
        num_bytes_written = os.write(tmp_file_handle, ilp_bytes)
        assert num_bytes_written == len(ilp_bytes)
        os.close(tmp_file_handle)
        workflow =  PixelClassificationWorkflow.from_ilp(
            ilp_path=Path(tmp_file_path),
            on_async_change=on_async_change,
            executor=executor,
            priority_executor=priority_executor,
            ebrains_user_credentials=ebrains_user_credentials,
        )
        os.remove(tmp_file_path)
        return workflow

    def to_ilp_workflow_group(self) -> IlpPixelClassificationWorkflowGroup:
        return IlpPixelClassificationWorkflowGroup.create(
            feature_extractors=self.feature_selection_applet.feature_extractors(),
            labels=self.brushing_applet.labels(),
            classifier=self.pixel_classifier_applet.pixel_classifier(),
        )

    def get_ilp_contents(self) -> bytes:
        return self.to_ilp_workflow_group().to_h5_file_bytes()

    def save_project(self, fs: IFilesystem, path: PurePosixPath) -> int:
        contents = self.get_ilp_contents()
        save_result = fs.create_file(path=path, contents=contents)
        if isinstance(save_result, Exception):
            raise save_result #FIXME: return instead
        return len(contents)

    def run_rpc(self, *, user_prompt: UserPrompt, applet_name: str, method_name: str, arguments: JsonObject) -> "UsageError | None":
        return self.wsapplets[applet_name].run_rpc(method_name=method_name, arguments=arguments, user_prompt=user_prompt)

    def get_json_state(self) -> JsonObject:
        return {name: applet._get_json_state() for name, applet in self.wsapplets.items()} #pyright: ignore [reportPrivateUsage]


class WsPixelClassificationWorkflow(PixelClassificationWorkflow):
    def __init__(
        self,
        *,
        on_async_change: Callable[[], None],
        executor: Executor,
        priority_executor: PriorityExecutor,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],

        feature_extractors: "Set[IlpFilter] | None" = None,
        labels: Sequence[Label] = (),
        pixel_classifier: "VigraPixelClassifier[IlpFilter] | None" = None,
    ):
        super().__init__(
            on_async_change=on_async_change,
            executor=executor,
            ebrains_user_credentials=ebrains_user_credentials,
            priority_executor=priority_executor,
            feature_extractors=feature_extractors,
            labels=labels,
            pixel_classifier=pixel_classifier,
        )

    @staticmethod
    def from_pixel_classification_workflow(
        workflow: PixelClassificationWorkflow, ebrains_user_credentials: Optional[EbrainsUserCredentials]
    ) -> "WsPixelClassificationWorkflow":
        return WsPixelClassificationWorkflow(
            on_async_change=workflow.on_async_change,
            executor=workflow.executor,
            ebrains_user_credentials=ebrains_user_credentials,
            priority_executor=workflow.priority_executor,
            feature_extractors=set(workflow.feature_selection_applet.feature_extractors()),
            labels=workflow.brushing_applet.labels(),
            pixel_classifier=workflow.pixel_classifier_applet.pixel_classifier(),
        )

    @staticmethod
    def load_from_ilp(
        *,
        ilp_path: Path,
        on_async_change: Callable[[], None],
        executor: Executor,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],
        priority_executor: PriorityExecutor,
        session_url: Url,
    ) -> "WsPixelClassificationWorkflow | Exception":
        fs_result = OsFs.create()
        if isinstance(fs_result, Exception):
            return fs_result

        try:
            f = h5py.File(ilp_path, "r")
        except Exception as e:
            print(e)
            return Exception(f"Could not open ilp file")

        parsing_result = IlpPixelClassificationWorkflowGroup.parse(
            group=f,
            ilp_fs=fs_result,
            ebrains_user_credentials=ebrains_user_credentials,
        )
        if isinstance(parsing_result, Exception):
            return parsing_result
        return WsPixelClassificationWorkflow(
            on_async_change=on_async_change,
            executor=executor,
            priority_executor=priority_executor,
            ebrains_user_credentials=ebrains_user_credentials,

            feature_extractors=set(parsing_result.FeatureSelections.feature_extractors),
            labels=parsing_result.PixelClassification.labels,
            pixel_classifier=parsing_result.PixelClassification.classifier,
        )

    @staticmethod
    def load_from_ilp_bytes(
        *,
        ilp_bytes: bytes,
        on_async_change: Callable[[], None],
        executor: Executor,
        priority_executor: PriorityExecutor,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],
        session_url: Url,
    ) -> "WsPixelClassificationWorkflow | Exception":
        try:
            tmp_file_handle, tmp_file_path = tempfile.mkstemp(suffix=".h5") # FIXME
            num_bytes_written = os.write(tmp_file_handle, ilp_bytes)
            assert num_bytes_written == len(ilp_bytes)
            os.close(tmp_file_handle)
        except Exception as e:
            print(e)
            return Exception(f"Error processing ilp bytes")
        workflow =  WsPixelClassificationWorkflow.load_from_ilp(
            ilp_path=Path(tmp_file_path),
            on_async_change=on_async_change,
            executor=executor,
            ebrains_user_credentials=ebrains_user_credentials,
            priority_executor=priority_executor,
            session_url=session_url,
        )
        try:
            os.remove(tmp_file_path)
        except Exception as e:
            print(e)
        return workflow

