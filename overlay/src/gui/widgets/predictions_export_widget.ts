import { ensureJsonArray, ensureOptional } from '../../util/serialization';
import { Applet } from '../../client/applets/applet';
import { ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from '../../util/serialization';
import { createElement, createInputParagraph, createTable } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { DataSource, Session } from '../../client/ilastik';
import { CssClasses } from '../css_classes';
import { ErrorPopupWidget } from './popup';
import { PixelPredictionsExportParamsInput, SimpleSegmentationExportParamsInput } from './export_params_input';

const sink_creation_stati = ["pending", "running", "cancelled", "failed", "succeeded"] as const;
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
    public readonly element: HTMLElement;
    jobsDisplay: HTMLDivElement;
    predictionsExportParamsInput: PixelPredictionsExportParamsInput;
    simpleSegmentationExportParamsInput: SimpleSegmentationExportParamsInput;

    public constructor({name, parentElement, session, help}: {
        name: string, parentElement: HTMLElement, session: Session, help: string[]
    }){
        super({
            name,
            session,
            deserializer: stateFromJsonValue,
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Export Predictions", parentElement, help}).element
        this.element.classList.add("ItkPredictionsExportApplet")

        let predictionsExportControls = createElement({tagName: "details", parentElement: this.element})
        createElement({tagName: "summary", parentElement: predictionsExportControls, innerText: "Export Prediction Map"})
        this.predictionsExportParamsInput = new PixelPredictionsExportParamsInput({
            parentElement: predictionsExportControls,
            session
        })
        createInputParagraph({
            inputType: "button", value: "Create Prediction Map Export Job", parentElement: predictionsExportControls, onClick: () => {
                let payload = this.predictionsExportParamsInput.value
                if(!payload){
                    new ErrorPopupWidget({message: "Missing export parameters"})
                    return
                }
                this.doRPC("start_export_job", payload)
            }
        })


        let simpleSegmentationExportControls = createElement({tagName: "details", parentElement: this.element})
        createElement({tagName: "summary", parentElement: simpleSegmentationExportControls, innerText: "Export Simple Segmentation"})
        this.simpleSegmentationExportParamsInput = new SimpleSegmentationExportParamsInput({
            parentElement: simpleSegmentationExportControls,
            session
        })
        createInputParagraph({
            inputType: "button", value: "Create Simple Segmentation Export Job", parentElement: simpleSegmentationExportControls, onClick: () => {
                let payload = this.simpleSegmentationExportParamsInput.value
                if(!payload){
                    new ErrorPopupWidget({message: "Missing export parameters"})
                    return
                }
                this.doRPC("start_simple_segmentation_export_job", payload)
            }
        })

        this.jobsDisplay = createElement({tagName: "div", parentElement: this.element});
    }

    protected onNewState(new_state: State){
        this.jobsDisplay.innerHTML = ""

        this.predictionsExportParamsInput.setParams({
            datasourceSuggestions: new_state.datasource_suggestions,
            numberOfPixelClasses: new_state.num_classes,
        })
        this.simpleSegmentationExportParamsInput.setParams({
            datasourceSuggestions: new_state.datasource_suggestions,
            numberOfPixelClasses: new_state.num_classes,
        })

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
