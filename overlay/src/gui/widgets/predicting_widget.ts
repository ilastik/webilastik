import { Applet } from "../../client/applets/applet";
import { PredictionsView, Session } from "../../client/ilastik";
import { createElement, createImage, createInput, createInputParagraph, removeElement } from "../../util/misc";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from "../../util/serialization";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";

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
    channel_colors: Array<{r: number, g: number, b: number}>,
}

function deserializeState(value: JsonValue): State{
    let obj = ensureJsonObject(value)
    return {
        generation: ensureJsonNumber(obj["generation"]),
        description: ensureClassifierDescription(ensureJsonString(obj["description"])),
        live_update: ensureJsonBoolean(obj["live_update"]),
        channel_colors: ensureJsonArray(obj["channel_colors"]).map(raw_color => {
            const color_obj = ensureJsonObject(raw_color)
            return {
                r: ensureJsonNumber(color_obj["r"]),
                g: ensureJsonNumber(color_obj["g"]),
                b: ensureJsonNumber(color_obj["b"]),
            }
        })
    }
}

export class PredictingWidget extends Applet<State>{
    public readonly viewer: Viewer;
    public readonly session: Session

    public readonly element: HTMLDivElement
    private classifierDescriptionDisplay: HTMLSpanElement
    private liveUpdateCheckbox: HTMLInputElement

    constructor({session, viewer, parentElement}: {session: Session, viewer: Viewer, parentElement: HTMLElement}){
        super({
            deserializer: deserializeState,
            name: "pixel_classification_applet",
            session,
            onNewState: (new_state: State) => this.onNewState(new_state),
        })
        this.viewer = viewer
        this.session = session

        this.element = createElement({tagName: "div", parentElement})
        createElement({tagName: "label", innerText: "Live Update", parentElement: this.element})
        this.liveUpdateCheckbox = createInput({
            inputType: "checkbox", parentElement: this.element, onClick: () => {
                this.doRPC("set_live_update", {live_update: this.liveUpdateCheckbox.checked})
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

    private async onNewState(new_state: State){
        this.showInfo(new_state.description)
        this.liveUpdateCheckbox.checked = new_state.live_update
    }

    public destroy(){
        this.closePredictionViews()
        removeElement(this.element)
    }
}
