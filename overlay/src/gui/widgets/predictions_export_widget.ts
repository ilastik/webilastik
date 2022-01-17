import { ensureJsonArray, ensureOptional } from '../../util/serialization';
import { Applet } from '../../client/applets/applet';
import { ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from '../../util/serialization';
import { createElement, createInputParagraph } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { Session } from '../../client/ilastik';
import { DataSourcePicker } from './datasource_picker';
import { DataSinkSelectorWidget } from './datasink_selector';
import { CssClasses } from '../css_classes';





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
    error_message?: string,
}

export class PredictionsExportWidget extends Applet<State>{
    public readonly element: HTMLElement;
    private job_table: HTMLTableElement;
    private readonly errorMessageContainer: HTMLParagraphElement;

    public constructor({name, parentElement, session}: {
        name: string, parentElement: HTMLElement, session: Session
    }){
        super({
            name,
            session,
            deserializer: (data) => {
                let data_obj = ensureJsonObject(data)
                let raw_jobs = ensureJsonArray(data_obj["jobs"])
                return {
                    jobs: Job.fromJsonArray(raw_jobs),
                    error_message: ensureOptional(ensureJsonString, data_obj.error_message)
                }
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Export Predictions", parentElement}).element
        this.element.classList.add("ItkPredictionsExportApplet")

        let fieldset = createElement({tagName: "fieldset", parentElement: this.element})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: "Data Source"})

        new DataSourcePicker({name: "export_datasource_applet", parentElement: fieldset, session})

        fieldset = createElement({tagName: "fieldset", parentElement: this.element})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: "Data Sink"})

        new DataSinkSelectorWidget({name: "export_datasink_applet", parentElement: fieldset, session})

        createInputParagraph({
            inputType: "button", value: "Create Job", parentElement: this.element, onClick: () => this.doRPC("start_export_job", {})
        })

        this.errorMessageContainer = createElement({tagName: "p", parentElement: this.element})

        this.job_table = createElement({tagName: "table", parentElement: this.element, cssClasses: ["ItkPredictionsExportApplet_job_table"]});
    }

    protected onNewState(new_state: State){
        this.errorMessageContainer.innerHTML = ""
        if(new_state.error_message){
            createElement({
                tagName: "span",
                parentElement: this.errorMessageContainer,
                innerHTML: new_state.error_message,
                cssClasses: [CssClasses.ErrorText]
            })
        }
        this.job_table.innerHTML = ""
        let thead = createElement({tagName: "thead", parentElement: this.job_table})
            let head_tr = createElement({tagName: "tr", parentElement: thead})
                createElement({tagName: "th", parentElement: head_tr, innerHTML: "name"})
                createElement({tagName: "th", parentElement: head_tr, innerHTML: "status"})
                createElement({tagName: "th", parentElement: head_tr, innerHTML: "progress"})

        let tbody = createElement({tagName: "tbody", parentElement: this.job_table})
        for(let job of new_state.jobs){
            let job_progress = job.num_args === undefined ? "unknwown" : Math.round(job.num_completed_steps / job.num_args * 100).toString()
            let job_tr = createElement({tagName: "tr", parentElement: tbody})
                createElement({tagName: "td", parentElement: job_tr, innerHTML: job.name})
                createElement({tagName: "td", parentElement: job_tr, innerHTML: job.status})
                createElement({tagName: "td", parentElement: job_tr, innerHTML: `${job_progress}%` })
        }
    }
}
