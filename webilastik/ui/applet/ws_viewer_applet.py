#pyright: strict

from abc import ABC, abstractmethod
from concurrent.futures import Executor
from typing import Dict, Optional, Sequence, Tuple, Set, Callable, Any, Mapping
import re
import json
import threading
from dataclasses import dataclass
import asyncio


from ndstructs.utils.json_serializable import JsonObject, ensureJsonArray, ensureJsonInt, ensureJsonObject, ensureJsonString
from aiohttp import web

from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.server.session_allocator import uncachable_json_response
from webilastik.ui.applet.brushing_applet import Label
from webilastik.ui.applet.ws_applet import WsApplet
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import DataScheme, Url, Protocol
from webilastik.datasource import FsDataSource
from webilastik.ui.applet import AppletOutput, CascadeError, CascadeOk, CascadeResult, UserPrompt, cascade
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

class DataView(View):
    pass

class RawDataView(DataView):
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

class StrippedPrecomputedView(DataView):
    def __init__(self, *, name: str, session_url: Url, datasource: PrecomputedChunksDataSource) -> None:
        self.datasource = datasource
        all_scales_url = datasource.url.updated_with(hash_="")
        resolution_str = "_".join(str(axis) for axis in datasource.spatial_resolution)
        super().__init__(
            name=name,
            url=session_url.updated_with(
                datascheme=DataScheme.PRECOMPUTED
            ).concatpath(f"stripped_precomputed/url={all_scales_url.to_base64()}/resolution={resolution_str}"),
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
            ).concatpath(f"predictions/raw_data={raw_data.url.to_base64()}/generation={classifier_generation}"),
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

class UnsupportedDatasetView(DataView):
    def to_json_value(self) -> JsonObject:
        return super().to_json_value()

class FailedView(DataView):
    def __init__(self, name: str, url: Url, error_message: str) -> None:
        super().__init__(name, url)
        self.error_message: str = error_message

    def to_json_value(self) -> JsonObject:
        return {
            **super().to_json_value(),
            "error_message": self.error_message,
        }

@dataclass
class ViewsState:
    frontend_timestamp: int
    data_views: Mapping[Url, DataView]
    prediction_views: Mapping[Url, PredictionsView]

    def to_json_value(self) -> JsonObject:
        return {
            "frontend_timestamp": self.frontend_timestamp,
            "data_views": tuple(view.to_json_value() for view in self.data_views.values()),
            "prediction_views": tuple(view.to_json_value() for view in self.prediction_views.values()),
        }

    def updated_with(
        self,
        *,
        frontend_timestamp: int,
        data_views: "None | Mapping[Url, DataView]" = None,
        prediction_views: "None | Mapping[Url, PredictionsView]" = None,
    ) -> "ViewsState":
        if frontend_timestamp < self.frontend_timestamp:
            return self.updated_with(frontend_timestamp=self.frontend_timestamp)
        return ViewsState(
            frontend_timestamp=frontend_timestamp,
            data_views=self.data_views if data_views is None else data_views,
            prediction_views=self.prediction_views if prediction_views is None else prediction_views,
        )

    def with_extra_views(
        self,
        *,
        frontend_timestamp: int,
        extra_data_views: "Mapping[Url, DataView]" = {},
        extra_prediction_views: "Mapping[Url, PredictionsView]" = {},
    ) -> "ViewsState":
        return self.updated_with(
            frontend_timestamp=frontend_timestamp,
            data_views={**self.data_views, **extra_data_views},
            prediction_views={**self.prediction_views, **extra_prediction_views},
        )


class WsViewerApplet(WsApplet):
    def __init__(
        self,
        *,
        name: str,
        generational_classifier: AppletOutput["Tuple[VigraPixelClassifier[IlpFilter], int] | None"],
        labels: AppletOutput["Sequence[Label] | None"],
        allowed_protocols: Set[Protocol],
        session_url: Url,
        executor: Executor,
        on_async_change: Callable[[], Any]
    ) -> None:
        self._in_generational_classifier = generational_classifier
        self._in_labels = labels
        self.allowed_protocols = allowed_protocols
        self.session_url = session_url
        self.executor = executor
        self.on_async_change = on_async_change
        self.lock = threading.Lock()

        self.cached_views: Dict[Url, View] = {}
        self.state: ViewsState = ViewsState(frontend_timestamp=0, data_views={}, prediction_views={})
        self.frontend_timestamp = 0
        super().__init__(name=name)

    def _get_json_state(self) -> JsonObject:
        with self.lock:
            labels = self._in_labels() or ()
            return {
                **self.state.to_json_value(),
                "label_colors": tuple(label.color.to_json_data() for label in labels if len(label.annotations) > 0), # FIXME
            }

    def take_snapshot(self) -> ViewsState:
        with self.lock:
            return self.state

    def restore_snaphot(self, snapshot: ViewsState) -> None:
        with self.lock:
            self.state = snapshot

    @cascade(refresh_self=True)
    def _add_data_view(self, user_prompt: UserPrompt, view: DataView, frontend_timestamp: int) -> CascadeResult:
        with self.lock:
            self.state = self.state.with_extra_views(frontend_timestamp=frontend_timestamp, extra_data_views={view.url: view})
            if view.url not in self.cached_views or isinstance(self.cached_views[view.url], FailedView):
                self.cached_views[view.url] = view
        return CascadeOk()

    def refresh(self, user_prompt: UserPrompt) -> CascadeResult:
        labels = self._in_labels()
        classifier_and_generation = self._in_generational_classifier()
        with self.lock:
            self.cached_views = {url: view for url, view in self.cached_views.items() if not isinstance(view, PredictionsView)}
            new_prediction_views: Dict[Url, PredictionsView] = {}
            if classifier_and_generation is not None and labels is not None:
                _, generation = classifier_and_generation
                for view in tuple(self.state.data_views.values()):
                    if isinstance(view, RawDataView) and len(view.datasources) == 1:
                        training_datasource = view.datasources[0]
                    elif isinstance(view, StrippedPrecomputedView):
                        training_datasource = view.datasource
                    else:
                        continue
                    predictions_view = PredictionsView(
                        name=f"Predicting on {view.name}",
                        classifier_generation=generation,
                        raw_data=training_datasource,
                        session_url=self.session_url,
                    )
                    new_prediction_views[predictions_view.url] = predictions_view
                    self.cached_views[predictions_view.url] = predictions_view
            self.state = self.state.updated_with(frontend_timestamp=self.state.frontend_timestamp, prediction_views=new_prediction_views)
        self.on_async_change() #FIXME: this should probably be done at the workflow level, not at the applet level
        return CascadeOk()

    @cascade(refresh_self=False)
    def close_predictions(self, user_prompt: UserPrompt, frontend_timestamp: int) -> CascadeResult:
        with self.lock:
            self.state = self.state.updated_with(frontend_timestamp=frontend_timestamp, prediction_views={})
            return CascadeOk()

    @cascade(refresh_self=True)
    def set_data_views(self, user_prompt: UserPrompt, native_views: Mapping[str, Url], frontend_timestamp: int) -> CascadeResult:
        with self.lock:
            new_data_views: Dict[Url, DataView] = {}
            for view_name, view_url in native_views.items():
                if  PredictionsView.matches(view_url):
                    continue
                cached_view = self.cached_views.get(view_url)
                if isinstance(cached_view, (RawDataView, StrippedPrecomputedView, UnsupportedDatasetView)):
                    new_data_views[view_url] = cached_view
                    continue
                future_view = self.executor.submit(
                    _try_open_data_view,
                    name=view_name, url=view_url, allowed_protocols=tuple(self.allowed_protocols), session_url=self.session_url
                )
                future_view.add_done_callback(lambda fut: self._add_data_view(user_prompt, fut.result(), frontend_timestamp=frontend_timestamp))
                future_view.add_done_callback(lambda _: self.on_async_change())
            self.state = self.state.updated_with(frontend_timestamp=frontend_timestamp, data_views=new_data_views, prediction_views={})
        return CascadeOk()

    def run_rpc(self, *, user_prompt: UserPrompt, method_name: str, arguments: JsonObject) -> Optional[UsageError]:
        frontend_timestamp = ensureJsonInt(arguments.get("frontend_timestamp"))

        if method_name == "set_data_views":
            active_view_urls: Dict[str, Url] = {}
            for native_view in ensureJsonArray(arguments.get("native_views")):
                native_view_obj = ensureJsonObject(native_view)
                view_url = Url.parse(ensureJsonString(native_view_obj.get("url")))
                view_name = ensureJsonString(native_view_obj.get("name"))
                if view_url is None:
                    raise ValueError(f"Could not parse url in {json.dumps(native_view)}")
                active_view_urls[view_name] = view_url
            result = self.set_data_views(user_prompt=user_prompt, native_views=active_view_urls, frontend_timestamp=frontend_timestamp)
        elif method_name == "close_predictions":
            result = self.close_predictions(user_prompt=user_prompt, frontend_timestamp=frontend_timestamp)
        else:
            raise ValueError(f"Invalid method name: '{method_name}'")

        if isinstance(result, CascadeError):
            return UsageError(result.message)
        else:
            return None

    async def make_data_view(self, request: web.Request) -> web.Response:
        payload = await request.json()
        view_name = ensureJsonString(payload.get("name"))
        raw_url = ensureJsonString(payload.get("url"))
        if raw_url is None:
            return  uncachable_json_response({"error": "Missing 'url' key in payload"}, status=400)
        url = Url.parse(raw_url)
        if url is None:
            return  uncachable_json_response({"error": "Bad url in payload"}, status=400)

        with self.lock:
            view = self.cached_views.get(url)
            if view:
                return web.json_response(view.to_json_value(), status=200)
            if url.datascheme == DataScheme.PRECOMPUTED:
                for view in self.state.data_views.values():
                    if isinstance(view, RawDataView):
                        for ds in view.datasources:
                            if isinstance(ds, PrecomputedChunksDataSource) and ds.url == url:
                                stripped_view = StrippedPrecomputedView(name=view_name, session_url=self.session_url, datasource=ds)
                                return web.json_response(stripped_view.to_json_value(), status=200)
                    if isinstance(view, StrippedPrecomputedView) and view.datasource.url == url:
                        return web.json_response(view.to_json_value(), status=200)
        view = await asyncio.wrap_future(self.executor.submit(
            _try_open_data_view,
            name=view_name, url=url, session_url=self.session_url, allowed_protocols=[Protocol.HTTPS, Protocol.HTTP]
        ))
        return web.json_response(view.to_json_value(), status=200)


def _try_open_data_view(
    *, name: str, url: Url, session_url: Url, allowed_protocols: Sequence[Protocol] = (Protocol.HTTPS, Protocol.HTTP)
) -> "DataView":
    stripped_view_result = StrippedPrecomputedView.try_from_url(name=name, url=url, session_url=session_url, allowed_protocols=allowed_protocols)
    if isinstance(stripped_view_result, Exception):
        return FailedView(name=name, url=url, error_message=str(stripped_view_result))
    if isinstance(stripped_view_result, StrippedPrecomputedView):
        return stripped_view_result

    fixed_url = url.updated_with(hash_="")
    datasources_result = try_get_datasources_from_url(url=fixed_url, allowed_protocols=allowed_protocols)
    if isinstance(datasources_result, type(None)):
        return UnsupportedDatasetView(name=name, url=url)
    if isinstance(datasources_result, Exception):
        return FailedView(name=name, url=url, error_message=str(datasources_result))

    # if the requested URL matches the URL of a single returned datasource, we have to strip it out of the other scales
    if len(datasources_result) > 1:
        for ds in datasources_result:
            if isinstance(ds, PrecomputedChunksDataSource) and ds.url == url:
                return StrippedPrecomputedView(name=name, session_url=session_url, datasource=ds)

    return RawDataView(name=name, url=url, datasources=datasources_result)