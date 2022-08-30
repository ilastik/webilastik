#pyright: strict

from abc import ABC, abstractmethod
from concurrent.futures import Executor
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Set, Callable, Any, Mapping
import re
import json
import threading
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonObject, ensureJsonString
from webilastik.annotations.annotation import Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import DataScheme, Url, Protocol
from webilastik.datasource import FsDataSource
from webilastik.ui.applet import Applet, AppletOutput, CascadeError, CascadeOk, CascadeResult, UserPrompt, cascade
from webilastik.ui.datasource import try_get_datasources_from_url

class View(ABC):
    def __init__(self, name: str, url: Url) -> None:
        self.name = name
        self.url = url
        super().__init__()

    @abstractmethod
    def to_json_value(self) -> JsonObject:
        return {
            "name": self.name,
            "url": self.url.raw,
            "__class__": self.__class__.__name__,
        }

    @staticmethod
    def try_open(*, name: str, url: Url, session_url: Url, allowed_protocols: Sequence[Protocol]) -> "View":
        view_result = (
            PredictionsView.try_from_url(name=name, url=url, session_url=session_url, allowed_protocols=allowed_protocols) or
            StrippedPrecomputedView.try_from_url(name=name, url=url, session_url=session_url, allowed_protocols=allowed_protocols) or
            RawDataView.try_from_url(name=name, url=url, allowed_protocols=allowed_protocols)
        )
        if isinstance(view_result, type(None)):
            return UnsupportedDatasetView(name=name, url=url)
        if isinstance(view_result, Exception):
            return FailedView(name=name, url=url, error_message=str(view_result))
        return view_result


class RawDataView(View):
    def __init__(self, name: str, url: Url, datasources: Sequence[FsDataSource]) -> None:
        self.datasources = datasources
        super().__init__(name=name, url=url)

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "datasources": tuple([ds.to_json_value() for ds in self.datasources])
        }

    @classmethod
    def try_from_url(cls, name: str, url: Url, allowed_protocols: Sequence[Protocol]) -> "RawDataView | None | Exception":
        datasources_result = try_get_datasources_from_url(url=url, allowed_protocols=allowed_protocols)
        if isinstance(datasources_result, (Exception, type(None))):
            return datasources_result
        return RawDataView(name=name, url=url, datasources=datasources_result)

class StrippedPrecomputedView(View):
    def __init__(self, *, name: str, session_url: Url, datasource: PrecomputedChunksDataSource) -> None:
        self.datasource = datasource
        original_url = datasource.url.updated_with(hash_="")
        resolution_str = "_".join(str(axis) for axis in datasource.spatial_resolution)
        super().__init__(
            name=name,
            url=session_url.updated_with(
                datascheme=DataScheme.PRECOMPUTED
            ).concatpath(f"stripped_precomputed/url={original_url.raw}/resolution=${resolution_str}"),
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "datasource": self.datasource.to_json_value(),
        }

    @classmethod
    def matches(cls, url: Url) -> bool:
        return cls.extract_url_params(url=url) is not None

    @classmethod
    def extract_url_params(cls, url: Url) -> "Tuple[Url, Tuple[int, int, int]] | None | Exception":
        try:
            stripped_precomputed_url_regex = re.compile(r"/stripped_precomputed/url=(?P<url>[^/]+)/resolution=(?P<resolution>\d+_\d+_\d+)")
            match = stripped_precomputed_url_regex.search(url.path.as_posix())
            if match is None:
                return None
            url = Url.from_base64(match.group("url"))
            selected_resolution = tuple(int(axis) for axis in match.group("resolution").split("_"))
            return (url, selected_resolution)
        except Exception as e:
            return e

    @classmethod
    def try_from_url(cls, *, name: str, url: Url, session_url: Url, allowed_protocols: Sequence[Protocol]) -> "StrippedPrecomputedView | None | Exception":
        url_params_result = cls.extract_url_params(url)
        if isinstance(url_params_result,  (Exception, type(None))):
            return url_params_result
        original_url, selected_resolution = url_params_result
        raw_view_result = RawDataView.try_from_url(name=name, url=original_url, allowed_protocols=allowed_protocols)
        assert raw_view_result is not None
        if isinstance(raw_view_result, Exception):
            return raw_view_result

        datasources = [ds for ds in raw_view_result.datasources if ds.spatial_resolution == selected_resolution]
        if len(datasources) != 1:
            return Exception(f"Expected single datasource, found these: {[ds.url for ds in datasources]}")
        datasource = datasources[0]
        if not isinstance(datasource, PrecomputedChunksDataSource):
            return Exception(f"Expected {url} to point to precomptued chunks. Got this: {datasource.__class__.__name__}")
        return StrippedPrecomputedView(name=name, session_url=session_url, datasource=datasource)

class PredictionsView(View):
    def __init__(
        self, *, name: str, session_url: Url, raw_data: FsDataSource, classifier_generation: int,
    ) -> None:
        self.raw_data: FsDataSource = raw_data
        self.classifier_generation: int = classifier_generation
        super().__init__(
            name=name,
            url=session_url.updated_with(
                datascheme=DataScheme.PRECOMPUTED # FIXME: this assumes neuroglancer as the viewer
            ).concatpath(f"predictions/raw_data=${raw_data.url.to_base64()}/generation=${classifier_generation}"),
        )

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "raw_data": self.raw_data.to_json_value(),
            "classifier_generation": self.classifier_generation,
        }

    @classmethod
    def matches(cls, url: Url) -> "bool | Exception":
        result = cls.extract_url_params(url)
        return result if isinstance(result, Exception) else (result is not None)

    @classmethod
    def extract_url_params(cls, url: Url) -> "Tuple[Url, int] | None | Exception":
        try:
            predictions_regex = re.compile(r"/predictions/raw_data=(?P<raw_data>[^/]+)/generation=(?P<generation>[^/?]+)")
            match = predictions_regex.search(url.path.as_posix())
            if match is None:
                return None
            raw_data_url = Url.from_base64(match.group("raw_data"))
            classifier_generation = int(match.group("generation"))
            return (raw_data_url, classifier_generation)
        except Exception as e:
            return e

    @classmethod
    def try_from_url(cls, *, name: str, url: Url, session_url: Url, allowed_protocols: Sequence[Protocol]) -> "PredictionsView | None | Exception":
        try:
            url_params_result = cls.extract_url_params(url)
            if isinstance(url_params_result, (Exception, type(None))):
                return url_params_result
            raw_data_url, classifier_generation = url_params_result
            raw_view_result = RawDataView.try_from_url(name=name, url=raw_data_url, allowed_protocols=allowed_protocols)
            assert raw_view_result is not None
            if isinstance(raw_view_result, Exception):
                return raw_view_result
            datasources = raw_view_result.datasources
            if len(datasources) != 1:
                return Exception(f"Expected single datasource, found these: {[ds.url for ds in datasources]}")
            return PredictionsView(
                name=name, session_url=session_url, raw_data=datasources[0], classifier_generation=classifier_generation
            )
        except Exception as e:
            return e

class UnsupportedDatasetView(View):
    def to_json_value(self) -> JsonObject:
        return super().to_json_value()

class FailedView(View):
    def __init__(self, name: str, url: Url, error_message: str) -> None:
        super().__init__(name, url)
        self.error_message: str = error_message

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "error_message": self.error_message,
        }


@dataclass
class ViewerAppletState:
    generation: int
    active_views: Sequence[View]

    def to_json_value(self) -> JsonObject:
        return {
            "active_views": tuple(view.to_json_value() for view in self.active_views)
        }

class WsViewerApplet(Applet):
    def __init__(
        self,
        *,
        name: str,
        generational_classifier: AppletOutput["Tuple[VigraPixelClassifier[IlpFilter], int] | None"],
        label_colors: AppletOutput["Sequence[Color] | None"],
        allowed_protocols: Set[Protocol],
        session_url: Url,
        executor: Executor,
        on_async_change: Callable[[], Any]
    ) -> None:
        self._in_classifier = generational_classifier
        self._in_label_colors = label_colors
        self.allowed_protocols = allowed_protocols
        self.session_url = session_url
        self.executor = executor
        self.on_async_change = on_async_change
        self.lock = threading.Lock()

        self.views_generation: int = 0
        self.cached_views: Dict[Url, View] = {}
        self.active_views: Dict[Url, View] = {}

        super().__init__(name=name)

    def _get_json_state(self) -> JsonValue:
        with self.lock:
            return ViewerAppletState(active_views=tuple(self.active_views.values()), generation=self.views_generation).to_json_value()

    def print(self, msg: str):
        print(f"[VIEWER APPLET gen {self.views_generation:03d}] {msg}")

    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        label_colors = self._in_label_colors()
        classifier_and_generation = self._in_classifier()
        with self.lock:
            self.print(f"Closing all previous prediction views...")
            self.active_views = {url: view for url, view in self.active_views.items() if not isinstance(view, PredictionsView)}
            if classifier_and_generation is None or label_colors is None:
                self.print(f"No classsifier: Returning ")
                return CascadeOk()
            _, generation = classifier_and_generation
            self.print(f"Updating predictions...")
            for view in tuple(self.active_views.values()):
                if isinstance(view, RawDataView) and len(view.datasources) == 1:
                    training_datasource = view.datasources[0]
                elif isinstance(view, StrippedPrecomputedView):
                    training_datasource = view.datasource
                else:
                    continue
                self.print(f"will add prediction view to {view.url}")
                predictions_view = PredictionsView(
                    name=f"Predicting on {view.name}",
                    classifier_generation=generation,
                    raw_data=training_datasource,
                    session_url=self.session_url,
                )
                self.active_views[predictions_view.url] = predictions_view
        return CascadeOk()

    @cascade(refresh_self=False)
    def close_predictions(self, user_prompt: UserPrompt) -> CascadeResult:
        with self.lock:
            self.active_views = {url: view for url, view in self.active_views.items() if not isinstance(view, PredictionsView)}
            return CascadeOk()

    @cascade(refresh_self=True)
    def set_active_views(self, user_prompt: UserPrompt, native_views: Mapping[str, Url]) -> CascadeResult:
        with self.lock:
            self.views_generation += 1
            views_generation = self.views_generation
            native_views_urls = set(native_views.values())

            for url in tuple(self.active_views.keys()):
                if url not in native_views_urls:
                    self.print(f"Url {url} not in native views. Removing...")
                    del self.active_views[url]
            for view_name, view_url in native_views.items():
                if view_url in self.active_views:
                    self.print(f"Url {view_url} is already open. Skipping...")
                    continue
                if  PredictionsView.matches(view_url):
                    self.print(f"Url {view_url} is a predictions view, dealt with in refresh. Skipping...")
                    continue
                if view_url in self.cached_views:
                    self.print(f"Url {view_url} was cached. Using that...")
                    self.active_views[view_url] = self.cached_views[view_url]
                    continue
                self.print(f"Will try to open {view_url} ...")
                future_view = self.executor.submit(
                    _try_open_view,
                    name=view_name, url=view_url, allowed_protocols=tuple(self.allowed_protocols), session_url=self.session_url
                )
                future_view.add_done_callback(lambda fut: self._add_active_view(user_prompt, fut.result(), views_generation))
                future_view.add_done_callback(lambda _: self.on_async_change())
        return CascadeOk()

    @cascade(refresh_self=False)
    def _add_active_view(self, user_prompt: UserPrompt, view: "View", views_generation: int) -> CascadeResult:
        with self.lock:
            self.print(f">>> (Gen {views_generation}) Adding view ({view.__class__.__name__}) for {view.url}")
            if self.views_generation == views_generation:
                self.active_views[view.url] = view
            if view.url not in self.cached_views or isinstance(self.cached_views[view.url], FailedView):
                self.cached_views[view.url] = view
        return CascadeOk()

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        if(method_name == "set_active_views"):
            active_view_urls: Dict[str, Url] = {}
            for native_view in ensureJsonArray(arguments.get("native_views")):
                native_view_obj = ensureJsonObject(native_view)
                view_url = Url.parse(ensureJsonString(native_view_obj.get("url")))
                view_name = ensureJsonString(native_view_obj.get("name"))
                if view_url is None:
                    raise ValueError(f"Could not parse url in {json.dumps(native_view)}")
                active_view_urls[view_name] = view_url

            result = self.set_active_views(user_prompt=user_prompt, native_views=active_view_urls)
            if isinstance(result, CascadeError):
                return UsageError(result.message)
            return None

        raise ValueError(f"Invalid method name: '{method_name}'")

def _try_open_view(*, name: str, url: Url, session_url: Url, allowed_protocols: Sequence[Protocol]) -> "View":
    view_result = (
        StrippedPrecomputedView.try_from_url(name=name, url=url, session_url=session_url, allowed_protocols=allowed_protocols) or
        RawDataView.try_from_url(name=name, url=url, allowed_protocols=allowed_protocols)
    )
    if isinstance(view_result, type(None)):
        return UnsupportedDatasetView(name=name, url=url)
    if isinstance(view_result, Exception):
        return FailedView(name=name, url=url, error_message=str(view_result))
    return view_result