import { Applet } from "../../client/applets/applet";
import { CheckDatasourceCompatibilityParams, CheckDatasourceCompatibilityResponse } from "../../client/dto";
import { Color, FsDataSource, Session } from "../../client/ilastik";
import { assertUnreachable, createElement, createImage, createInputParagraph, removeElement } from "../../util/misc";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from "../../util/serialization";
import { FailedView, PredictionsView, RawDataView, StrippedPrecomputedView, UnsupportedDatasetView } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";
import { BooleanInput } from "./boolean_input";

const classifier_descriptions = ["disabled", "waiting for inputs", "training", "ready", "error"] as const;
export type ClassifierDescription = typeof classifier_descriptions[number];
export function ensureClassifierDescription(value: string): ClassifierDescription{
    const variant = classifier_descriptions.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid classifier description: ${value}`)
    }
    return variant
}

type State = {
    generation: number,
    description: ClassifierDescription,
    live_update: boolean,
    channel_colors: Array<Color>,
}

function deserializeState(value: JsonValue): State{
    let obj = ensureJsonObject(value)
    return {
        generation: ensureJsonNumber(obj["generation"]),
        description: ensureClassifierDescription(ensureJsonString(obj["description"])),
        live_update: ensureJsonBoolean(obj["live_update"]),
        channel_colors: ensureJsonArray(obj["channel_colors"]).map(raw_color => {
            const color_obj = ensureJsonObject(raw_color)
            return new Color({
                r: ensureJsonNumber(color_obj["r"]),
                g: ensureJsonNumber(color_obj["g"]),
                b: ensureJsonNumber(color_obj["b"]),
            })
        })
    }
}

export class PredictingWidget extends Applet<State>{
    public readonly viewer: Viewer;
    public readonly session: Session

    public readonly element: HTMLDivElement
    private classifierDescriptionDisplay: HTMLSpanElement
    private liveUpdateCheckbox: BooleanInput
    private compatCheckGeneration = 0;
    private state: State = {
        generation: -1,
        description: "waiting for inputs",
        channel_colors: [],
        live_update: false,
    }

    constructor({session, viewer, parentElement}: {session: Session, viewer: Viewer, parentElement: HTMLElement}){
        super({
            deserializer: deserializeState,
            name: "pixel_classification_applet",
            session,
            onNewState: (new_state: State) => {
                this.state = new_state
                this.showInfo(new_state.description)
                this.liveUpdateCheckbox.value = new_state.live_update
                this.refreshPredictions()
            },
        })
        this.viewer = viewer
        viewer.addDataChangedHandler(() => this.refreshPredictions())
        this.session = session

        this.element = createElement({tagName: "div", parentElement})
        createElement({tagName: "label", innerText: "Live Update", parentElement: this.element})
        this.liveUpdateCheckbox = new BooleanInput({
            parentElement: this.element, onClick: () => {
                this.doRPC("set_live_update", {live_update: this.liveUpdateCheckbox.value})
            }
        })
        this.classifierDescriptionDisplay = createElement({tagName: "span", parentElement: this.element})
        createInputParagraph({
            inputType: "button", parentElement: this.element, value: "Clear Predictions", onClick: (ev) => {
                this.closePredictionViews()
                this.doRPC("set_live_update", {live_update: false})
                ev.preventDefault() //FIXME: is this necessary to prevent form submition?
                return false //FIXME: is this necessary to prevent form submition?
            }
        })
    }

    public async checkDatasourceCompatibility(datasources: FsDataSource[]): Promise<boolean[] | Error>{
        let response = await fetch(
            this.session.sessionUrl.joinPath("check_datasource_compatibility").raw,
            {
                method: "POST",
                body: JSON.stringify(new CheckDatasourceCompatibilityParams({
                    datasources: datasources.map(ds => ds.toDto())
                }).toJsonValue())
            }
        )
        if(!response.ok){
            return new Error(await response.text())
        }
        let compatibilities = CheckDatasourceCompatibilityResponse.fromJsonValue(await response.json())
        if(compatibilities instanceof Error){
            return compatibilities
        }
        return compatibilities.compatible
    }

    private closePredictionViews(){
        this.viewer.getViews().forEach(view => {
            if(view instanceof PredictionsView){
                this.viewer.closeView(view)
            }
        })
    }

    private showInfo(description: ClassifierDescription){
        this.classifierDescriptionDisplay.innerHTML = `Classifier status: ${description}`
        if(description == "training"){
            let loadingGif = createImage({src: "/public/images/loading.gif", parentElement: this.classifierDescriptionDisplay})
            loadingGif.style.marginLeft = "5px"

        }

        if(description == "error"){
            this.classifierDescriptionDisplay.classList.add(CssClasses.ErrorText)
            this.classifierDescriptionDisplay.classList.remove(CssClasses.InfoText)
        }else{
            this.classifierDescriptionDisplay.classList.add(CssClasses.InfoText)
            this.classifierDescriptionDisplay.classList.remove(CssClasses.ErrorText)
        }
    }

    private async refreshPredictions(){
        const compatCheckGeneration = this.compatCheckGeneration = this.compatCheckGeneration + 1
        // console.log(`(${compatCheckGeneration}) INFO: Starting new refreshPredictions`)

        let stalePredictionViews = new Array<PredictionsView>();
        let validPredictionViews = new Array<PredictionsView>();
        let predictionRawDataSources = new Map<string, FsDataSource>();
        for(let view of this.viewer.getViews()){
            if(view instanceof UnsupportedDatasetView || view instanceof FailedView){
                continue
            }
            if(view instanceof PredictionsView){
                if(
                    view.classifierGeneration != this.state.generation ||
                    this.state.channel_colors.length != view.channel_colors.length ||
                    !view.channel_colors.every((color, idx) => color.equals(this.state.channel_colors[idx]))
                ){
                    stalePredictionViews.push(view)
                }else{
                    validPredictionViews.push(view)
                }
                continue
            }
            if(view instanceof RawDataView){
                const datasources = view.getDatasources()
                if(!datasources || datasources.length != 1){
                    continue
                }
                const datasource = datasources[0]
                predictionRawDataSources.set(view.name + " " + datasource.resolutionString, datasource)
                continue
            }
            if(view instanceof StrippedPrecomputedView){
                predictionRawDataSources.set(view.name, view.datasource)
                continue
            }
            assertUnreachable(view)
        }

        for(const [name, rawDataSource] of Array.from(predictionRawDataSources.entries())){
            if(validPredictionViews.find(prediction_view => prediction_view.raw_data.equals(rawDataSource))){
                // console.log(`(${compatCheckGeneration}) INFO: No need to open predictions for ${rawDataSource.url}`)
                predictionRawDataSources.delete(name)
            }
        }

        for(const view of stalePredictionViews){
            // console.log(`(${compatCheckGeneration}) WORK: Closing predictions view for ${view.raw_data.url}`)
            this.viewer.closeView(view)
            if(compatCheckGeneration != this.compatCheckGeneration){
                // console.log(`(${compatCheckGeneration}) ABORTING (closing old preds): function recursed from events`)
                return
            }
        }

        if(predictionRawDataSources.size == 0){
            // console.log(`(${compatCheckGeneration}) DONE: No remaining raw data needing predictions.`)
            return
        }

        if(this.state.description != "ready"){
            // console.log(`(${compatCheckGeneration}) DONE: Classifier is not ready, not opening predictions.`)
            return
        }

        const compatibilities = await this.checkDatasourceCompatibility(Array.from(predictionRawDataSources.values()))
        if(compatCheckGeneration != this.compatCheckGeneration){
            // console.log(`(${compatCheckGeneration}) ABORTING: Predicting widget hook went stale.`)
            return
        }
        if(compatibilities instanceof Error){
            // console.log(`(${compatCheckGeneration}) ABORTING: Error when checking datasource compatibilities: ${compatibilities.message}`)
            return
        }

        let rawDataSourceIndex = 0
        for(const [name, ds] of predictionRawDataSources.entries()){
            if(!compatibilities[rawDataSourceIndex++]){
                console.log(`(${compatCheckGeneration}) SKIP: incompatible raw data: ${ds.url}`)
                continue
            }
            console.log(`(${compatCheckGeneration}) WORK: Opening predictions for ${ds.url}`);
            this.viewer.openDataView(
                new PredictionsView({
                    classifierGeneration: this.state.generation,
                    name: `predicting on ${name}`,
                    raw_data: ds,
                    session: this.session,
                    channel_colors: this.state.channel_colors.slice()
                })
            )
            if(compatCheckGeneration != this.compatCheckGeneration){
                console.log(`(${compatCheckGeneration}) ABORTING (opening new preds): function recursed from events`)
                return
            }
        }
    }

    public destroy(){
        this.closePredictionViews()
        removeElement(this.element)
    }
}
