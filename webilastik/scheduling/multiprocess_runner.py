from typing import Hashable, Optional, Sequence, List, Generic, Tuple, TypeVar, Dict, Callable, Coroutine
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from collections import defaultdict
import asyncio

from ndstructs import Array5D, Interval5D, Shape5D
from ndstructs.datasource import DataSource, DataRoi
from numpy.lib.shape_base import tile

from webilastik.operator import Operator
from webilastik.ui.applet  import Applet, Slot, CONFIRMER
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier
from webilastik.ui.applet.data_selection_applet import ILane

IN = TypeVar("IN", bound=Hashable)
OUT = TypeVar("OUT")
class MultiprocessRunner:
    """Exports the outputs of an operator created by an upstream applet."""
    def __init__(self, num_workers: Optional[int] = None):
        max_workers = num_workers or max(1, multiprocessing.cpu_count() - 1)
        self._executors = [ProcessPoolExecutor(max_workers=1) for _ in range(max_workers)]

    def __del__(self):
        for idx, executor in enumerate(self._executors):
            print(f"===> Shutting down executor {idx} from {self}")
            executor.shutdown()

    async def async_compute(self, target: Callable[[IN], OUT], arg: IN) -> OUT:
        loop = asyncio.get_event_loop()
        exec_idx = hash(arg) % len(self._executors)
        executor = self._executors[exec_idx]
        result : OUT =  await loop.run_in_executor(executor, target, arg)
        return result

    def compute(self, target: Callable[[IN], OUT], arg: IN) -> OUT:
        exec_idx = hash(arg) % len(self._executors)
        executor = self._executors[exec_idx]
        return executor.submit(target, arg).result()

class PixelPredictionsRunner:
    def __init__(self, *, classifier: PixelClassifier[IlpFilter], runner: MultiprocessRunner):
        self.runner = runner
        self.classifier = classifier
