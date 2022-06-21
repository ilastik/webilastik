import threading
from typing import Callable, Any
import time

from ndstructs.utils.json_serializable import JsonObject

from webilastik.ui.applet import InertApplet, NoSnapshotApplet
from webilastik.ui.usage_error import UsageError
from webilastik.ui.applet.ws_applet import WsApplet




Interaction = Callable[[], "UsageError | None"]

class SessionApplet(WsApplet, InertApplet, NoSnapshotApplet):
    def __init__(
        self,
        *,
        name: str,
        remaining_seconds: int,
        update_interval_seconds: int = 1,
        on_changed: Callable[["SessionApplet"], Any]
    ) -> None:
        self.remaining_seconds: int
        self._update_interval_seconds = update_interval_seconds
        self._on_changed = on_changed
        self._stopped = False
        self._counting_thread = threading.Thread(group=None, target=self._do_count)
        super().__init__(name)

    def _do_count(self):
        while not self._stopped and self.remaining_seconds > 0:
            time.sleep(self._update_interval_seconds)
            self.remaining_seconds -= max(0, self._update_interval_seconds)

    def _get_json_state(self) -> JsonObject:
        return {"remaining_seconds": self.remaining_seconds}