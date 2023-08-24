import { Applet } from "../../client/applets/applet";
import { CheckDatasourceCompatibilityParams, CheckDatasourceCompatibilityResponse, Shape5DDto } from "../../client/dto";
import { Color, FsDataSource, Session, Shape5D } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, ensureJsonString, ensureOptional, JsonValue } from "../../util/serialization";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";
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

 //FIXME: use DTOs
type State = {
    generation: number,
    description: ClassifierDescription,
    live_update: boolean,
    channel_colors: Array<Color>,
    minInputShape: Shape5D | undefined,
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
        }),
        minInputShape: ensureOptional(
            (v) => {
                const dto = Shape5DDto.fromJsonValue(v)
                if(dto instanceof Error){
                    throw `FIXME: bad payload from server`
                }
                return Shape5D.fromDto(dto)
            },
            obj["minInputShape"]
        )
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
        minInputShape: undefined,
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
        // viewer.addDataChangedHandler(() => this.refreshPredictions())
        viewer.addViewportsChangedHandler(() => this.refreshPredictions())
        this.session = session

        this.element = new Div({parentElement, children: [
            this.classifierDescriptionDisplay = new Paragraph({parentElement: undefined}),
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({innerText: "Live Update", parentElement: undefined}),
                this.liveUpdateCheckbox = new BooleanInput({parentElement: undefined, onClick: () => {
                    this.doRPC("set_live_update", {live_update: this.liveUpdateCheckbox.value})
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
        this.viewer.getLaneWidgets().forEach(lane => lane.closePredictions())
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

    private refreshPredictions = async () => {
        if(this.state.description != "ready"){
            this.closePredictionViews()
            return
        }
        for(const lane of this.viewer.getLaneWidgets()){
            if(lane.rawData.shape.c != this.state.minInputShape!.c){
                lane.closePredictions()
                continue
            }
            if(!lane.isVisible){
                continue
            }
            lane.refreshPredictions({
                classifierGeneration: this.state.generation,
                channelColors: this.state.channel_colors,
                session: this.session,
            })
        }
    }

    public destroy(){
        this.closePredictionViews()
        this.element.destroy()
    }
}
