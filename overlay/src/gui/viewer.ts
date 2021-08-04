// import { vec3 } from "gl-matrix";
import { vec3 } from "gl-matrix";
import { DataSource, Session } from "../client/ilastik";
import { IMultiscaleDataSource } from "../datasource/datasource";
import { HtmlImgSource } from "../datasource/html_img";
import { PrecomputedChunks } from "../datasource/precomputed_chunks";
import { IDataView, IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { awaitStalable, StaleResult } from "../util/misc";
import { Url } from "../util/parsed_url";

export abstract class View{
    public name: string;
    public readonly multiscale_datasource: IMultiscaleDataSource;

    public constructor({name, multiscale_datasource}: {
        name: string,
        multiscale_datasource: IMultiscaleDataSource,
    }){
        this.name = name
        this.multiscale_datasource = multiscale_datasource
    }

    public displaysTheSameAs(other: View): boolean{
        return this.multiscale_datasource.url.equals(other.multiscale_datasource.url)
    }
}

export class RawView extends View{}

export class PixelTrainingView extends View{
    public readonly raw_data: DataSource
    constructor(params: ConstructorParameters<typeof View>[0] & {raw_data: DataSource}){
        super(params)
        this.raw_data = params.raw_data
    }

    public equals(other: PixelTrainingView): boolean{
        return this.raw_data.equals(other.raw_data) && this.name == other.name
    }
}

export class PixelPredictionsView extends View{
    public readonly raw_data: DataSource
    constructor(params: ConstructorParameters<typeof View>[0] & {raw_data: DataSource}){
        super(params)
        this.raw_data = params.raw_data
    }
}

export class Viewer{
    public readonly driver: IViewerDriver;
    public readonly ilastik_session: Session;
    private views = new Array<View>()
    private onViewportsChangedHandlers = new Array<() => void>();

    public constructor({driver, ilastik_session}: {driver: IViewerDriver, ilastik_session: Session}){
        this.driver = driver
        this.ilastik_session = ilastik_session
        const onViewportsChangedHandler = async () => {
            this.dropClosedViews()
            const missing_views = await awaitStalable({referenceKey: "createMissingViews", callable: this.createMissingViews})
            if(missing_views instanceof StaleResult){
                return
            }
            this.views = this.views.concat(missing_views)
            for(let handler of this.onViewportsChangedHandlers){
                await handler() //FIXME
            }
        }
        driver.onViewportsChanged(onViewportsChangedHandler)
        onViewportsChangedHandler()
    }

    public getViews(): Array<View>{
        return this.views.slice()
    }

    private findViewFromNative(native_view: IDataView): View | undefined{
        return  this.views.find(view => {
            return view.multiscale_datasource.url.double_protocol_raw == Url.parse(native_view.url).double_protocol_raw
        })
    }

    public findView(view: View) : View | undefined{
        return this.views.find(v => v.constructor == view.constructor && v.displaysTheSameAs(view))
    }

    private dropClosedViews(){
        const raw_urls_on_display = this.driver.getOpenDataViews().map(view => Url.parse(view.url).double_protocol_raw)
        this.views = this.views.filter(view => raw_urls_on_display.includes(view.multiscale_datasource.url.double_protocol_raw))
    }

    private createMissingViews = async (): Promise<Array<View>> => { //FIXME: detect old prediction/training views that are still open?
        let out = new Array<View>();
        for(let native_view of this.driver.getOpenDataViews().filter(native_view => this.findViewFromNative(native_view) === undefined)){
            let native_url = Url.parse(native_view.url)
            let multiscale_datasource : IMultiscaleDataSource;
            if(HtmlImgSource.accepts(native_url)){
                multiscale_datasource = new HtmlImgSource(native_url)
            }else if(native_url.datascheme == "precomputed"){
                try{
                    multiscale_datasource = await PrecomputedChunks.fromUrl(native_url)
                }catch(e){
                    console.error(`${e}`)
                    continue
                }
            }else{
                console.log(`Unsupported url: ${native_url.double_protocol_raw}`)
                continue
            }
            out.push(new RawView({name: native_view.name, multiscale_datasource: multiscale_datasource}))
        }
        return out
    }

    public getViewportDrivers(): Array<IViewportDriver>{
        return this.driver.getViewportDrivers()
    }

    public getTrackedElement(): HTMLElement{
        return this.driver.getTrackedElement()
    }

    public onViewportsChanged(handler: () => void){
        this.onViewportsChangedHandlers.push(handler)
    }

    public refreshView({view, channel_colors}: {view: View, channel_colors?: vec3[]}){
        if(!this.findView(view)){
            this.views.push(view)
        }
        this.driver.refreshView({channel_colors, name: view.name, url: view.multiscale_datasource.url.double_protocol_raw})
    }

    public getActiveView(): View | undefined{
        const native_view = this.driver.getDataViewOnDisplay()
        if(native_view){
            return this.findViewFromNative(native_view)
        }
        return undefined
    }
}
