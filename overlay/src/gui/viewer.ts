// import { vec3 } from "gl-matrix";
import { vec3 } from "gl-matrix";
import { Session } from "../client/ilastik";
import { IMultiscaleDataSource } from "../datasource/datasource";
import { HtmlImgSource } from "../datasource/html_img";
import { PrecomputedChunks, PredictionsPrecomputedChunks, StrippedPrecomputedChunks } from "../datasource/precomputed_chunks";
import { IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { ParsedUrl } from "../util/parsed_url";

export abstract class View{
    public readonly name: string;
    public readonly datasource: IMultiscaleDataSource;

    public constructor({name, datasource}: {
        name: string,
        datasource: IMultiscaleDataSource,
    }){
        this.name = name
        this.datasource = datasource
    }
}

export class Viewer{
    public static training_view_name_prefix = "ilastik training: "
    public static predictions_view_name_prefix = "ilastik predictions: "

    public readonly driver: IViewerDriver;
    public readonly ilastik_session: Session;

    private asyncStart : number = 0

    public constructor({driver, ilastik_session}: {driver: IViewerDriver, ilastik_session: Session}){
        this.driver = driver
        this.ilastik_session = ilastik_session
    }

    public getViewportDrivers(): Array<IViewportDriver>{
        return this.driver.getViewportDrivers()
    }

    public getTrackedElement(): HTMLElement{
        return this.driver.getTrackedElement()
    }

    public onViewportsChanged(handler: () => void){
        if(this.driver.onViewportsChanged !== undefined){
            this.driver.onViewportsChanged(handler)
        }
    }

    public refreshView(params: {name: string, url: string, similar_url_hint?: string, channel_colors?: vec3[]}){
        this.driver.refreshView(params)
    }


    public async getActiveView(): Promise<View | undefined | Error>{
        const asyncStart = this.asyncStart = performance.now()
        const native_view = this.driver.getDataViewOnDisplay()
        if(native_view === undefined){
            return undefined
        }
        let current_url = ParsedUrl.parse(native_view.url)
        let multiscale_datasource : IMultiscaleDataSource;
        if(HtmlImgSource.accepts(current_url)){
            multiscale_datasource = new HtmlImgSource(current_url)
        }else if(PredictionsPrecomputedChunks.match(current_url)){
            multiscale_datasource = await PredictionsPrecomputedChunks.fromUrl(current_url)
        }else if(StrippedPrecomputedChunks.match(current_url)){
            multiscale_datasource = await StrippedPrecomputedChunks.fromUrl(current_url)
        }else{
            try{
                multiscale_datasource = await PrecomputedChunks.fromUrl(current_url)
            }catch(e){
                return Error(`${e}`)
            }
        }
        if(asyncStart < this.asyncStart){
            return undefined
        }
        return {name: native_view.name, datasource: multiscale_datasource}
    }
}
