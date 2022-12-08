import { GetDatasourcesFromUrlParamsDto } from "../client/dto";
import { Color, FsDataSource, PrecomputedChunksDataSource, Session } from "../client/ilastik";
import { INativeView } from "../drivers/viewer_driver";
import { Url } from "../util/parsed_url";

export type DataViewUnion = RawDataView | StrippedPrecomputedView | UnsupportedDatasetView | FailedView
export type ViewUnion = DataViewUnion | PredictionsView

export abstract class View{
    public readonly name: string;
    public readonly url: Url;

    constructor(params: {name: string, url: Url}){
        this.name = params.name
        this.url = params.url
    }

    public toNative(name?: string): INativeView{
        return {
            name: name || this.name,
            url: this.url.updatedWith({search: new Map(), hash: ""}).raw
        }
    }

    public static async tryOpen(params: {name: string, url: Url, session: Session}): Promise<ViewUnion>{
        const strippedViewResult = await StrippedPrecomputedView.tryFromUrl({name: params.name, url: params.url, session: params.session})
        if(strippedViewResult instanceof Error){
            return new FailedView({...params, errorMessage: strippedViewResult.message})
        }
        if(strippedViewResult instanceof StrippedPrecomputedView){
            return strippedViewResult
        }

        if(PredictionsView.matches(params.url)){  //can't guess prediction colors from old predictions... yet
            return new UnsupportedDatasetView(params)
        }
        // const predictionsViewResult = await PredictionsView.tryFromUrl({name: params.name, url: params.url, session: params.session})
        // if(predictionsViewResult instanceof Error){
        //     return new FailedView({...params, errorMessage: predictionsViewResult.message})
        // }
        // if(predictionsViewResult instanceof PredictionsView){
        //     return predictionsViewResult
        // }


        const rawDataViewResult = await RawDataView.tryFromUrl({session: params.session, url: params.url, name: params.name})
        if(rawDataViewResult === undefined){
            return new UnsupportedDatasetView({...params})
        }
        if(rawDataViewResult instanceof Error){
            return new FailedView({...params, errorMessage: rawDataViewResult.message})
        }
        return rawDataViewResult
    }
}

export abstract class DataView extends View{
    public abstract getDatasources(): Array<FsDataSource> | undefined;

}

export class RawDataView extends DataView{
    public readonly datasources: FsDataSource[]
    constructor(params: {name: string, url: Url, datasources: Array<FsDataSource>}){
        const url = params.datasources.find(ds => ds instanceof PrecomputedChunksDataSource) ?
            params.url.updatedWith({datascheme: "precomputed"}) :
            params.url
        super({...params, url})
        this.datasources = params.datasources
    }

    public getDatasources(): Array<FsDataSource> | undefined{
        return this.datasources.slice()
    }

    public static async tryFromUrl(params: {session: Session, name: string, url: Url}): Promise<RawDataView | undefined | Error>{
        const datasources_result = await params.session.getDatasourcesFromUrl(
            new GetDatasourcesFromUrlParamsDto({url: params.url.toDto()})
        )
        if(datasources_result instanceof Error || datasources_result === undefined){
            return datasources_result
        }
        return new RawDataView({name: params.name, url: params.url, datasources: datasources_result instanceof Array ? datasources_result : [datasources_result]})
    }
}

export class StrippedPrecomputedView extends DataView{
    public static readonly regex = new RegExp(
        String.raw`/stripped_precomputed/datasource=(?<datasource>[^/]+)`
    )
    public readonly datasource: FsDataSource

    public constructor(params: {name: string, session: Session, datasource: PrecomputedChunksDataSource}){
        super({
            name: params.name,
            url: params.session.sessionUrl.updatedWith({
                datascheme: "precomputed",
            }).joinPath(`stripped_precomputed/datasource=${params.datasource.toBase64()}`),
        })
        this.datasource = params.datasource
    }

    public getDatasources(): Array<FsDataSource>{
        return [this.datasource]
    }

    public static matches(url: Url): boolean{
        const extractedParams = this.extractDatasourceFromUrl(url)
        return extractedParams !== undefined && !(extractedParams instanceof Error)
    }

    public static extractDatasourceFromUrl(url: Url): PrecomputedChunksDataSource | undefined | Error{
        const match = url.path.raw.match(StrippedPrecomputedView.regex)
        if(match === null){
            return undefined
        }
        return FsDataSource.fromBase64(match.groups!["datasource"])
    }

    public static async tryFromUrl(params: {name: string, url: Url, session: Session}): Promise<StrippedPrecomputedView | undefined | Error>{
        const datasource_result = this.extractDatasourceFromUrl(params.url)
        if(datasource_result instanceof Error || datasource_result === undefined){
            return datasource_result
        }
        return new StrippedPrecomputedView({name: params.name, datasource: datasource_result, session: params.session})
    }
}

export class PredictionsView extends View{
    public static readonly regex = new RegExp(
        String.raw`/predictions/raw_data=(?<raw_data>[^/]+)/generation=(?<generation>[^/?]+)`
    )
    public readonly raw_data: FsDataSource;
    public readonly classifierGeneration: number;
    public readonly channel_colors: Color[];

    public constructor(params:{
        name: string, session: Session, raw_data: FsDataSource, classifierGeneration: number, channel_colors: Color[]
    }){
        super({
            name: params.name,
            url: params.session.sessionUrl.updatedWith({
                datascheme: "precomputed" // FIXME: this assumes neuroglancer as the viewer
            }).joinPath(`predictions/raw_data=${params.raw_data.toBase64()}/generation=${params.classifierGeneration}`),
        })
        this.raw_data = params.raw_data
        this.classifierGeneration = params.classifierGeneration
        this.channel_colors = params.channel_colors
    }

    public static matches(url: Url): boolean | Error {
        const result = this.extractUrlParams(url)
        return result instanceof Error ? result : (result !== undefined)
    }

    public static extractUrlParams(url: Url): {raw_data: FsDataSource, classifierGeneration: number} | undefined | Error{
        const match = url.path.raw.match(PredictionsView.regex)
        if(match === null){
            return undefined
        }
        const raw_data_result = FsDataSource.fromBase64(match.groups!["raw_data"])
        if(raw_data_result instanceof Error){
            return raw_data_result
        }
        const classifierGeneration = parseInt(match.groups!["generation"])
        return {raw_data: raw_data_result, classifierGeneration}
    }

    // public static async tryFromUrl(params:{name: string, url: Url, session: Session}): Promise<PredictionsView | undefined | Error>{
    //     const urlParamsResult = this.extractUrlParams(params.url)
    //     if(urlParamsResult instanceof Error || urlParamsResult === undefined){
    //         return urlParamsResult
    //     }
    //     const {raw_data, classifierGeneration} = urlParamsResult
    //     return new PredictionsView({
    //         name: params.name, session: params.session, raw_data: raw_data, classifierGeneration, channel_colors: "FIXME"
    //     })
    // }
}

export class UnsupportedDatasetView extends DataView{
    public getDatasources(): undefined{
        return undefined
    }
}

export class FailedView extends DataView{
    public readonly errorMessage: string;
    public constructor(params: {name: string, url: Url, errorMessage: string}){
        super(params)
        this.errorMessage = params.errorMessage
    }
    public getDatasources(): undefined{
        return undefined
    }
}