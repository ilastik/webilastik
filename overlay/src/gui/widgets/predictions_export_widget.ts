import { Applet } from '../../client/applets/applet';
import { JsonValue } from '../../util/serialization';
import { assertUnreachable, createElement, createInput, createInputParagraph, createTable } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { Color, DataSource, Session } from '../../client/ilastik';
import { CssClasses } from '../css_classes';
import { ErrorPopupWidget, InputPopupWidget } from './popup';
import {
    JobMessage,
    LabelHeaderMessage,
    PixelClassificationExportAppletStateMessage,
    StartPixelProbabilitiesExportJobParamsMessage,
    StartSimpleSegmentationExportJobParamsMessage
} from '../../client/message_schema';
import { PopupSelect, SelectorWidget } from './selector_widget';
import { DataSourceInput } from './datasource_input';
import { PrecomputedChunksScale_DataSink_Input } from './precomputed_chunks_scale_datasink_input';

const sink_creation_stati = ["pending", "running", "cancelled", "failed", "succeeded"] as const;
export type SinkCreationStatus = typeof sink_creation_stati[number];
export function ensureSinkCreationStatus(value: string): SinkCreationStatus{
    const variant = sink_creation_stati.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid sink creation status: ${value}`)
    }
    return variant
}

class LabelHeader{
    constructor(public readonly name: string, public readonly color: Color){
    }
    public static fromMessage(message: LabelHeaderMessage): LabelHeader{
        return new LabelHeader(message.name, Color.fromMessage(message.color))
    }
    public toMessage(): LabelHeaderMessage{
        return new LabelHeaderMessage({name: this.name, color: this.color.toMessage()})
    }
}

class PixelClassificationExportAppletState{
    jobs: Array<JobMessage>
    populated_labels: LabelHeader[] | undefined
    datasource_suggestions: DataSource[]

    constructor(params: {
        jobs: Array<JobMessage>
        populated_labels: LabelHeaderMessage[] | undefined
        datasource_suggestions: DataSource[]
    }){
        this.jobs = params.jobs
        this.populated_labels = params.populated_labels?.map(msg => LabelHeader.fromMessage(msg))
        this.datasource_suggestions = params.datasource_suggestions
    }

    public static fromMessage(message: PixelClassificationExportAppletStateMessage): PixelClassificationExportAppletState{
        return new this({
            jobs: message.jobs,
            datasource_suggestions: (message.datasource_suggestions || []).map(msg => DataSource.fromMessage(msg)), //FIXME?
            populated_labels: message.populated_labels
        })
    }
}

export class PredictionsExportWidget extends Applet<PixelClassificationExportAppletState>{
    public readonly element: HTMLElement;
    jobsDisplay: HTMLDivElement;
    exportModeSelector: PopupSelect<"pixel probabilities" | "simple segmentation">;
    datasinkInput: PrecomputedChunksScale_DataSink_Input;
    datasourceInput: DataSourceInput;
    labelSelectorContainer: HTMLParagraphElement;
    labelToExportSelector: PopupSelect<LabelHeader> | undefined;
    inputSuggestionsButtonContainer: HTMLSpanElement;

    public constructor({name, parentElement, session, help}: {
        name: string, parentElement: HTMLElement, session: Session, help: string[]
    }){
        super({
            name,
            session,
            deserializer: (data: JsonValue) => {
                const message = PixelClassificationExportAppletStateMessage.fromJsonValue(data)
                if(message instanceof Error){
                    throw `FIXME!!: ${message.message}`
                }
                return PixelClassificationExportAppletState.fromMessage(message)
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })

        this.element = new CollapsableWidget({display_name: "Export Predictions", parentElement, help}).element
        this.element.classList.add("ItkPredictionsExportApplet")

        const exportModeContainer = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: exportModeContainer, innerText: "Export mode: "})
        this.exportModeSelector = new PopupSelect<"pixel probabilities" | "simple segmentation">({
            popupTitle: "Select an export mode",
            parentElement: exportModeContainer,
            options: ["pixel probabilities", "simple segmentation"], //FIXME?
            optionRenderer: (args) => createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option}),
            onChange: () => this.refreshInputs(),
        })

        const datasourceFieldset = createElement({tagName: "fieldset", parentElement: this.element})
        createElement({tagName: "legend", parentElement: datasourceFieldset, innerText: "Input Data:"})
        this.datasourceInput = new DataSourceInput({
            parentElement: datasourceFieldset,
            session,
            onChanged: (ds: DataSource | undefined) => {
                if(!ds){
                    this.datasinkInput.sinkShapeInput.xInput.value = undefined
                    this.datasinkInput.sinkShapeInput.yInput.value = undefined
                    this.datasinkInput.sinkShapeInput.zInput.value = undefined
                    this.datasinkInput.sinkShapeInput.tInput.value = undefined

                    this.datasinkInput.tileShapeInput.xInput.value = undefined
                    this.datasinkInput.tileShapeInput.yInput.value = undefined
                    this.datasinkInput.tileShapeInput.zInput.value = undefined
                    this.datasinkInput.tileShapeInput.tInput.value = undefined
                }else{
                    this.datasinkInput.sinkShapeInput.xInput.value = ds.shape.x
                    this.datasinkInput.sinkShapeInput.yInput.value = ds.shape.y
                    this.datasinkInput.sinkShapeInput.zInput.value = ds.shape.z
                    this.datasinkInput.sinkShapeInput.tInput.value = ds.shape.t

                    this.datasinkInput.tileShapeInput.xInput.value = ds.tile_shape.x
                    this.datasinkInput.tileShapeInput.yInput.value = ds.tile_shape.y
                    this.datasinkInput.tileShapeInput.zInput.value = ds.tile_shape.z
                    this.datasinkInput.tileShapeInput.tInput.value = ds.tile_shape.t
                }
                this.datasinkInput.resolutionInput.value = ds?.spatial_resolution
            }
        })
        this.inputSuggestionsButtonContainer = createElement({tagName: "span", parentElement: datasourceFieldset})


        const datasinkFieldset = createElement({tagName: "fieldset", parentElement: this.element})
        createElement({tagName: "legend", parentElement: datasinkFieldset, innerText: "Output: "})
        this.datasinkInput = new PrecomputedChunksScale_DataSink_Input({
            parentElement: datasinkFieldset,
            disableDataType: true,
            disableShape: true,
            disableTileShape: true,
            disableEncoding: true,
            disableResolution: true,
        })

        this.labelSelectorContainer = createElement({tagName: "p", parentElement: this.element});

        createInputParagraph({
            inputType: "button", value: "Start Export Job", parentElement: this.element, onClick: () => {
                const datasource = this.datasourceInput.value
                const datasink = this.datasinkInput.value
                if(!datasource || !datasink){
                    new ErrorPopupWidget({message: "Missing export parameters"})
                    return
                }
                if(this.exportModeSelector.value == "pixel probabilities"){
                    this.doRPC("launch_pixel_probabilities_export_job", new StartPixelProbabilitiesExportJobParamsMessage({
                        datasource: datasource.toMessage(), datasink: datasink
                    }))
                }else if(this.exportModeSelector.value == "simple segmentation"){
                    const label_header = this.labelToExportSelector?.value;
                    if(!label_header){
                        new ErrorPopupWidget({message: "Missing export parameters"})
                        return
                    }
                    this.doRPC("launch_simple_segmentation_export_job", new StartSimpleSegmentationExportJobParamsMessage({
                        datasource: datasource.toMessage(), datasink: datasink, label_header: label_header.toMessage()
                    }))
                }else{
                    assertUnreachable(this.exportModeSelector.value)
                }
            }
        })

        this.jobsDisplay = createElement({tagName: "div", parentElement: this.element});
        this.refreshInputs()
    }

    private refreshInputs = () => {
        const exportMode = this.exportModeSelector.value
        if(exportMode == 'pixel probabilities'){
            this.datasinkInput.dataTypeSelector.value = "float32"
            this.datasinkInput.tileShapeInput.cInput.value = this.labelToExportSelector?.options.length
            this.datasinkInput.sinkShapeInput.cInput.value = this.labelToExportSelector?.options.length
            this.labelSelectorContainer.style.display = "none"
        }else if (exportMode == "simple segmentation"){
            this.datasinkInput.dataTypeSelector.value = "uint8"
            this.datasinkInput.tileShapeInput.cInput.value = 3
            this.datasinkInput.sinkShapeInput.cInput.value = 3
            this.labelSelectorContainer.style.display = "block"
        }else{
            assertUnreachable(exportMode)
        }
    }

    protected onNewState(new_state: PixelClassificationExportAppletState){
        this.jobsDisplay.innerHTML = ""

        this.inputSuggestionsButtonContainer.innerHTML = ""
        createInput({
            inputType: "button",
            parentElement: this.inputSuggestionsButtonContainer,
            value: "Use an Annotated Dataset",
            disabled: new_state.datasource_suggestions.length == 0,
            onClick: () => new InputPopupWidget<DataSource>({
                title: "Pick an annotated dataset as input",
                inputWidgetFactory: (parentElement) => {
                    return new SelectorWidget({
                        parentElement: parentElement,
                        options: new_state.datasource_suggestions,
                        optionRenderer: (args) => createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option.getDisplayString()}),
                    })
                },
                onConfirm: (ds) => {
                    this.datasourceInput.value = ds
                },
            })
        })

        let previousLabelSelection = this.labelToExportSelector?.value;
        this.labelSelectorContainer.innerHTML = ""
        createElement({tagName: "label", parentElement: this.labelSelectorContainer, innerText: "Select a label to segment: "})
        if(new_state.populated_labels){
            this.labelToExportSelector = new PopupSelect<LabelHeader>({
                parentElement: this.labelSelectorContainer,
                popupTitle: "Select a label to segment",
                options: new_state.populated_labels,
                comparator: (label1, label2) => label1.name == label2.name,
                optionRenderer: (args) => {
                    createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option.name + " "})
                    createElement({tagName: "span", parentElement: args.parentElement, innerText: "🖌️", inlineCss: {
                        backgroundColor: args.option.color.hexCode,
                        padding: "2px",
                        border: "solid 1px black"
                    }})
                },
            })
            if(previousLabelSelection){
                for(let labelHeader of new_state.populated_labels){
                    if(labelHeader.name == previousLabelSelection.name || labelHeader.color.equals(previousLabelSelection.color)){
                        this.labelToExportSelector.value = labelHeader
                        break
                    }
                }
            }
        }else{
            createElement({tagName: "span", parentElement: this.labelSelectorContainer, innerText: "No populated labels"})
        }

        if(new_state.jobs.length > 0){
            createTable({
                parentElement: this.jobsDisplay,
                cssClasses: [CssClasses.ItkTable],
                title: {header: "Jobs:"},
                headers: {name: "Name", status: "Status", progress: "Progress"},
                rows: new_state.jobs.map(job => ({
                    name: job.name,
                    status: job.status,
                    progress: job.num_args === undefined ? "unknwown" : `${Math.round(job.num_completed_steps / job.num_args * 100)}%`
                }))
            })
        }

        this.refreshInputs()
    }
}
