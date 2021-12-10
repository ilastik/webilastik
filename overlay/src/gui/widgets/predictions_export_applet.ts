import { ensureJsonArray } from '../../util/serialization';
import { Applet } from '../../client/applets/applet';
import { ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from '../../util/serialization';
import { createElement, createInput, createInputParagraph } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { DataSource, DataSourceLoadParams, PrecomputedChunksEncoder, PrecomputedChunksScaleSink_CreationParams, Session } from '../../client/ilastik';
import { SelectorWidget } from './selector_widget';
import { Url } from '../../util/parsed_url';





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

export class PrecomputedChunksSinkFields{
    element: HTMLFieldSetElement;
    url_input: HTMLInputElement;
    encoding_selector: SelectorWidget<"raw">;
    constructor(params: {parentElement: HTMLElement}){
        this.element = createElement({tagName: "fieldset", parentElement: params.parentElement})
            createElement({tagName: "legend", parentElement: this.element, innerHTML: "Precomputed Chunks Sink Params"})

            this.url_input = createInputParagraph({inputType: "url", parentElement: this.element, label_text: "Url: "})

            let p = createElement({tagName: "p", parentElement: this.element})
                createElement({tagName: "label", parentElement: p, innerHTML: "Compression: "})
                this.encoding_selector = new SelectorWidget({
                    parentElement: p,
                    options: new Array<PrecomputedChunksEncoder>("raw"),
                    optionRenderer: (opt) => opt,
                    onSelection: () => {},
                })
    }

    public getValue(): PrecomputedChunksScaleSink_CreationParams | undefined{
        if(!this.url_input.validity.valid){
            return undefined
        }
        return new PrecomputedChunksScaleSink_CreationParams({
            url: Url.parse(this.url_input.value),
            encoding: this.encoding_selector.getSelection(),
        })
    }
}

export class DataProxyDataSourceCreatorWidget{
    public readonly element: HTMLFieldSetElement;
    public readonly bucket_name_input: HTMLInputElement;
    public readonly path_input: HTMLInputElement;

    constructor(params: {parentElement: HTMLElement}){
        this.element = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: this.element, innerHTML: "Data Source from Data-Proxy"})

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Bucket name: ", parentElement: p})
        this.bucket_name_input = createInput({inputType: "text", parentElement: p, required: true, value: "hbp-image-service"})

        p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Path: ", parentElement: p})
        this.path_input = createInput({inputType: "text", parentElement: p, required: true})
    }

    public get value(): DataSource | undefined{
        if(this.element.validity.valid){
            return
        }
        return undefined
    }
}

export class PredictionsExportApplet extends Applet<{jobs: Job[]}>{
    public readonly element: HTMLElement;
    private job_table: HTMLTableElement;
    private new_job_form: HTMLFormElement;

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
                    jobs: Job.fromJsonArray(raw_jobs)
                }
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Export Predictions", parentElement}).element
        this.element.classList.add("ItkPredictionsExportApplet")

        this.new_job_form = createElement({tagName: "form", parentElement: this.element}) as HTMLFormElement

            const datasource_fs = createElement({tagName: "fieldset", parentElement: this.new_job_form})
                createElement({tagName: "legend", parentElement: datasource_fs, innerHTML: "Raw Data"})

                const data_source_url_input = createInputParagraph({inputType: "url", parentElement: datasource_fs, required: true, label_text: "URL: "})

                const spatial_resolution_fs = createElement({tagName: "fieldset", parentElement: datasource_fs})
                    createElement({tagName: "legend", parentElement: spatial_resolution_fs, innerHTML: "Spatial Resolution (nm): "})

                    createElement({tagName: "label", parentElement: spatial_resolution_fs, innerHTML: "x: "})
                    /* const spatial_resolution_x_input = */createInput({inputType: "number", parentElement: spatial_resolution_fs, inlineCss: {width: "4em"}});

                    createElement({tagName: "label", parentElement: spatial_resolution_fs, innerHTML: " y: "})
                    /* const spatial_resolution_y_input = */createInput({inputType: "number", parentElement: spatial_resolution_fs, inlineCss: {width: "4em"}});

                    createElement({tagName: "label", parentElement: spatial_resolution_fs, innerHTML: " z: "})
                    /* const spatial_resolution_z_input = */createInput({inputType: "number", parentElement: spatial_resolution_fs, inlineCss: {width: "4em"}});


            const datasink_fs = createElement({tagName: "fieldset", parentElement: this.new_job_form})
                createElement({tagName: "legend", parentElement: datasink_fs, innerHTML: "Data Sink"})

                const precomp_chunks_sink_fields = new PrecomputedChunksSinkFields({parentElement: datasink_fs})

        createInputParagraph({inputType: "submit", value: "Create Job", parentElement: this.new_job_form})

        this.job_table = createElement({tagName: "table", parentElement: this.element, cssClasses: ["ItkPredictionsExportApplet_job_table"]});

        this.new_job_form.addEventListener("submit", (ev) => {
            ev.preventDefault()
            const sink_params = precomp_chunks_sink_fields.getValue();
            if(sink_params === undefined){
                alert("Missing sink params") //FIXME ?
                return false
            }
            this.doRPC("start_export_job", {
                data_source_params: new DataSourceLoadParams({
                    url: Url.parse(data_source_url_input.value)
                }),
                data_sink_params: sink_params,
            })
            //don't submit synchronously
            console.log("~~~>>> returning false")
            return false
        })
    }

    // private async inferFileSystem(url: Url): FileSystem | Error{
    //     if(url.hostname == "data-proxy.ebrains.eu"){
    //         let path_components = url.path.split("/")
    //         if(path_components[0] != "api" || path_components[1] != "buckets" || path_components.length < 3){
    //             return Error(`Bad data-proxy bucket url: ${url.raw}`)
    //         }
    //         return new DataProxyBucketFs({bucket_name})
    //     }
    // }

    protected onNewState(new_state: {jobs: Array<Job>}){
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
