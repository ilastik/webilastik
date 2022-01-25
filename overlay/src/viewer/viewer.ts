// import { vec3 } from "gl-matrix";
import { vec3 } from "gl-matrix";
import { Session } from "../client/ilastik";
import { INativeView, IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { awaitStalable, StaleResult } from "../util/misc";
import { View } from "./view";


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

    private findViewFromNative(native_view: INativeView): View | undefined{
        return  this.views.find(view => view.correspondsTo({native_view}))
    }

    public findView(view: View) : View | undefined{
        //FIXME: is this safe? think auto-context
        //also, training on raw data that has a single scale?
        return this.views.find(v => v.correspondsTo({native_view: view.native_view}))
    }

    private dropClosedViews(){
        const native_views_on_display = this.driver.getOpenDataViews()
        this.views = this.views.filter(view => {
            for(let native_view of native_views_on_display){
                if(view.correspondsTo({native_view})){
                    return true
                }
            }
            return false
        })
    }

    public closeView(view: View){
        this.driver.closeView({native_view: view.native_view})
    }

    private createMissingViews = async (): Promise<Array<View>> => { //FIXME: detect old prediction/training views that are still open?
        let out = new Array<View>();
        for(let native_view of this.driver.getOpenDataViews()){
            if(this.findViewFromNative(native_view) !== undefined){
                continue
            }
            let view = await View.tryFromNative(native_view);
            if(view === undefined){
                console.log(`Unsupported url: ${native_view.url}`)
                continue
            }
            out.push(view)
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
        this.driver.refreshView({channel_colors, native_view: view.native_view})
    }

    public getActiveView(): View | undefined{
        const native_view = this.driver.getDataViewOnDisplay()
        if(native_view){
            return this.findViewFromNative(native_view)
        }
        return undefined
    }

    public destroy(){
        //FIXME: unregister events from native viewer using the driver
    }
}
