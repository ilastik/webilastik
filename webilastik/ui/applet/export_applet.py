from typing import Sequence

from ndstructs.datasource import DataSource, DataSourceSlice

from webilastik.operator import Operator
from webilastik.ui.applet  import Applet, Slot, CONFIRMER
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier
from webilastik.ui.applet.data_selection_applet import ILane

class ExportApplet(Applet):
    """Exports the outputs of an operator created by an upstream applet."""
    def __init__(self, producer: Slot[Operator], lanes: Slot[Sequence[ILane]]):
        self.producer = producer
        self.lanes = lanes
        super().__init__()

    def export_all(self) -> None:
        producer_op = self.producer()
        if not producer_op:
            raise ValueError("No producer from upstream")
        for lane in self.lanes() or []:
            #FIXME: get format/mapper/orchestrator/scheduler/whatever from slots or method args
            data_slice = DataSourceSlice(lane.get_raw_data())
            for slc in data_slice.get_tiles():
                #FIXME save this with a DataSink
                print(f"Computing on {data_slice} with producer {producer_op}")
                producer_op.compute(slc)