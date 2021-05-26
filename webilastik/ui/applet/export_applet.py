from typing import Sequence, List, Generic, Tuple, TypeVar, Dict
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

LANE = TypeVar("LANE", bound=ILane)
PRODUCER = TypeVar("PRODUCER", bound=Operator[DataRoi, Array5D], covariant=True)
class ExportApplet(Applet, Generic[PRODUCER]):
    """Exports the outputs of an operator created by an upstream applet."""
    def __init__(
        self, name: str, producer: Slot[PRODUCER], num_workers: int = max(1, multiprocessing.cpu_count() - 1)
    ):
        self.producer = producer
        self._executors = [ProcessPoolExecutor(max_workers=1) for _ in range(num_workers)]
        super().__init__(name=name)

    def __del__(self):
        for idx, executor in enumerate(self._executors):
            print(f"===> Shutting down executor {idx} from {self}")
            executor.shutdown()

    async def async_compute(self, roi: DataRoi):# -> Array5D:
        loop = asyncio.get_event_loop()
        exec_idx = hash(roi) % len(self._executors)
        producer_op = self.producer()
        executor = self._executors[exec_idx]
        return await loop.run_in_executor(executor, do_async_compute, producer_op, roi)

    def compute(self, roi: DataRoi) -> Array5D:
        producer_op = self.producer()
        tile_shape = roi.datasource.tile_shape.updated(c=roi.datasource.shape.c)

        slc_batches : Dict[int, List[DataRoi]] = defaultdict(list)
        for slc in roi.get_tiles(tile_shape=tile_shape):
            batch_idx = hash(slc) % len(self._executors)
            slc_batches[batch_idx].append(slc)

        result_batch_futures = []
        for idx, batch in slc_batches.items():
            executor = self._executors[idx]
            result_batch_futures.append(executor.submit(do_worker_compute, (producer_op, batch)))

        tiles : Sequence[Array5D] = [tile for future in result_batch_futures for tile in future.result()]

        return Array5D.combine(tiles)

    @property
    def ilp_data(self):
        return {
            "OutputFilenameFormat": "{dataset_dir}/{nickname}_{result_type}",
            "OutputFormat": "hdf5",
            "OutputInternalPath": "exported_data",
            "StorageVersion": "0.1",
        }

#these functions must be top level because ProcessPool doesn't like object methods
def do_async_compute(op: Operator[DataRoi, Array5D], roi: DataRoi) -> Array5D:
    pred_tile = op.compute(roi)
    return pred_tile


def do_worker_compute(slice_batch: Tuple[Operator[DataRoi, Array5D], Sequence[DataRoi]]) -> List[Array5D]:
    op = slice_batch[0]
    out = []
    for datasource_slc in slice_batch[1]:
        pred_tile = op.compute(datasource_slc)
        out.append(pred_tile)
    return out
