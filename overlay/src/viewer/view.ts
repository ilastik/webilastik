import { vec3 } from "gl-matrix";
import { DataSource, Session } from "../client/ilastik";
import { INativeView } from "../drivers/viewer_driver";
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

    public static async tryFromNative(params: {native_view: INativeView, session: Session}): Promise<View | undefined>{
        return (
            await PredictionsView.tryFromNative(params) ||
            await TrainingView.tryFromNative(params) ||
            await RawDataView.tryFromNative(params)
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
        return TrainingView.fromDataSource({datasource: raw_data, session: params.session})
    }

    public static async tryFromNative(params: {native_view: INativeView, session: Session}): Promise<RawDataView | undefined>{
        let url = Url.parse(params.native_view.url)
        let datasources: Array<DataSource> | Error = await DataSource.getDatasourcesFromUrl({datasource_url: url, session: params.session})
        if(datasources instanceof Error){
            return undefined
        }
        return new RawDataView({native_view: params.native_view, datasources})
    }
}

export class TrainingView extends View{
    public readonly raw_data: DataSource;

    constructor(params: {native_view: INativeView, raw_data: DataSource}){
        super(params)
        this.raw_data = params.raw_data
    }

    public static async tryFromNative(params: {native_view: INativeView, session: Session}): Promise<TrainingView | undefined>{
        let url = Url.parse(params.native_view.url)
        let datasources: Array<DataSource> | Error = await DataSource.getDatasourcesFromUrl({datasource_url: url, session: params.session})
        if(datasources instanceof Error || datasources.length > 1){
            return undefined
        }
        return new TrainingView({native_view: params.native_view, raw_data: datasources[0]})
    }

    public static fromDataSource({datasource, session}: {datasource: DataSource, session: Session}): TrainingView{
        let resolutionString = `${datasource.spatial_resolution[0]}x${datasource.spatial_resolution[1]}x${datasource.spatial_resolution[2]}nm`
        return new TrainingView({
            native_view: {
                name: `training on: ${datasource.url.path.name} ${resolutionString}`,
                url: datasource.toTrainingUrl(session).raw
            },
            raw_data: datasource
        })
    }
}

export class PredictionsView extends View{
    public readonly raw_data: DataSource;
    public readonly classifier_generation: number

    private constructor(params: {native_view: INativeView, raw_data: DataSource, classifier_generation: number}){
        super(params)
        this.raw_data = params.raw_data
        this.classifier_generation = params.classifier_generation
    }

    public getChunkUrl(interval: {x: [number, number], y: [number, number], z: [number, number]}): Url{
        return this.url.joinPath(
            `data/${interval.x[0]}-${interval.x[1]}_${interval.y[0]}-${interval.y[1]}_${interval.z[0]}-${interval.z[1]}`
        )
    }

    public static async tryFromNative(params: {native_view: INativeView, session: Session}): Promise<PredictionsView | undefined>{
        let url = Url.parse(params.native_view.url)

        let predictions_regex = /predictions\/raw_data=(?<raw_data>[^/]+)\/generation=(?<generation>[^/?]+)/
        let match = url.path.raw.match(predictions_regex)
        if(!match){
            return undefined
        }
        const raw_data_json: JsonValue = JSON.parse(Session.atob(match.groups!["raw_data"]))
        const raw_data = DataSource.fromJsonValue(raw_data_json)
        return new PredictionsView({
            native_view: params.native_view, raw_data, classifier_generation: parseInt(match.groups!["generation"])
        })
    }

    public static createFor(params: {raw_data: DataSource, ilastik_session: Session, classifier_generation: number}): PredictionsView{
        let raw_data_json = JSON.stringify(params.raw_data.toJsonValue())
        let predictions_url = params.ilastik_session.sessionUrl
            .updatedWith({datascheme: "precomputed"})
            .joinPath(`predictions/raw_data=${Session.btoa(raw_data_json)}/generation=${params.classifier_generation}`);
        return new PredictionsView({
            native_view: {
                name: `predicting on: ${params.raw_data.getDisplayString()}`,
                url: predictions_url.raw
            },
            raw_data: params.raw_data,
            classifier_generation: params.classifier_generation,
        })
    }
}