import { Filesystem, Session } from "../client/ilastik";
import { IViewerDriver } from "../drivers/viewer_driver";
import { createElement, removeElement } from "../util/misc";
import { BrushingWidget } from "./widgets/brushing_overlay/brushing_widget";
import { FeatureSelectionWidget } from "./widgets/feature_selection";
import { PredictionsExportWidget } from "./widgets/predictions_export_widget";
import { ProjectWidget } from "./widgets/project_widget";
import { DataSourceSelectionWidget } from "./widgets/datasource_selection_widget";
import { Path } from "../util/parsed_url";

export class ReferencePixelClassificationWorkflowGui{
    public readonly element: HTMLElement
    public readonly project_widget: ProjectWidget;
    public readonly feature_selection_applet: FeatureSelectionWidget
    public readonly brushing_widget: BrushingWidget;
    public readonly exporter_applet: PredictionsExportWidget;

    public readonly session: Session;
    public readonly data_selection_widget: DataSourceSelectionWidget;

    public constructor({parentElement, session, viewer_driver, projectLocation, defaultBucketName}: {
        parentElement: HTMLElement,
        session: Session,
        viewer_driver: IViewerDriver,
        projectLocation?: {fs: Filesystem, path: Path},
        defaultBucketName?: string,
    }){
        defaultBucketName = defaultBucketName || "hbp-image-service"
        this.session = session
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ReferencePixelClassificationWorkflowGui"]})

        this.project_widget = new ProjectWidget({
            parentElement: this.element, session, projectLocation, defaultBucketName, help: [
                ("You can save your project with all of its annotations to the Ebrains Data Proxy so that you can " +
                "reload it later to process more images or to refine your annotations.")
            ]
        })

        this.data_selection_widget = new DataSourceSelectionWidget({
            parentElement: this.element, session, viewer_driver, defaultBucketName, help: [
                ("Select simages from the Ebrains Data Proxy. You will be able to use those as training examples for the " +
                "pixel classifier."
                ),

                ("You can open multiple images and train the same Pixel Classifier with examples from different images, " +
                "which usually increases the robustness of the classifier.")
            ]
        });

        this.feature_selection_applet = new FeatureSelectionWidget({
            name: "feature_selection_applet",
            session: this.session,
            parentElement: this.element,
            help: [
                ("Pixel Classification uses different characteristics ('features') of your image to determine which class " +
                "each pixel should belong to. These take into account, for example, color and texture of each pixel as well " +
                "as that of the neighboring pixels. Each one of this characteristics requires some computational power, which " +
                "is why you can select only the ones that are sensible for your particular dataset."),

                ("Use the checkboxes below to select some image features and their corresponding gaussian sigma, " +
                "which will also determine the size of the neighborhood around each pixel that should be taken into " +
                "account when approximating the computation for that feature."),
            ]
        })
        this.brushing_widget = new BrushingWidget({
            applet_name: "brushing_applet",
            session: this.session,
            parentElement: this.element,
            viewer: this.data_selection_widget.viewer,
            help: [
                ("In order to classify the pixels of an image into different classes (e.g.: 'foreground' and 'background') " +
                "ilastik needs you to provide it with samples of each class. "),

                ("To do so, first select a particular resolution of your dataset (your viewer might interpolate between " +
                "multiple scales of the dataset, but ilastik operates on a single resolution). Once you've selected a " +
                "resolution to train on, you should see a new \"training\" tab at the top of the viewer. You must have the " +
                "\"training\" tab as the frontmost visible tab in order to start adding brush strokes (in neuroglancer " +
                "you can click the name of the raw data tab to hide it, for example). The status display in this applet " +
                "will show \"training on [datasource url]\" when you're in training mode "),

                ("Once you have some image features selected and at least one brush annotation, ilastik will automatically " +
                "use your examples to predict what classes the rest of your dataset should be, displaying the results in a " +
                "\"predictions\" tab. "),
            ]
        })
        this.exporter_applet = new PredictionsExportWidget({
            name: "export_applet",
            parentElement: this.element,
            session: this.session,
            viewer: this.data_selection_widget.viewer,
            defaultBucketName,
            help: [
                ("Once you trained your pixel classifier with the previous applets, you can apply it to other datasets " +
                "or even the same dataset that was used to do the training on."),

                ("To do so, select a data source by typing in the URL of the datasource in the Data Source Url field and " +
                "select a scale from the data source. This will the source of data that will be processed with the pixel " +
                "classifier that you've just trained. "),

                ("Then, configure a Data Sink, i.e., a destination that will receive the results of the pixel classification. " +
                "For now, webilastik will only export to ebrains' data-proxy buckets; Fill in the name of the bucket and then " +
                "the prefix (i.e.: path within the bucket) where the results in Neuroglancer's precomputed chunks format " +
                "should be written to."),

                ("Finally, click export button and eventually a new job shall be created if all the parameters were filled" +
                "in correctly."),

                ("You'll be able to find your results in the data-proxy GUI, in a url that looks something like this:"),

                ("https://data-proxy.ebrains.eu/your-bucket-name?prefix=your/selected/prefix"),
            ]
        })
    }

    public destroy(){
        //FIXME: close predictions and stuff
        this.brushing_widget.destroy()
        this.data_selection_widget.destroy()
        removeElement(this.element)
    }
}
