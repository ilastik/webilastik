import { Applet } from "../../client/applets/applet";
import { CheckDatasourceCompatibilityParams, CheckDatasourceCompatibilityResponse } from "../../client/dto";
import { Color, FsDataSource, Session } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, ensureJsonString, JsonValue } from "../../util/serialization";
import { PredictionsView, RawDataView, ViewUnion } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";
import { BooleanInput } from "./value_input_widget";
import { Div, ImageWidget, Label, Paragraph } from "./widget";

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

    public readonly element: Div
    private classifierDescriptionDisplay: Paragraph
    private liveUpdateCheckbox: BooleanInput
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
        viewer.addViewportsChangedHandler(() => this.refreshPredictions())
        this.session = session

        this.element = new Div({parentElement, children: [
            this.classifierDescriptionDisplay = new Paragraph({parentElement: undefined}),
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({innerText: "Live Update", parentElement: undefined}),
                this.liveUpdateCheckbox = new BooleanInput({parentElement: undefined, onClick: () => {
                    this.doRPC("set_live_update", {live_update: this.liveUpdateCheckbox.value})
                }}),
                new Button({inputType: "button", text: "Clear Predictions", parentElement: undefined, onClick: (ev): false => {
                    this.closePredictionViews()
                    this.doRPC("set_live_update", {live_update: false})
                    ev.preventDefault() //FIXME: is this necessary to prevent form submition?
                    return false //FIXME: is this necessary to prevent form submition?
                }}),
            ]}),
        ]})
    }

    public async checkDatasourceCompatibility(datasource: FsDataSource): Promise<boolean | Error>{
        let response = await fetch(
            this.session.sessionUrl.joinPath("check_datasource_compatibility").raw,
            {
                method: "POST",
                body: JSON.stringify(new CheckDatasourceCompatibilityParams({
                    datasources: [datasource.toDto()]
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
        return compatibilities.compatible[0]
    }

    private closePredictionViews(){
        this.viewer.getViews().forEach(view => {
            if(view instanceof PredictionsView){
                this.viewer.reconfigure({toClose: [view]}) //FIXME?
            }
        })
    }

    private showInfo(description: ClassifierDescription){
        this.classifierDescriptionDisplay.clear()
        this.classifierDescriptionDisplay.setInnerText(`Classifier status: ${description} `)
        if(description == "training"){
            new ImageWidget({src: Path.parse("/public/images/loading.gif"), parentElement: this.classifierDescriptionDisplay})
        }

        if(description == "error"){
            this.classifierDescriptionDisplay.addCssClass(CssClasses.ItkErrorText)
            this.classifierDescriptionDisplay.removeCssClass(CssClasses.InfoText)
        }else{
            this.classifierDescriptionDisplay.addCssClass(CssClasses.InfoText)
            this.classifierDescriptionDisplay.removeCssClass(CssClasses.ItkErrorText)
        }
    }

    private candidatePredictionsView: PredictionsView | undefined = undefined;
    private refreshPredictions = async () => {
        const dataView = this.viewer.getFirstDataView()
        const currentPredictionsView = this.viewer.getPredictionView()

        const toOpen: ViewUnion[] = []
        const toClose: ViewUnion[] = []

        if(currentPredictionsView && currentPredictionsView.isStale({classifierGeneration: this.state.generation, dataView})){
            toClose.push(currentPredictionsView)
        }

        if(dataView && this.state.description == "ready"){
            let rawData: FsDataSource;
            if(dataView instanceof RawDataView){
                rawData = dataView.datasources[0]
            }else{
                rawData = dataView.datasource
            }
            let predictonsOpacity = 0.5

            let newPredictionsView = new PredictionsView({
                classifierGeneration: this.state.generation,
                name: `predicting on ${dataView.name}`,
                raw_data: rawData,
                session: this.session,
                channel_colors: this.state.channel_colors.slice(),
                opacity: predictonsOpacity,
                visible: true,
            })
            if(!this.candidatePredictionsView || !newPredictionsView.hasSameDataAs(this.candidatePredictionsView)){
                this.candidatePredictionsView = newPredictionsView
                const rawDataIsCompatible = await this.checkDatasourceCompatibility(rawData);
                if(this.candidatePredictionsView != newPredictionsView){
                    console.log(`refreshPredictions went stale after async`)
                    return
                }
                if(rawDataIsCompatible === true){ //FIXME
                    console.log(`PredictingWidget: Will open this: ${newPredictionsView.url.raw}`)
                    toOpen.push(newPredictionsView)
                }
            }
        }

        // this.candidatePredictionsView = undefined
        if(toOpen.length > 0 || toClose.length > 0){
            this.viewer.reconfigure({toOpen, toClose})
        }
    }

    public destroy(){
        this.closePredictionViews()
        this.element.destroy()
    }
}
