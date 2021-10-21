from ndstructs.array5D import Array5D
from ndstructs.datasink.PrecomputedChunksDataSink import PrecomputedChunksScaleDataSink
from webilastik.datasource.DataRoi import DataRoi
from webilastik.scheduling.job import Job
from webilastik.ui.applet import Applet
from webilastik.operator import Operator

class ImageExportJob(Job[DataRoi, Array5D]):
    def __init__(
        self, *, name: str, roi: DataRoi, operator: Operator[DataRoi, Array5D], sink: PrecomputedChunksScaleDataSink
    ):
        super().__init__(
            name=name, target=operator.compute, steps=roi.split(sink.)
        )

class ImageExportApplet(Applet):
    def __init__(self):
        pass
