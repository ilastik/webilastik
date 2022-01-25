import { vec3 } from "gl-matrix";
import { Applet } from "../../client/applets/applet";
import { DataSource, Session } from "../../client/ilastik";
import { HashMap } from "../../util/hashmap";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, JsonValue } from "../../util/serialization";
import { PredictionsView, TrainingView } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";

type State = {
    classifier_generation: number;
    producer_is_ready: boolean;
    channel_colors: Array<{r: number, g: number, b: number}>;
}

export class PredictingWidget extends Applet<State>{
    public readonly viewer: Viewer;
    public readonly session: Session

    constructor({session, viewer}: {session: Session, viewer: Viewer}){
        super({
            deserializer: (value: JsonValue) => {
                let obj = ensureJsonObject(value)
                return {
                    classifier_generation: ensureJsonNumber(obj["classifier_generation"]),
                    producer_is_ready: ensureJsonBoolean(obj["producer_is_ready"]),
                    channel_colors: ensureJsonArray(obj["channel_colors"]).map(raw_color => {
                        const color_obj = ensureJsonObject(raw_color)
                        return {
                            r: ensureJsonNumber(color_obj["r"]),
                            g: ensureJsonNumber(color_obj["g"]),
                            b: ensureJsonNumber(color_obj["b"]),
                        }
                    })
                }
            },
            name: "pixel_classification_applet",
            session,
            onNewState: (new_state: State) => this.onNewState(new_state),
        })
        this.viewer = viewer
        this.session = session
    }

    private async onNewState(new_state: State){
        if(!new_state.producer_is_ready){
            this.viewer.getViews().forEach(view => {
                if(view instanceof PredictingWidget){
                    this.viewer.closeView(view)
                }
            })
            return
        }

        let viewsToOpen = new HashMap<DataSource, PredictionsView>({hash_function: ds => JSON.stringify(ds.toJsonValue())})

        for(let view of this.viewer.getViews()){
            // All training views need a prediction view...
            if(view instanceof TrainingView){
                let predictions_view = PredictionsView.createFor({
                    raw_data: view.raw_data,
                    ilastik_session: this.session,
                    classifier_generation: new_state.classifier_generation,
                })
                viewsToOpen.set(predictions_view.raw_data, predictions_view)
            }
        }

        for(let view of this.viewer.getViews()){
            if(!(view instanceof PredictionsView)){
                continue
            }
            if(view.classifier_generation == new_state.classifier_generation){
                // ... but predictions views with the same classifier generation need no refresh ...
                viewsToOpen.delete(view.raw_data)
            }else{
                // ... and predictions with an old classifier_generation need to be closed
                this.viewer.closeView(view)
            }
        }

        viewsToOpen.values().forEach(view => this.viewer.refreshView({
            view,
            channel_colors: new_state.channel_colors.map(color => vec3.fromValues(color.r, color.g, color.b))
        }))
    }
}
