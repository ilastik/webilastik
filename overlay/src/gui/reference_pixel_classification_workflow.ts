import { Session } from "../client/ilastik";
import { IViewerDriver } from "../drivers/viewer_driver";
import { createElement, removeElement } from "../util/misc";
import { PredictingWidget } from "./widgets/predicting_widget";
import { BrushingWidget } from "./widgets/brushing_overlay/brushing_widget";
import { FeatureSelectionWidget } from "./widgets/feature_selection";
import { Viewer } from "../viewer/viewer";
import { PredictionsExportApplet } from "./widgets/predictions_export_applet";

export class ReferencePixelClassificationWorkflowGui{
    public readonly element: HTMLElement
    public readonly feature_selection_applet: FeatureSelectionWidget
    public readonly brushing_applet: BrushingWidget;
    public readonly live_updater: PredictingWidget;
    public readonly exporter_applet: PredictionsExportApplet;

    public readonly session: Session;
    public readonly viewer: Viewer;

    public constructor({parentElement, session, viewer_driver}: {
        parentElement: HTMLElement,
        session: Session,
        viewer_driver: IViewerDriver,
    }){
        this.session = session
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ReferencePixelClassificationWorkflowGui"]})
        this.viewer = new Viewer({driver: viewer_driver, ilastik_session: session})

        this.feature_selection_applet = new FeatureSelectionWidget({
            name: "feature_selection_applet",
            session: this.session,
            parentElement: this.element,
        })
        this.brushing_applet = new BrushingWidget({
            session: this.session,
            parentElement: this.element,
            viewer: this.viewer,
        })
        this.live_updater = new PredictingWidget({
            session: this.session,
            viewer: this.viewer
        })
        this.exporter_applet = new PredictionsExportApplet({
            name: "export_applet",
            parentElement: this.element,
            session: this.session
        })
    }

    public destroy(){
        //FIXME: close predictions and stuff
        this.brushing_applet.destroy()
        this.viewer.destroy()
        removeElement(this.element)
    }
}
