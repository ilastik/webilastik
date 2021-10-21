import { vec3 } from "gl-matrix";
import { Applet } from "../../client/applets/applet";
import { DataSource, Session } from "../../client/ilastik";
import { HashMap } from "../../util/hashmap";
import { awaitStalable } from "../../util/misc";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, JsonObject, JsonValue } from "../../util/serialization";
import { PredictionsView, TrainingView } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";

class PredictingAppletState{
    constructor(
        public readonly producer_is_ready: boolean,
        public readonly channel_colors: Array<vec3>,
    ){}

    public toJsonValue(): JsonObject{
        return {
            producer_is_ready: this.producer_is_ready,
            channel_colors: this.channel_colors.map(cc => ({
                r: cc[0],
                g: cc[1],
                b: cc[2],
            }))
        }
    }

    public static fromJsonValue(value: JsonValue): PredictingAppletState{
        let obj = ensureJsonObject(value)
        let producer_is_ready = ensureJsonBoolean(obj["producer_is_ready"])
        let channel_colors = ensureJsonArray(obj["channel_colors"]).map(raw_color => {
            const color_obj = ensureJsonObject(raw_color)
            return vec3.fromValues(
                ensureJsonNumber(color_obj["r"]), ensureJsonNumber(color_obj["g"]), ensureJsonNumber(color_obj["b"])
            )
        })
        return new PredictingAppletState(producer_is_ready, channel_colors)
    }
}

export class PredictingWidget extends Applet<PredictingAppletState>{
    public readonly viewer: Viewer;
    public readonly session: Session

    constructor({socket, session, viewer}: {socket: WebSocket, session: Session, viewer: Viewer}){
        super({
            deserializer: PredictingAppletState.fromJsonValue,
            name: "pixel_classification_applet",
            socket,
            onNewState: async (new_state: PredictingAppletState) => {
                if(!new_state.producer_is_ready){
                    return
                }
                let predictionViews = await awaitStalable({referenceKey: "getPredictionsViews", callable: this.getPredictionsViews})
                if(predictionViews instanceof Array){
                    predictionViews.forEach(view => this.viewer.refreshView({view, channel_colors: new_state.channel_colors}))
                }
            },
        })
        this.viewer = viewer
        this.session = session
    }

    private getPredictionsViews = async (): Promise<Array<PredictionsView>> => {
        let views_to_refresh = new HashMap<DataSource, PredictionsView>({hash_function: ds => JSON.stringify(ds.toJsonValue())})
        for(let view of this.viewer.getViews()){
            if(view instanceof PredictionsView){
                views_to_refresh.set(view.raw_data, view)
            }else if(view instanceof TrainingView){
                let predictions_view = PredictionsView.createFor({
                    raw_data: view.raw_data,
                    ilastik_session: this.session,
                })
                views_to_refresh.set(predictions_view.raw_data, predictions_view)
            }
        }
        return views_to_refresh.values()
    }
}
