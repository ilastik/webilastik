from typing import Sequence, List, Generic, Tuple, TypeVar, Dict
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict

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
class ExportApplet(Applet, Generic[LANE, PRODUCER]):
    """Exports the outputs of an operator created by an upstream applet."""
    def __init__(self, name: str, producer: Slot[PRODUCER], lanes: Slot[Sequence[LANE]], num_workers: int = 4):
        self.producer = producer
        self.lanes = lanes
        self._executors = [ProcessPoolExecutor(max_workers=1) for i in range(num_workers)]
        super().__init__(name=name)

    def __del__(self):
        for idx, executor in enumerate(self._executors):
            print(f"===> Shutting down executor {idx} from {self}")
            executor.shutdown()

    def export_all(self) -> None:
        producer_op = self.producer()
        if not producer_op:
            raise ValueError("No producer from upstream")
        for lane in self.lanes() or []:
            data_slice = DataRoi(lane.get_raw_data())
            # FIXME: Maybe the provider operator should suggest a sensible tile shape?
            tile_shape = data_slice.datasource.tile_shape.updated(c=data_slice.datasource.shape.c)

            #FIXME: get format/mapper/orchestrator/scheduler/whatever from slots or method args
            for slc in data_slice.get_tiles(tile_shape=tile_shape):
                #FIXME save this with a DataSink
                print(f"Computing on {data_slice} with producer {producer_op}")
                producer_op.compute(slc)

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

        return tiles[0].combine(tiles[1:])

    @property
    def ilp_data(self):
        return {
            "OutputFilenameFormat": "{dataset_dir}/{nickname}_{result_type}",
            "OutputFormat": "hdf5",
            "OutputInternalPath": "exported_data",
            "StorageVersion": "0.1",
        }


def do_worker_compute(slice_batch: Tuple[Operator[DataRoi, Array5D], Sequence[DataRoi]]) -> List[Array5D]:
    op = slice_batch[0]
    out = []
    for datasource_slc in slice_batch[1]:
        pred_tile = op.compute(datasource_slc)
        out.append(pred_tile)
    return out
