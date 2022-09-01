// import { vec3 } from "gl-matrix";
import { vec3 } from "gl-matrix";
import { Applet } from "../client/applets/applet";
import { DataSource, PredictionsView, Session, View } from "../client/ilastik";
import { IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { HashMap } from "../util/hashmap";
import { Url } from "../util/parsed_url";
import { ensureJsonArray, ensureJsonNumber, ensureJsonObject, JsonValue } from "../util/serialization";


export class ViewerAppletState{
    public readonly active_views: HashMap<Url, View, string>
    public readonly label_colors: Array<{r: number, g: number, b: number}>

    constructor(params: {
        active_views: HashMap<Url, View, string>,
        label_colors: Array<{r: number, g: number, b: number}>,
    }){
        this.active_views = params.active_views
        this.label_colors = params.label_colors
    }

    public static fromJsonValue(value: JsonValue): ViewerAppletState{
        const value_obj = ensureJsonObject(value)
        let active_views = new HashMap<Url, View, string>();
        for(let view of ensureJsonArray(value_obj["active_views"]).map(raw_view => View.fromJsonValue(raw_view))){
            active_views.set(view.url, view)
        }
        return new ViewerAppletState({
            active_views,
            label_colors: ensureJsonArray(value_obj["label_colors"]).map(raw_color => {
                const color_obj = ensureJsonObject(raw_color)
                return {
                    r: ensureJsonNumber(color_obj["r"]),
                    g: ensureJsonNumber(color_obj["g"]),
                    b: ensureJsonNumber(color_obj["b"]),
                }
            })
        })
    }
}

export class Viewer extends Applet<ViewerAppletState>{
    public readonly driver: IViewerDriver;
    private onViewportsChangedHandlers = new Array<() => void>();
    private state: ViewerAppletState = new ViewerAppletState({active_views: new HashMap(), label_colors: []})

    private stateSwitchingPromise?: Promise<undefined>
    private resolveStateSwitching?: () => void
    private gotFirstState: boolean = false

    public constructor(params: {
        name: string,
        driver: IViewerDriver,
        ilastik_session: Session
    }){
        super({
            name: params.name,
            session: params.ilastik_session,
            deserializer: ViewerAppletState.fromJsonValue,
            onNewState: (newState) => this.onNewState(newState)
        })
        this.driver = params.driver
        const onViewportsChangedHandler = async () => {
            for(let handler of this.onViewportsChangedHandlers){
                // call handlers so they can react to e.g. layers hiding/showing
                handler() //FIXME
            }

            let {missingUpstream, removedDownstream} = this.diffNativeAndUpstreamViews()
            if(this.resolveStateSwitching !== undefined){
                if(missingUpstream.length == 0 && removedDownstream.length == 0){
                    this.resolveStateSwitching()
                }
                return
            }

            if(missingUpstream.length > 0){
                this.doRPC("add_native_views", {native_views: missingUpstream})
            }
            if(removedDownstream.length > 0){
                this.doRPC("remove_native_views", {native_views: removedDownstream})
            }
        }
        this.driver.onViewportsChanged(onViewportsChangedHandler)
    }

    private diffNativeAndUpstreamViews(): {missingUpstream: {name: string, url: Url}[], removedDownstream: {name: string, url: Url}[]}{
        let nativeViews = this.driver.getOpenDataViews()
        let missingUpstream = new Array<{name: string, url: Url}>()
        for(let nativeView of nativeViews){
            let nativeViewUrl = Url.parse(nativeView.url)
            if(!this.state.active_views.has(nativeViewUrl)){
                missingUpstream.push({name: nativeViewUrl.name, url: nativeViewUrl})
            }
        }
        let removedDownstream = new Array<{name: string, url: Url}>()
        for(let view of this.state.active_views.values()){
            if(!nativeViews.find(nv => Url.parse(nv.url).equals(view.url))){
                removedDownstream.push({name: view.name, url: view.url})
            }
        }
        return {missingUpstream, removedDownstream}
    }

    private async onNewState(newState: ViewerAppletState){
        if(!this.gotFirstState){
            let missingUpstream = this.diffNativeAndUpstreamViews().missingUpstream
            this.doRPC("add_native_views", {native_views: missingUpstream}) //once the state comes back it will have everything
            this.gotFirstState = true
            return
        }
        if(this.stateSwitchingPromise !== undefined){
            let acuallyDoIt = () => {
                this.onNewState(newState)
            }
            this.stateSwitchingPromise.then(acuallyDoIt, acuallyDoIt)
            return
        }

        this.state = newState

        this.stateSwitchingPromise = new Promise((resolve, _reject) => {
            this.resolveStateSwitching = () => {
                resolve(undefined)
                this.resolveStateSwitching = undefined
                this.stateSwitchingPromise = undefined
            }
        })

        let nativeViews = this.driver.getOpenDataViews()
        // Close all native views that are not in the new state

        let expectingChanges = false
        for(let native_view of nativeViews){
            let native_view_url = Url.parse(native_view.url)
            if(!newState.active_views.has(native_view_url)){
                this.driver.closeView({native_view})
                expectingChanges = true
            }
        }
        let channel_colors = newState.label_colors.map(c => vec3.fromValues(c.r, c.g, c.b))
        // open all missing views
        for(let view of newState.active_views.values()){
            if(nativeViews.find(nv => Url.parse(nv.url).equals(view.url))){
                continue
            }
            this.driver.refreshView({
                native_view: view.toNative(),
                channel_colors: view instanceof PredictionsView ? channel_colors : undefined
            })
            expectingChanges = true
        }

        if(!expectingChanges && this.resolveStateSwitching){
            this.resolveStateSwitching()
        }
    }

    public getViews(): Array<View>{
        return this.state.active_views.values()
    }

    public findView(view: View) : View | undefined{
        //FIXME: is this safe? think auto-context
        //also, training on raw data that has a single scale?
        return this.state.active_views.get(view.url)
    }

    public closeView(view: View){
        this.driver.closeView({native_view: view.toNative()})
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
        this.driver.refreshView({channel_colors, native_view: view.toNative()})
    }

    public openDatasource(params: {name: string, datasource: DataSource}){
        this.doRPC("open_datasource", {
            name: params.name, datasource: params.datasource
        })
    }

    public getActiveView(): View | undefined{
        const native_view = this.driver.getDataViewOnDisplay()
        if(native_view === undefined){
            return undefined
        }
        return this.state.active_views.get(Url.parse(native_view.url))
    }

    public destroy(){
        //FIXME: unregister events from native viewer using the driver
    }
}
