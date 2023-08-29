import { Applet } from '../../client/applets/applet';
import { JsonValue } from '../../util/serialization';
import { assertUnreachable, createElement, createFieldset } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { BucketFs, Color, FsDataSource, FsDataSink, Session, PrecomputedChunksSink, Shape5D, ZipFs, DziLevelDataSource } from '../../client/ilastik';
import { CssClasses } from '../css_classes';
import { ErrorPopupWidget, PopupWidget } from './popup';
import {
    CreateDziPyramidJobDto,
    ExportJobDto,
    JobCanceledDto,
    JobDto,
    JobFinishedDto,
    JobIsPendingDto,
    JobIsRunningDto,
    LabelHeaderDto,
    OpenDatasinkJobDto,
    PixelClassificationExportAppletStateDto,
    StartPixelProbabilitiesExportJobParamsDto,
    StartSimpleSegmentationExportJobParamsDto,
    ZipDirectoryJobDto,
    TransferFileJobDto,
} from '../../client/dto';
import { Viewer } from '../../viewer/viewer';
import { DataSourceListWidget } from './list_widget';
import { DatasinkConfigWidget, UnsupportedDziDataType } from './datasink_builder_widget';
import { DataType } from '../../util/precomputed_chunks';
import { FileLocationPatternInputWidget } from './file_location_input';
import { Button, ButtonWidget, Select } from './input_widget';
import { Anchor, Div, Label, Paragraph, Span, Table, TableData, TableHeader, TableRow } from './widget';
import { Path, Url } from '../../util/parsed_url';
import { BooleanInput } from './value_input_widget';
import { Shape5DInputNoChannel } from './shape5d_input';
import { DataSourceSelectionWidget } from './datasource_selection_widget';
import { TabsWidget } from './tabs_widget';
import { ExportPattern } from '../../util/export_pattern';
import { HashMap } from '../../util/hashmap';

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
    private readonly jobDto: ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipDirectoryJobDto | TransferFileJobDto | JobDto;

    constructor(jobDto: Job["jobDto"]){
        this.jobDto = jobDto
    }

    private makeProgressDisplay(params: {
        viewer: Viewer,
        session: Session,
    }): TableData{
        const jobDto = this.jobDto

        if(jobDto.status instanceof JobIsPendingDto){
            return new TableData({parentElement: undefined, innerText: "pending"})
        }
        if(jobDto.status instanceof JobCanceledDto){
            const cancellationMessage = jobDto.status.message;
            return new TableData({parentElement: undefined, children: [
                new Label({parentElement: undefined, innerText: "cancelled"}),
                new ButtonWidget({
                    parentElement: undefined, contents: "?", onClick: () => PopupWidget.OkPopup({
                        title: "Job Cancelled", paragraphs: [cancellationMessage]
                    })
                })
            ]})
        }
        if(jobDto.status instanceof JobIsRunningDto){
            return new TableData({
                parentElement: undefined,
                innerText: jobDto.num_args === undefined ?
                    "unknwown" :
                    `${Math.round(jobDto.status.num_completed_steps / jobDto.num_args * 100)}%`
            })
        }
        if(!(jobDto.status instanceof JobFinishedDto)){
            assertUnreachable(jobDto.status)
        }
        if(jobDto.status.error_message){
            let td = new TableData({parentElement: undefined, innerText: "failed"})
            td.element.title = jobDto.status.error_message
            return td
        }
        let out = new TableData({parentElement: undefined})

        let dataProxyGuiUrl: Url | undefined = undefined;

        if(jobDto instanceof TransferFileJobDto){
            const targetUrl = Url.fromDto(jobDto.target_url);
            dataProxyGuiUrl = BucketFs.tryGetDataProxyGuiUrl({url: targetUrl.parent})
            new ButtonWidget({parentElement: out, contents: "Open", onClick: async () => DataSourceSelectionWidget.tryOpenViews({
                urls: [targetUrl], viewer: params.viewer, session: params.session
            })})
        }else if(jobDto instanceof ExportJobDto){
            const sink = FsDataSink.fromDto(jobDto.datasink)
            if(sink.filesystem instanceof BucketFs){
                dataProxyGuiUrl = sink.filesystem.getDataProxyGuiUrl({dirPath: sink.path})
            }
            if(sink instanceof PrecomputedChunksSink){
                new Button({parentElement: out, inputType: "button", text: "Open", onClick: () => {
                    DataSourceSelectionWidget.tryOpenViews({
                        urls: [sink.toDataSource().url], viewer: params.viewer, session: params.session
                    })
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
    public toTableRow(params: {
        viewer: Viewer,
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
    private datasourceListWidget: DataSourceListWidget;
    private customTileShapeCheckbox: BooleanInput;
    private tileShapeInput: Shape5DInputNoChannel
    private exportModeSelector: TabsWidget<"pixel probabilities" | "simple segmentation", Paragraph>;

    public constructor({name, parentElement, session, help, viewer, defaultBucketName, inputBucketPath, outputPathPattern}: {
        name: string,
        parentElement: HTMLElement,
        session: Session,
        help: string[],
        viewer: Viewer,
        defaultBucketName: string,
        inputBucketPath: Path,
        outputPathPattern?: ExportPattern,
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

        this.exportModeSelector = new TabsWidget({parentElement: this.element, tabBodyWidgets: new Map([
            ["pixel probabilities", new Paragraph({parentElement: undefined, innerText: "Exports an image with one float32 channel per class (brush color)"})],
            ["simple segmentation", this.labelSelectorContainer = new Paragraph({parentElement: this.element})]
        ])})

        const datasourceFieldset = createFieldset({parentElement: this.element, legend: "Input Datasets:"})
        this.datasourceListWidget = new DataSourceListWidget({
            parentElement: datasourceFieldset, session: this.session, defaultBucketName, defaultBucketPath: inputBucketPath
        })

        const datasinkFieldset = createFieldset({legend: "Output: ", parentElement: this.element})
        const fileLocationInputWidget = new FileLocationPatternInputWidget({
            parentElement: datasinkFieldset,
            defaultBucketName,
            defaultPathPattern: outputPathPattern,
            filesystemChoices: ["data-proxy"],
            tooltip: "You can use any of the following replacements to compose output paths for export outputs:\n" +
                "{item_index} ordinal number representing the position of the input data source in the list of inputs\n" +
                "{name} the name of the input datasource (e.g.: the file at '/my/file.png' is named 'file.png'\n" +
                "{output_type} the semantic meaning of the data in the output. Either 'simple_segmentation' or 'pixel_probabilities'\n" +
                "{timestamp} a string representing the time when the job was submitted (e.g. '2023y12m31d__13h59min58s')\n" +
                "{extension} the file (or folder) extension, representing the data type (e.g. 'n5', 'dzi')"
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
            new Button({parentElement: undefined, inputType: "button", text: "Start Export Jobs", onClick: async () => {
                const exportMode = this.exportModeSelector.current.label
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
                    new ErrorPopupWidget({message: "Training isn't done yet"})
                    return
                }

                if(this.datasourceListWidget.value.filter(ds => ds instanceof FsDataSource).length == 0){
                    new ErrorPopupWidget({message: "No valid datasets to process"})
                    return
                }

                const jobSubmissionPayloads: Array<StartPixelProbabilitiesExportJobParamsDto | StartSimpleSegmentationExportJobParamsDto> = []
                const outputPathToInputUrl = new HashMap<Path, Url, string>();
                for(let job_index=0; job_index < this.datasourceListWidget.value.length; job_index++){
                    const datasource = this.datasourceListWidget.value[job_index]
                    if(!(datasource instanceof FsDataSource)){
                        continue
                    }
                    let inputPath: Path;
                    if(datasource instanceof DziLevelDataSource && datasource.filesystem instanceof ZipFs){
                        inputPath = datasource.filesystem.zip_file_path
                    }else{
                        inputPath = datasource.path
                    }
                    let fileLocation = fileLocationInputWidget.tryGetLocation({
                        itemIndex: job_index,
                        inputPath: inputPath,
                        resultType: exportMode,
                        extension: datasinkConfigWidget.extension,
                    });
                    if(fileLocation === undefined){
                        new ErrorPopupWidget({message: "Unexpected bad file location"}) //FIXME? Shouldn't this be impossible?
                        return
                    }
                    if(fileLocation.path.equals(Path.root)){
                        new ErrorPopupWidget({message: `Can't export directly to the root of the filesystem. Provide a file name.`})
                        return
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
                    const datasink_result = datasinkConfigWidget.tryMakeDataSink({
                        filesystem: fileLocation.filesystem,
                        path: fileLocation.path,
                        dtype,
                        interval: datasource.interval.updated({c: [0, numChannels]}),
                        resolution: datasource.spatial_resolution,
                        tile_shape: datasink_tile_shape.updated({c: numChannels}),
                    })
                    if(datasink_result instanceof UnsupportedDziDataType && exportMode == "pixel probabilities"){
                        new ErrorPopupWidget({
                            message: (
                                "Can't export pixel probabilities as .dzip, since those are float values. " +
                                "Maybe you meant to use 'simple segmentation'?"
                            )
                        })
                        return
                    }
                    if(datasink_result instanceof Error){
                        new ErrorPopupWidget({message: datasink_result.message})
                        return
                    }
                    if(!datasource || !datasink_result){
                        new ErrorPopupWidget({message: "Missing export parameters"})
                        return
                    }

                    const outputPath = datasink_result.filesystem instanceof ZipFs ? datasink_result.filesystem.zip_file_path : datasink_result.path
                    const conflictingInputUrl = outputPathToInputUrl.get(outputPath)
                    if(conflictingInputUrl){
                        new ErrorPopupWidget({
                            message: [
                                new Paragraph({parentElement: undefined, innerText: "Conflicting outputs:"}),
                                new Paragraph({parentElement: undefined, children: [
                                    new Span({parentElement: undefined, innerText: "The input image at "}),
                                    new Span({parentElement: undefined, cssClasses: [CssClasses.ItkEmphasisText], innerText: `${conflictingInputUrl} `}),
                                    new Span({parentElement: undefined, innerText: `would produce an output in the same path as the input image at `}),
                                    new Span({parentElement: undefined, cssClasses: [CssClasses.ItkEmphasisText], innerText: `${datasource.url}`}),
                                ]}),
                                new Paragraph({parentElement: undefined, children: [
                                    new Span({parentElement: undefined, innerText: "Both these inputs would have written to the path "}),
                                    new Span({parentElement: undefined, cssClasses: [CssClasses.ItkEmphasisText], innerText: outputPath.raw}),
                                ]})
                            ]
                        })
                        return
                    }
                    outputPathToInputUrl.set(outputPath, datasource.url)

                    datasink_result
                    if(exportMode == "pixel probabilities"){
                        jobSubmissionPayloads.push(
                            new StartPixelProbabilitiesExportJobParamsDto({
                                datasource: datasource.toDto(), datasink: datasink_result.toDto()
                            })
                        )
                        // this.doRPC("launch_pixel_probabilities_export_job", )
                    }else if(exportMode == "simple segmentation"){
                        const label_header = this.labelToExportSelector?.value;
                        if(!label_header){
                            new ErrorPopupWidget({message: "Missing export parameters"})
                            return
                        }
                        jobSubmissionPayloads.push(
                            new StartSimpleSegmentationExportJobParamsDto({
                                datasource: datasource.toDto(), datasink: datasink_result.toDto(), label_header: label_header.toDto()
                            })
                        )
                        // this.doRPC("launch_simple_segmentation_export_job", )
                    }else{
                        assertUnreachable(exportMode)
                    }
                }
                const jobsSubmissionResult = await PopupWidget.WaitPopup({
                    title: "Submitting jobs...",
                    operation: this.session.doHttpRpc(
                        jobSubmissionPayloads.map(payload => ({
                            applet_name: this.name,
                            method_name: payload instanceof StartPixelProbabilitiesExportJobParamsDto ?
                                "launch_pixel_probabilities_export_job" :
                                "launch_simple_segmentation_export_job",
                            arguments: payload,
                        }))
                    )
                })
                if(jobsSubmissionResult instanceof Error){
                    new ErrorPopupWidget({message: "Some job submissions failed."})
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
                viewer: this.viewer
            })
            new TableRow({parentElement: jobsTable, children: [row.name, row.progress]})
        })
    }
}
