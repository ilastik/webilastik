import { ensureJsonArray, ensureOptional } from '../../util/serialization';
import { Applet } from '../../client/applets/applet';
import { ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from '../../util/serialization';
import { createElement, createInputParagraph, createTable } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { DataSource, Session } from '../../client/ilastik';
import { DataSourceInput } from './datasource_input';
import { CssClasses } from '../css_classes';
import { PrecomputedChunksScaleDataSinkInput } from './precomputed_chunks_scale_datasink_input';
import { ErrorPopupWidget, PopupWidget } from './popup';
import { OneShotSelectorWidget } from './selector_widget';

const sink_creation_stati = ["success", "failed", "running" ] as const;
export type SinkCreationStatus = typeof sink_creation_stati[number];
export function ensureSinkCreationStatus(value: string): SinkCreationStatus{
    const variant = sink_creation_stati.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid sink creation status: ${value}`)
    }
    return variant
}

export class Job{
    public readonly name: string
    public readonly uuid: string
    public readonly num_args?: number
    public readonly num_completed_steps: number
    public readonly status: string

    public constructor(params: {
        name: string,
        uuid: string,
        num_args?: number,
        num_completed_steps: number,
        status: string,
    }){
        this.name = params.name
        this.uuid = params.uuid
        this.num_args = params.num_args
        this.num_completed_steps = params.num_completed_steps
        this.status = params.status
    }

    public static fromJsonValue(data: JsonValue): Job{
        let data_obj = ensureJsonObject(data)
        let num_args = data_obj["num_args"]

        return new Job({
            name: ensureJsonString(data_obj["name"]),
            uuid: ensureJsonString(data_obj["uuid"]),
            num_args: num_args === undefined || num_args === null ? undefined : ensureJsonNumber(num_args),
            num_completed_steps: ensureJsonNumber(data_obj["num_completed_steps"]),
            status: ensureJsonString(data_obj["status"]),
        })
    }

    public static fromJsonArray(data: JsonValue): Array<Job>{
        let data_array = ensureJsonArray(data)
        return data_array.map(element => this.fromJsonValue(element))
    }
}

type State = {
    jobs: Array<Job>,
    num_classes: number | undefined,
    datasource_suggestions: DataSource[],
}

function stateFromJsonValue(data: JsonValue): State{
    let data_obj = ensureJsonObject(data)
    return {
        jobs: Job.fromJsonArray(ensureJsonArray(data_obj["jobs"])),
        num_classes: ensureOptional(ensureJsonNumber, data_obj["num_classes"]),
        datasource_suggestions: ensureJsonArray(data_obj["datasource_suggestions"]).map(raw => DataSource.fromJsonValue(raw))
    }
}

export class PredictionsExportWidget extends Applet<State>{
    private state: State
    public readonly element: HTMLElement;
    jobsDisplay: HTMLDivElement;
    private datasourceInput: DataSourceInput;
    private datasinkInput: PrecomputedChunksScaleDataSinkInput;

    public constructor({name, parentElement, session, help}: {
        name: string, parentElement: HTMLElement, session: Session, help: string[]
    }){
        super({
            name,
            session,
            deserializer: stateFromJsonValue,
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.state = {jobs: [], num_classes: undefined, datasource_suggestions: []}
        this.element = new CollapsableWidget({display_name: "Export Predictions", parentElement, help}).element
        this.element.classList.add("ItkPredictionsExportApplet")

        this.datasourceInput = DataSourceInput.createLabeled({
            legend: "Input:", parentElement: this.element, session, onChanged: (ds: DataSource | undefined) => {
                if(ds  === undefined){
                    return
                }
                if(this.state.num_classes !== undefined){
                    this.datasinkInput.setParameters({
                        shape: ds.shape.updated({c: this.state.num_classes}),
                        tileShape: ds.tile_shape.updated({c: this.state.num_classes}),
                        resolution: ds.spatial_resolution,
                    })
                }
            }
        })
        createInputParagraph({inputType: "button", parentElement: this.element, label_text: "or ", value: "use training data...", onClick: () => {
            if(this.state.datasource_suggestions.length == 0){
                new ErrorPopupWidget({message: "No brush strokes to derive data input suggestions from."})
                return
            }
            let popup = new PopupWidget("Input suggestions")
            new OneShotSelectorWidget({
                parentElement: popup.element,
                options: this.state.datasource_suggestions,
                optionRenderer: (ds) => ds.getDisplayString(),
                onOk: (ds) => {
                    this.datasourceInput.value = ds
                    popup.destroy()
                },
                onCancel: () => {
                    popup.destroy()
                },
            })
        }})
        this.datasinkInput = PrecomputedChunksScaleDataSinkInput.createLabeled({
            legend: "Output:",
            parentElement: this.element,
            encoding: "raw",
            dataType: "float32",
            disableShape: true,
            disableTileShape: true,
            disableDataType: true,
            disableEncoding: true,
        })
        createInputParagraph({
            inputType: "button", value: "Create Job", parentElement: this.element, onClick: () => {
                let datasource = this.datasourceInput.value
                let datasink = this.datasinkInput.value
                if(!datasource || !datasink){
                    new ErrorPopupWidget({message: "Missing export parameters"})
                    return
                }
                this.doRPC(
                    "start_export_job", //FIXME: what about simple segmentation?
                    {datasource: datasource.toJsonValue(), datasink: datasink.toJsonValue()}
                )
            }
        })

        this.jobsDisplay = createElement({tagName: "div", parentElement: this.element});
    }

    protected onNewState(new_state: State){
        this.state = new_state
        this.jobsDisplay.innerHTML = ""

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
    }
}
