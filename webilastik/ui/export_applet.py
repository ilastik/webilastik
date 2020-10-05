from typing import List, Optional

from ndstructs.datasource import DataSource, DataSourceSlice

from webilastik.operator import Operator
from webilastik.ui.applet  import Applet, Slot, CONFIRMER
from webilastik.annotations.annotation import Annotation
from webilastik.features.ilp_filter import IlpFilter
from webilastik.classifiers.pixel_classifier import PixelClassifier, VigraPixelClassifier

class ExportApplet(Applet):
    def __init__(self, operator: Slot[Operator], datasources: Slot[List[DataSource]]):
        self.operator = operator
        self.datasources = datasources
        super().__init__()

    def export_all(self) -> None:
        operator = self.operator()
        if not operator:
            raise ValueError("No operator from upstream")
        for ds in self.datasources() or []:
            #FIXME: get format/mapper/orchestrator/scheduler/whatever from slots or method args
            data_slice = DataSourceSlice(ds)
            for slc in data_slice.get_tiles():
                #FIXME save this with a DataSink
                print(f"Computing on {data_slice} with operator {operator}")
                operator.compute(slc)