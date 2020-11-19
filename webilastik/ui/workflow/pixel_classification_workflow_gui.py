from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from webilastik.ui.applet.array5d_viewer import Array5DViewer, GimpArray5DViewer


class PixelClassificationWorkflowGui(PixelClassificationWorkflow):
    def __init__(self) -> None:
        super().__init__()
        self.viewer = GimpArray5DViewer(
            source=self.pixel_classifier_applet.pixel_classifier, lanes=self.data_selection_applet.lanes
        )
