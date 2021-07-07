import { vec3 } from "gl-matrix";
import { Applet } from "../../client/applets/applet";
import { DataSource, Session } from "../../client/ilastik";
import { PredictionsPrecomputedChunks } from "../../datasource/precomputed_chunks";
import { IViewerDriver } from "../../drivers/viewer_driver";
import { ParsedUrl } from "../../util/parsed_url";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject, JsonObject, JsonValue } from "../../util/serialization";

class PredictingAppletState{
    constructor(
        public readonly producer_is_ready: boolean,
        public readonly channel_colors: Array<vec3>,
        public readonly datasources: Array<DataSource>,
    ){}

    public toJsonValue(): JsonObject{
        return {
            producer_is_ready: this.producer_is_ready,
            datasources: this.datasources.map(ds => ds.toJsonValue()),
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
        let datasources = ensureJsonArray(obj["datasources"]).map(rds => DataSource.fromJsonValue(rds))
        return new PredictingAppletState(producer_is_ready, channel_colors, datasources)
    }
}

export class PredictingWidget extends Applet<PredictingAppletState>{
    constructor({session, viewer_driver}: {session: Session, viewer_driver: IViewerDriver}){
        super({
            deserializer: PredictingAppletState.fromJsonValue,
            name: "predicting_applet",
            session,
            onNewState: async (new_state) => {
                if(!new_state.producer_is_ready){
                    return
                }
                new_state.datasources.forEach(async (ds, ds_index) => {
                    let precomp_predictions = await PredictionsPrecomputedChunks.createFor({ilastik_session: session, raw_data: ParsedUrl.parse(ds.url)})
                    viewer_driver.refreshView({
                        name: `lane${ds_index}`,
                        url: precomp_predictions.url.getSchemedHref("://"),
                        similar_url_hint: ds.url.toString(),
                        channel_colors: new_state.channel_colors
                    })
                })
            }
        })
    }
}
