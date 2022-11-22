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

        const fixedUrl = params.url.updatedWith({hash: ""})
        const datasourcesResult = await params.session.getDatasourcesFromUrl(
            new GetDatasourcesFromUrlParamsDto({url: fixedUrl.toDto()})
        )
        if(datasourcesResult === undefined){
            return new UnsupportedDatasetView({...params})
        }
        if(datasourcesResult instanceof Error){
            return new FailedView({...params, errorMessage: datasourcesResult.message})
        }

        // if the requested URL matches the URL of a single returned datasource, we have to strip it out of the other scales
        if(datasourcesResult.length > 1){
            for(const ds of datasourcesResult){
                if(ds instanceof PrecomputedChunksDataSource && ds.url.equals(params.url)){
                    return new StrippedPrecomputedView({name: params.name, session: params.session, datasource: ds})
                }
            }
        }
        return new RawDataView({...params, datasources: datasourcesResult})
    }
}

export abstract class DataView extends View{
    public abstract getDatasources(): Array<FsDataSource> | undefined;

}

export class RawDataView extends DataView{
    public readonly datasources: FsDataSource[]
    constructor(params: {name: string, url: Url, datasources: Array<FsDataSource>}){
        super(params)
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
        return new RawDataView({name: params.name, url: params.url, datasources: datasources_result})
    }
}

export class StrippedPrecomputedView extends DataView{
    public static readonly regex = new RegExp(
        String.raw`/stripped_precomputed/url=(?<url>[^/]+)/resolution=(?<resolution>\d+_\d+_\d+)`
    )
    public readonly datasource: FsDataSource

    public constructor(params: {name: string, session: Session, datasource: PrecomputedChunksDataSource}){
        const all_scales_url = params.datasource.url.updatedWith({hash: ""})
        const resolution_str = params.datasource.spatial_resolution.map(axis => axis.toString()).join("_")

        super({
            name: params.name,
            url: params.session.sessionUrl.updatedWith({
                datascheme: "precomputed",
            }).joinPath(`stripped_precomputed/url=${all_scales_url.toBase64()}/resolution=${resolution_str}`),
        })
        this.datasource = params.datasource
    }

    public getDatasources(): Array<FsDataSource>{
        return [this.datasource]
    }

    public static matches(url: Url): boolean{
        const extractedParams = this.extractUrlParams(url)
        return extractedParams !== undefined && !(extractedParams instanceof Error)
    }

    public static extractUrlParams(url: Url): {datasetUrl: Url, selectedResolution: [number, number, number]} | undefined | Error{
        const match = url.path.raw.match(StrippedPrecomputedView.regex)
        if(match === null){
            return undefined
        }
        const datasetUrl = Url.fromBase64(match.groups!["url"])
        const selectedResolutionStr = match.groups!["resolution"].split("_")
        const selectedResolution: [number, number, number] = [
            parseInt(selectedResolutionStr[0]), parseInt(selectedResolutionStr[1]), parseInt(selectedResolutionStr[2])
        ]
        for(let i of selectedResolution){
            if(Number.isNaN(i)){
                return new Error(`Bad resolution: ${selectedResolutionStr}`)
            }
        }
        return {datasetUrl, selectedResolution}
    }

    public static async tryFromUrl(params: {name: string, url: Url, session: Session}): Promise<StrippedPrecomputedView | undefined | Error>{
        const url_params_result = this.extractUrlParams(params.url)
        if(url_params_result instanceof Error || url_params_result === undefined){
            return url_params_result
        }
        const {datasetUrl, selectedResolution} = url_params_result;
        const rawViewResult = await RawDataView.tryFromUrl({name: params.name, url: datasetUrl, session: params.session})
        if(rawViewResult instanceof Error || rawViewResult === undefined){
            return rawViewResult
        }

        const datasources = rawViewResult.datasources.filter(ds => {
            return ds.spatial_resolution[0] === selectedResolution[0] &&
                   ds.spatial_resolution[1] === selectedResolution[1] &&
                   ds.spatial_resolution[2] === selectedResolution[2]
        })
        if(datasources.length != 1){
            return Error(`Expected single datasource, found these: ${[datasources.map(ds => ds.url.raw)]}`)
        }
        const datasource = datasources[0]
        if(!(datasource instanceof PrecomputedChunksDataSource)){
            return Error(`
                Expected ${datasetUrl.raw} to point to precomptued chunks. Got this:
                ${JSON.stringify(datasource.toDto().toJsonValue())}
            }`)
        }
        return new StrippedPrecomputedView({name: params.name, datasource, session: params.session})
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
            }).joinPath(`predictions/raw_data=${params.raw_data.url.toBase64()}/generation=${params.classifierGeneration}`),
        })
        this.raw_data = params.raw_data
        this.classifierGeneration = params.classifierGeneration
        this.channel_colors = params.channel_colors
    }


    public static matches(url: Url): boolean | Error {
        const result = this.extractUrlParams(url)
        return result instanceof Error ? result : (result !== undefined)
    }

    public static extractUrlParams(url: Url): {rawDataUrl: Url, classifierGeneration: number} | undefined | Error{
        const match = url.path.raw.match(PredictionsView.regex)
        if(match === null){
            return undefined
        }
        const rawDataUrl = Url.fromBase64(match.groups!["raw_data"])
        const classifierGeneration = parseInt(match.groups!["generation"])
        return {rawDataUrl, classifierGeneration}
    }

    // public static async tryFromUrl(params:{name: string, url: Url, session: Session}): Promise<PredictionsView | undefined | Error>{
    //     const urlParamsResult = this.extractUrlParams(params.url)
    //     if(urlParamsResult instanceof Error || urlParamsResult === undefined){
    //         return urlParamsResult
    //     }
    //     const {rawDataUrl, classifierGeneration} = urlParamsResult
    //     const rawViewUrl = await RawDataView.tryFromUrl({name: params.name, url: rawDataUrl, session: params.session})
    //     if(rawViewUrl instanceof Error || rawViewUrl === undefined){
    //         return rawViewUrl
    //     }
    //     const datasources = rawViewUrl.datasources
    //     if(datasources.length != 1){
    //         return Error(`Expected single datasource, found these: ${datasources.map(ds => ds.url.raw).join(', ')}`)
    //     }
    //     return new PredictionsView({
    //         name: params.name, session: params.session, raw_data: datasources[0], classifierGeneration
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