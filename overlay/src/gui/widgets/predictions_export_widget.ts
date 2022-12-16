import { Applet } from '../../client/applets/applet';
import { JsonValue } from '../../util/serialization';
import { assertUnreachable, createElement, createFieldset, createInput, createInputParagraph, createTable } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { BucketFs, Color, FsDataSource, Filesystem, FsDataSink, Session } from '../../client/ilastik';
import { CssClasses } from '../css_classes';
import { ErrorPopupWidget } from './popup';
import {
    ExportJobDto,
    LabelHeaderDto,
    OpenDatasinkJobDto,
    PixelClassificationExportAppletStateDto,
    PrecomputedChunksSinkDto,
    StartPixelProbabilitiesExportJobParamsDto,
    StartSimpleSegmentationExportJobParamsDto
} from '../../client/dto';
import { PopupSelect } from './selector_widget';
import { Viewer } from '../../viewer/viewer';
import { DataSourceListWidget } from './list_widget';
import { DatasinkConfigWidget } from './datasink_builder_widget';
import { DataType } from '../../util/precomputed_chunks';
import { FileLocationPatternInputWidget } from './file_location_input';
import { Select } from './input_widget';
import { Label, Paragraph, Span } from './widget';

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
    public static fromDto(message: LabelHeaderDto): LabelHeader{
        return new LabelHeader(message.name, Color.fromDto(message.color))
    }
    public toDto(): LabelHeaderDto{
        return new LabelHeaderDto({name: this.name, color: this.color.toDto()})
    }
}

class PixelClassificationExportAppletState{
    jobs: Array<ExportJobDto | OpenDatasinkJobDto>
    populated_labels: LabelHeader[] | undefined
    datasource_suggestions: FsDataSource[]

    constructor(params: {
        jobs: Array<ExportJobDto | OpenDatasinkJobDto>
        populated_labels: LabelHeaderDto[] | undefined
        datasource_suggestions: FsDataSource[]
    }){
        this.jobs = params.jobs
        this.populated_labels = params.populated_labels?.map(msg => LabelHeader.fromDto(msg))
        this.datasource_suggestions = params.datasource_suggestions
    }

    public static fromDto(message: PixelClassificationExportAppletStateDto): PixelClassificationExportAppletState{
        return new this({
            jobs: message.jobs,
            datasource_suggestions: (message.datasource_suggestions || []).map(msg => FsDataSource.fromDto(msg)), //FIXME?
            populated_labels: message.populated_labels
        })
    }
}

export class PredictionsExportWidget extends Applet<PixelClassificationExportAppletState>{
    private viewer: Viewer

    public readonly element: HTMLElement;
    private jobsDisplay: HTMLDivElement;
    private labelSelectorContainer: HTMLParagraphElement;
    private labelToExportSelector: PopupSelect<LabelHeader> | undefined;
    private exportModeSelector: Select<"pixel probabilities" | "simple segmentation">;
    private datasourceListWidget: DataSourceListWidget;

    public constructor({name, parentElement, session, help, viewer}: {
        name: string, parentElement: HTMLElement, session: Session, help: string[], viewer: Viewer
    }){
        super({
            name,
            session,
            deserializer: (data: JsonValue) => {
                const message = PixelClassificationExportAppletStateDto.fromJsonValue(data)
                if(message instanceof Error){
                    throw `FIXME!!: ${message.message}`
                }
                return PixelClassificationExportAppletState.fromDto(message)
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.viewer = viewer
        this.element = new CollapsableWidget({display_name: "Export Predictions", parentElement, help}).element
        this.element.classList.add("ItkPredictionsExportApplet")

        new Paragraph({parentElement: this.element, children: [
            new Label({parentElement: undefined, innerText: "Export mode: "}),
            this.exportModeSelector = new Select<"pixel probabilities" | "simple segmentation">({
                popupTitle: "Select an export mode",
                parentElement: undefined,
                options: ["pixel probabilities", "simple segmentation"], //FIXME?
                renderer: (opt) => new Span({parentElement: undefined, innerText: opt}),
            })
        ]})

        const datasourceFieldset = createFieldset({parentElement: this.element, legend: "Input Datasets:"})
        this.datasourceListWidget = new DataSourceListWidget({parentElement: datasourceFieldset, session: this.session})

        const datasinkFieldset = createFieldset({legend: "Output: ", parentElement: this.element})
        const fileLocationInputWidget = new FileLocationPatternInputWidget({
            parentElement: datasinkFieldset, defaultBucketName: "hbp-image-service"
        })
        const datasinkConfigWidget = new DatasinkConfigWidget({parentElement: datasinkFieldset})

        this.labelSelectorContainer = createElement({tagName: "p", parentElement: this.element});

        createInputParagraph({
            inputType: "button", value: "Start Export Jobs", parentElement: this.element, onClick: () => {
                const exportMode = this.exportModeSelector.value
                let dtype: DataType;
                let numChannels: number;
                if(exportMode == "pixel probabilities"){
                    dtype = "float32"
                    numChannels = this.labelToExportSelector?.options.length || 0 //FIXME: maybe just save the number of labels in state?
                }else if(exportMode == "simple segmentation"){
                    dtype = "uint8"
                    numChannels = 3
                }else{
                    assertUnreachable(exportMode)
                }

                if(numChannels == 0){
                    new ErrorPopupWidget({message: "Missing or wrong parameters"})
                    return
                }

                for(let job_index=0; job_index < this.datasourceListWidget.value.length; job_index++){
                    const datasource = this.datasourceListWidget.value[job_index]
                    let fileLocation = fileLocationInputWidget.tryGetLocation({
                        item_index: job_index, name: datasource.url.path.name
                    });
                    if(fileLocation === undefined){
                        new ErrorPopupWidget({message: "Unexpected bad file location"}) //FIXME? Shouldn't this be impossible?
                        return
                    }
                    if(!(datasource instanceof FsDataSource)){
                        continue
                    }
                    const datasink = datasinkConfigWidget.tryMakeDataSink({
                        filesystem: fileLocation.filesystem,
                        path: fileLocation.path,
                        dtype,
                        interval: datasource.interval.updated({c: [0, numChannels]}),
                        resolution: datasource.spatial_resolution,
                        tile_shape: datasource.tile_shape.updated({c: numChannels})
                    })
                    if(!datasource || !datasink){
                        new ErrorPopupWidget({message: "Missing export parameters"})
                        return
                    }
                    if(this.exportModeSelector.value == "pixel probabilities"){
                        this.doRPC("launch_pixel_probabilities_export_job", new StartPixelProbabilitiesExportJobParamsDto({
                            datasource: datasource.toDto(), datasink: datasink.toDto()
                        }))
                    }else if(this.exportModeSelector.value == "simple segmentation"){
                        const label_header = this.labelToExportSelector?.value;
                        if(!label_header){
                            new ErrorPopupWidget({message: "Missing export parameters"})
                            return
                        }
                        this.doRPC("launch_simple_segmentation_export_job", new StartSimpleSegmentationExportJobParamsDto({
                            datasource: datasource.toDto(), datasink: datasink.toDto(), label_header: label_header.toDto()
                        }))
                    }else{
                        assertUnreachable(this.exportModeSelector.value)
                    }
                }
            }
        })

        this.jobsDisplay = createElement({tagName: "div", parentElement: this.element});
    }

    protected onNewState(new_state: PixelClassificationExportAppletState){
        this.jobsDisplay.innerHTML = ""

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

        if(new_state.jobs.length == 0){
            return
        }
        createTable({
            parentElement: this.jobsDisplay,
            cssClasses: [CssClasses.ItkTable],
            title: {header: "Jobs:"},
            headers: {name: "Name", status: "Status", progress: "Progress"},
            rows: new_state.jobs.map(job => {
                let progressColumnContents: HTMLElement | string = job.num_args === undefined ? "unknwown" : `${Math.round(job.num_completed_steps / job.num_args * 100)}%`
                if(job.status == 'succeeded' && job instanceof ExportJobDto){
                    progressColumnContents = createElement({tagName: "span", parentElement: undefined})
                    const outputFs = Filesystem.fromDto(job.datasink.filesystem);
                    if(outputFs instanceof BucketFs && job.datasink instanceof PrecomputedChunksSinkDto){ //FIXME
                        const dataProxyLink = createElement({tagName: "a", parentElement: progressColumnContents, innerText: "Open in Data Proxy"})
                        let dataProxyPrefixParam = job.datasink.path.replace(/^\//, "")
                        if(job.datasink instanceof PrecomputedChunksSinkDto){
                            dataProxyPrefixParam += "/"
                        }
                        dataProxyLink.href = `https://data-proxy.ebrains.eu/${outputFs.bucket_name}?prefix=${dataProxyPrefixParam}`
                        dataProxyLink.target = "_blank"
                        dataProxyLink.rel = "noopener noreferrer"
                    }
                    createInput({inputType: "button", parentElement: progressColumnContents, value: "Open in Viewer", onClick: () => {
                        this.viewer.openDataViewFromDataSource(FsDataSink.fromDto(job.datasink).toDataSource())
                    }})
                }
                return{
                    name: job.name,
                    status: job.status,
                    progress: progressColumnContents
                }
            })
        })
    }
}
