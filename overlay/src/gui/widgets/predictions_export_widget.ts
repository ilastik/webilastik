import { Applet } from '../../client/applets/applet';
import { JsonValue } from '../../util/serialization';
import { assertUnreachable, createElement, createFieldset } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { BucketFs, Color, FsDataSource, FsDataSink, Session, PrecomputedChunksSink, Shape5D, Filesystem } from '../../client/ilastik';
import { CssClasses } from '../css_classes';
import { ErrorPopupWidget } from './popup';
import {
    CreateDziPyramidJobDto,
    ExportJobDto,
    LabelHeaderDto,
    OpenDatasinkJobDto,
    PixelClassificationExportAppletStateDto,
    StartPixelProbabilitiesExportJobParamsDto,
    StartSimpleSegmentationExportJobParamsDto,
    ZipJobDto
} from '../../client/dto';
import { Viewer } from '../../viewer/viewer';
import { DataSourceListWidget } from './list_widget';
import { DatasinkConfigWidget } from './datasink_builder_widget';
import { DataType } from '../../util/precomputed_chunks';
import { FileLocationPatternInputWidget } from './file_location_input';
import { Button, Select } from './input_widget';
import { Anchor, Div, Label, Paragraph, Span, Table, TableData, TableHeader, TableRow } from './widget';
import { Path, Url } from '../../util/parsed_url';
import { BooleanInput } from './value_input_widget';
import { Shape5DInputNoChannel } from './shape5d_input';
import { DataSourceSelectionWidget } from './datasource_selection_widget';

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
    public equals(other: LabelHeader): boolean{
        return this.name == other.name && this.color == other.color
    }
    public couldBe(other: LabelHeader): boolean{
        return this.name == other.name || this.color == other.color
    }
}

class Job{
    private readonly jobDto: ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipJobDto;

    constructor(jobDto: ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipJobDto){
        this.jobDto = jobDto
    }

    private makeProgressDisplay(params: {
        openInViewer: (datasource: FsDataSource) => void,
        session: Session,
    }): TableData{
        const jobDto = this.jobDto

        if(jobDto.status == "pending" || jobDto.status == "cancelled"){
            return new TableData({parentElement: undefined, innerText: jobDto.status})
        }
        if(jobDto.status == "running"){
            return new TableData({
                parentElement: undefined,
                innerText: jobDto.num_args === undefined ?
                    "unknwown" :
                    `${Math.round(jobDto.num_completed_steps / jobDto.num_args * 100)}%`
            })
        }
        if(jobDto.status == "completed"){
            if(jobDto.error_message){
                let td = new TableData({parentElement: undefined, innerText: "failed"})
                td.element.title = jobDto.error_message
                return td
            }
            let out = new TableData({parentElement: undefined})

            let dataProxyGuiUrl: Url | undefined = undefined;

            if(jobDto instanceof ZipJobDto){
                const fs = Filesystem.fromDto(jobDto.output_fs)
                if(fs instanceof BucketFs){
                    out.clear()
                    dataProxyGuiUrl = fs.getDataProxyGuiUrl({dirPath: Path.parse(jobDto.output_path).parent})
                }
                const output_path = Path.fromDto(jobDto.output_path)
                if(output_path.extension?.toLowerCase() === "dzip"){
                    const outputUrl = fs.getUrl(output_path).updatedWith({datascheme: "deepzoom"})
                    new Button({parentElement: out, inputType: "button", text: "Open in Viewer", onClick: async () => {
                        const datasourceResult = await DataSourceSelectionWidget.uiResolveUrlToDatasource({
                            datasources: outputUrl,
                            session: params.session,
                        })
                        if(datasourceResult instanceof Error){
                            new ErrorPopupWidget({message: `Could not open URL: ${datasourceResult}`})
                            return
                        }
                        params.openInViewer(datasourceResult)

                    }})
                    createElement({parentElement: out.element, tagName: "br"}) //FIXME?
                }
            }else if(jobDto instanceof ExportJobDto){
                const sink = FsDataSink.fromDto(jobDto.datasink)
                if(sink.filesystem instanceof BucketFs){
                    dataProxyGuiUrl = sink.filesystem.getDataProxyGuiUrl({dirPath: sink.path})
                }
                if(sink instanceof PrecomputedChunksSink){
                    new Button({parentElement: out, inputType: "button", text: "Open in Viewer", onClick: () => {
                        params.openInViewer(sink.toDataSource())
                    }})
                    createElement({parentElement: out.element, tagName: "br"}) //FIXME?
                }
            }else{
                out.element.innerText = "100%"
            }

            if(dataProxyGuiUrl){
                new Anchor({
                    parentElement: out,
                    innerText: "Open in Data Proxy",
                    href: dataProxyGuiUrl,
                    target: "_blank",
                    rel: "noopener noreferrer",
                })
            }

            return out
        }
        assertUnreachable(jobDto.status)
    }
    public toTableRow(params: {
        openInViewer: (datasource: FsDataSource) => void,
        session: Session,
    }): {name: TableData, progress: TableData}{
        return {
            name: new TableData({parentElement: undefined, innerText: this.jobDto.name}),
            progress: this.makeProgressDisplay(params),
        }
    }
}

class PixelClassificationExportAppletState{
    jobs: Array<Job>
    populated_labels: LabelHeader[] | undefined
    datasource_suggestions: FsDataSource[]

    constructor(params: {
        jobs: Array<Job>
        populated_labels: LabelHeaderDto[] | undefined
        datasource_suggestions: FsDataSource[]
    }){
        this.jobs = params.jobs
        this.populated_labels = params.populated_labels?.map(msg => LabelHeader.fromDto(msg))
        this.datasource_suggestions = params.datasource_suggestions
    }

    public static fromDto(message: PixelClassificationExportAppletStateDto): PixelClassificationExportAppletState{
        return new this({
            jobs: message.jobs.map(dto => new Job(dto)),
            datasource_suggestions: (message.datasource_suggestions || []).map(msg => FsDataSource.fromDto(msg)), //FIXME?
            populated_labels: message.populated_labels
        })
    }
}

export class PredictionsExportWidget extends Applet<PixelClassificationExportAppletState>{
    private viewer: Viewer

    public readonly element: HTMLElement;
    private jobsDisplay: Div;
    private labelSelectorContainer: Span;
    private labelToExportSelector: Select<LabelHeader> | undefined;
    private exportModeSelector: Select<"pixel probabilities" | "simple segmentation">;
    private datasourceListWidget: DataSourceListWidget;
    private customTileShapeCheckbox: BooleanInput;
    private tileShapeInput: Shape5DInputNoChannel

    public constructor({name, parentElement, session, help, viewer, defaultBucketName}: {
        name: string, parentElement: HTMLElement, session: Session, help: string[], viewer: Viewer, defaultBucketName: string
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
                onChange: (val) => this.labelSelectorContainer.show(val == "simple segmentation"),
            }),
        ]})
        this.labelSelectorContainer = new Paragraph({parentElement: this.element});
        this.labelSelectorContainer.show(false)

        const datasourceFieldset = createFieldset({parentElement: this.element, legend: "Input Datasets:"})
        this.datasourceListWidget = new DataSourceListWidget({
            parentElement: datasourceFieldset, session: this.session, defaultBucketName
        })

        const datasinkFieldset = createFieldset({legend: "Output: ", parentElement: this.element})
        const fileLocationInputWidget = new FileLocationPatternInputWidget({
            parentElement: datasinkFieldset,
            defaultBucketName,
            defaultPathPattern: "/ilastik_exports/{timestamp}/{name}_{output_type}",
            filesystemChoices: ["data-proxy"]
        })
        const datasinkConfigWidget = new DatasinkConfigWidget({parentElement: datasinkFieldset})

        new Paragraph({parentElement: this.element, children: [
            new Label({parentElement: undefined, innerText: "Use Custom Tile Shape: "}),
            this.customTileShapeCheckbox = new BooleanInput({parentElement: undefined, value: false, onChange: () => {
                this.tileShapeInput.disabled = !this.customTileShapeCheckbox.value
                tileShapeP.show(this.customTileShapeCheckbox.value)
            }}),
        ]})
        let tileShapeP = new Paragraph({parentElement: this.element})
        tileShapeP.show(this.customTileShapeCheckbox.value)
        this.tileShapeInput = new Shape5DInputNoChannel({parentElement: tileShapeP.element, disabled: !this.customTileShapeCheckbox.value})


        new Paragraph({parentElement: this.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Button({parentElement: undefined, inputType: "button", text: "Start Export Jobs", onClick: () => {
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

                if(this.datasourceListWidget.value.filter(ds => ds instanceof FsDataSource).length == 0){
                    new ErrorPopupWidget({message: "No valid datasets to process"})
                    return
                }

                for(let job_index=0; job_index < this.datasourceListWidget.value.length; job_index++){
                    const datasource = this.datasourceListWidget.value[job_index]
                    let fileLocation = fileLocationInputWidget.tryGetLocation({
                        item_index: job_index, name: datasource.url.path.name, output_type: this.exportModeSelector.value
                    });
                    if(fileLocation === undefined){
                        new ErrorPopupWidget({message: "Unexpected bad file location"}) //FIXME? Shouldn't this be impossible?
                        return
                    }
                    if(!(datasource instanceof FsDataSource)){
                        continue
                    }
                    let datasink_tile_shape: Shape5D
                    if(this.customTileShapeCheckbox.value){
                        const custom_tile_shape = this.tileShapeInput.getShape({c: numChannels})
                        if(custom_tile_shape === undefined){
                            new ErrorPopupWidget({message: "Custom tile shape is incomplete"})
                            return
                        }
                        datasink_tile_shape = custom_tile_shape.clampedWith(datasource.shape)
                    }else{
                        datasink_tile_shape = datasource.tile_shape
                    }

                    const datasink = datasinkConfigWidget.tryMakeDataSink({
                        filesystem: fileLocation.filesystem,
                        path: fileLocation.path,
                        dtype,
                        interval: datasource.interval.updated({c: [0, numChannels]}),
                        resolution: datasource.spatial_resolution,
                        tile_shape: datasink_tile_shape.updated({c: numChannels}),
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
            }}),
        ]})

        this.jobsDisplay = new Div({parentElement: this.element});
    }

    protected onNewState(new_state: PixelClassificationExportAppletState){
        this.jobsDisplay.clear()

        let previousLabelSelection = this.labelToExportSelector?.value;
        this.labelSelectorContainer.clear()
        new Label({parentElement: this.labelSelectorContainer, innerText: "Select a label to segment: "})
        if(new_state.populated_labels){
            this.labelToExportSelector = new Select<LabelHeader>({
                parentElement: this.labelSelectorContainer,
                popupTitle: "Select a label to segment",
                options: new_state.populated_labels,
                renderer: (val) => new Span({
                    parentElement: undefined,
                    children: [
                        new Span({parentElement: undefined, innerText: val.name + " "}),
                        new Span({parentElement: undefined, innerText: "🖌️", inlineCss: {
                            backgroundColor: val.color.hexCode,
                            padding: "2px",
                            border: "solid 1px black"
                        }}),
                    ]
                }),
            })

            if(previousLabelSelection){
                const foudnLabel = new_state.populated_labels.find(labelHeader => previousLabelSelection?.couldBe(labelHeader))
                if(foudnLabel){
                    this.labelToExportSelector.value = foudnLabel
                }
            }
        }else{
            new Span({parentElement: this.labelSelectorContainer, innerText: "No populated labels", cssClasses: [CssClasses.ItkErrorText]})
        }

        if(new_state.jobs.length == 0){
            return
        }

        const jobsTable = new Table({parentElement: this.jobsDisplay, cssClasses: [CssClasses.ItkTable], children: [
            new TableRow({parentElement: undefined, children: [
                new TableHeader({parentElement: undefined, innerText: "Name"}), //FIXME: mode? name?
                new TableHeader({parentElement: undefined, innerText: "Progress"}),
            ]}),
        ]})

        new_state.jobs.forEach(job => {
            const row = job.toTableRow({
                session: this.session,
                openInViewer: (datasource) => {
                    this.viewer.openLane({
                        rawData: datasource,
                        name: datasource.url.name, //FIXME?
                        isVisible: true,
                    })
                }
            })
            new TableRow({parentElement: jobsTable, children: [row.name, row.progress]})
        })
    }
}
