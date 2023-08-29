import { Filesystem, Session } from "../client/ilastik";
import { IViewerDriver } from "../drivers/viewer_driver";
import { createElement, removeElement } from "../util/misc";
import { BrushingWidget } from "./widgets/brushing_overlay/brushing_widget";
import { FeatureSelectionApplet } from "./widgets/feature_selection_applet";
import { PredictionsExportWidget } from "./widgets/predictions_export_widget";
import { ProjectWidget } from "./widgets/project_widget";
import { DataSourceSelectionWidget } from "./widgets/datasource_selection_widget";
import { Path } from "../util/parsed_url";
import { ExportPattern } from "../util/export_pattern";
import { Paragraph, VideoWidget } from "./widgets/widget";
import { CssClasses } from "./css_classes";

export class ReferencePixelClassificationWorkflowGui{
    public readonly element: HTMLElement
    public readonly project_widget: ProjectWidget;
    public readonly feature_selection_applet: FeatureSelectionApplet
    public readonly brushing_widget: BrushingWidget;
    public readonly exporter_applet: PredictionsExportWidget;

    public readonly session: Session;
    public readonly data_selection_widget: DataSourceSelectionWidget;

    public constructor({
        parentElement, session, viewer_driver, projectLocation, defaultBucketName, defaultBucketPath=Path.root, outputPathPattern,
    }: {
        parentElement: HTMLElement,
        session: Session,
        viewer_driver: IViewerDriver,
        projectLocation?: {fs: Filesystem, path: Path},
        defaultBucketName?: string,
        defaultBucketPath?: Path,
        outputPathPattern?: ExportPattern,
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
            parentElement: this.element, session, viewer_driver, defaultBucketName, defaultBucketPath, help: [
                ("Select simages from the Ebrains Data Proxy. You will be able to use those as training examples for the " +
                "pixel classifier."
                ),

                ("You can open multiple images and train the same Pixel Classifier with examples from different images, " +
                "which usually increases the robustness of the classifier.")
            ]
        });

        this.feature_selection_applet = new FeatureSelectionApplet({
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
                ("In order to classify the pixels of an image into different classes (e.g.: 'Foreground is blue' and 'Background is yellow') " +
                "ilastik needs you to provide it with samples of each class. YOu do so by brushing over your sample datasets."),

                new Paragraph({parentElement: undefined, innerText: "Selecting an image to train on", cssClasses: [CssClasses.ItkHelpTextHeading]}),
                ("Use the 'Training Images' widget to open sample datasets and use the visibility controls to select one to brush on."),

                new Paragraph({parentElement: undefined, innerText: "Managing Labels", cssClasses: [CssClasses.ItkHelpTextHeading]}),
                ("You can rename Labels, change their colors, create and delete them."),
                ("To change a label's name, click the text input field with its name and type a different one."),
                ("To change a label's color, click colored box to he left of the label's name and pick a different color."),
                ("To delete label along with every brush stroke within it, click the 'x' button to the right of its name."),

                new Paragraph({parentElement: undefined, innerText: "Training the classifier", cssClasses: [CssClasses.ItkHelpTextHeading]}),
                new VideoWidget({
                    parentElement: undefined, sources: [Path.parse("/public/videos/help_training.webm")], cssClasses: [CssClasses.ItkHelpVideo]
                }),
                ("1- Select an image from the 'Input Images' widget to train on by making it visible via the visibility buttons."),
                ("2- Select a label color by either clicking the 'Select' button next to that label's name or by choosing from the "+
                 "dropdown labeled 'Current Label."),
                ("3- Hold 'Alt' with the mouse over your image and you should see the mouse cursor turn into a pencil. Click and drag to " +
                "draw a brush stroke, which marks those pixels under the brush stroke as belonging to that particular label."),
                ("3.1 - If you make a mistake, you can delete a brush stroke by finding it in the brush stroke list and clicking the 'x' " +
                 "button right next to its coordinates"),
                ("4 - Click the 'Live Update' toggle button to get live feedback"),
                ("5 - Repeat step 3 until you are happy with the predictions generated by the classifier. You can also modify the feature " +
                "selection in the 'Image Features' applet to see if more features produce better results or fewer features make for faster " +
                "computations."),
            ]
        })
        this.exporter_applet = new PredictionsExportWidget({
            name: "export_applet",
            parentElement: this.element,
            session: this.session,
            viewer: this.data_selection_widget.viewer,
            defaultBucketName,
            inputBucketPath: defaultBucketPath,
            outputPathPattern,
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
