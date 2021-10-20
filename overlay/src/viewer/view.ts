import { vec3 } from "gl-matrix";
import { DataSource, PrecomputedChunksDataSource, Session, SkimageDataSource } from "../client/ilastik";
import { INativeView } from "../drivers/viewer_driver";
import { uuidv4 } from "../util/misc";
import { Url } from "../util/parsed_url";
import { JsonValue } from "../util/serialization";

export abstract class View{
    public readonly native_view: INativeView;
    public readonly url: Url;

    constructor(params: {native_view: INativeView}){
        this.native_view = params.native_view
        this.url = Url.parse(this.native_view.url)
    }

    public correspondsTo({native_view}: {native_view: INativeView}): boolean{
        return Url.parse(native_view.url).equals(this.url)
    }

    public static async tryFromNative(native_view: INativeView): Promise<View | undefined>{
        return (
            await PredictionsView.tryFromNative(native_view) ||
            await TrainingView.tryFromNative(native_view) ||
            await RawDataView.tryFromNative(native_view)
        )
    }
}

export class RawDataView extends View{
    public readonly datasources: Array<DataSource>;
    constructor(params: {native_view: INativeView, datasources: Array<DataSource>}){
        super(params)
        this.datasources = params.datasources
    }

    public toTrainingView(params: {resolution: vec3, session: Session}): TrainingView{
        let raw_data = this.datasources.find(ds => vec3.equals(ds.spatial_resolution, params.resolution))
        if(raw_data === undefined){
            throw `Resolution ${vec3.str(params.resolution)} not found on ${JSON.stringify(this.native_view)}`
        }
        return new TrainingView({
            native_view: {
                name: `training on: ${raw_data.getDisplayString()}`,
                url: raw_data.toTrainingUrl(params.session).raw
            },
            raw_data
        })
    }

    public static async tryFromNative(native_view: INativeView): Promise<RawDataView | undefined>{
        let url = Url.parse(native_view.url)
        let datasources: Array<DataSource> | undefined = undefined
        datasources = await SkimageDataSource.tryArrayFromUrl(url)
        datasources = datasources || await PrecomputedChunksDataSource.tryArrayFromUrl(url)
        if(datasources === undefined){
            return undefined
        }
        return new RawDataView({
            native_view, datasources
        })
    }
}

export class TrainingView extends View{
    public readonly raw_data: DataSource;

    constructor(params: {native_view: INativeView, raw_data: DataSource}){
        super(params)
        this.raw_data = params.raw_data
    }

    public static async tryFromNative(native_view: INativeView): Promise<TrainingView | undefined>{
        let url = Url.parse(native_view.url)
        let raw_data : DataSource | undefined = undefined;
        raw_data = raw_data || await SkimageDataSource.tryGetTrainingRawData(url);
        raw_data = raw_data || await PrecomputedChunksDataSource.tryGetTrainingRawData(url);
        if(raw_data){
            return new TrainingView({
                native_view, raw_data
            })
        }
        return undefined
    }
}

export class PredictionsView extends View{
    public readonly raw_data: DataSource;

    private constructor(params: {native_view: INativeView, raw_data: DataSource}){
        super(params)
        this.raw_data = params.raw_data
    }

    public getChunkUrl(interval: {x: [number, number], y: [number, number], z: [number, number]}): Url{
        return this.url.joinPath(
            `data/${interval.x[0]}-${interval.x[1]}_${interval.y[0]}-${interval.y[1]}_${interval.z[0]}-${interval.z[1]}`
        )
    }

    public static async tryFromNative(native_view: INativeView): Promise<PredictionsView | undefined>{
        let url = Url.parse(native_view.url)

        let predictions_regex = /predictions\/raw_data=(?<raw_data>[^/?]+)/
        let match = url.path.match(predictions_regex)
        if(!match){
            return undefined
        }
        const raw_data_json: JsonValue = JSON.parse(Session.atob(match.groups!["raw_data"]))
        const raw_data = DataSource.fromJsonValue(raw_data_json)
        return new PredictionsView({
            native_view, raw_data
        })
    }

    public static createFor({raw_data, ilastik_session}: {raw_data: DataSource, ilastik_session: Session}): PredictionsView{
        let raw_data_json = JSON.stringify(raw_data.toJsonValue())
        let predictions_url = Url.parse(ilastik_session.session_url)
            .updatedWith({datascheme: "precomputed"})
            .joinPath(`predictions/raw_data=${Session.btoa(raw_data_json)}/run_id=${uuidv4()}`);
        return new PredictionsView({
            native_view: {
                name: `predicting on: ${raw_data.getDisplayString()}`,
                url: predictions_url.raw
            },
            raw_data,
        })
    }
}