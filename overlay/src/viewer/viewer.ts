// import { vec3 } from "gl-matrix";
import { vec3 } from "gl-matrix";
import { Applet } from "../client/applets/applet";
import { DataSource, PredictionsView, Session, View, DataView } from "../client/ilastik";
import { INativeView, IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { HashMap } from "../util/hashmap";
import { Url } from "../util/parsed_url";
import { ensureJsonArray, ensureJsonNumber, ensureJsonObject, JsonValue, toJsonValue } from "../util/serialization";


export class ViewerAppletState{
    public readonly data_views: HashMap<Url, DataView, string>
    public readonly prediction_views: HashMap<Url, PredictionsView, string>
    public readonly label_colors: Array<{r: number, g: number, b: number}>

    constructor(params: {
        data_views: HashMap<Url, DataView, string>,
        prediction_views: HashMap<Url, PredictionsView, string>,
        label_colors: Array<{r: number, g: number, b: number}>,
    }){
        this.data_views = params.data_views
        this.prediction_views = params.prediction_views
        this.label_colors = params.label_colors
    }

    public static fromJsonValue(value: JsonValue): ViewerAppletState{
        const value_obj = ensureJsonObject(value)
        let data_views = new HashMap<Url, DataView, string>();
        for(let view of ensureJsonArray(value_obj["data_views"]).map(raw_view => DataView.fromJsonValue(raw_view))){
            data_views.set(view.url, view)
        }

        let prediction_views = new HashMap<Url, PredictionsView, string>()
        for(let view of ensureJsonArray(value_obj["prediction_views"]).map(raw_view => PredictionsView.fromJsonValue(raw_view))){
            prediction_views.set(view.url, view)
        }

        return new ViewerAppletState({
            data_views,
            prediction_views,
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
    private state: ViewerAppletState = new ViewerAppletState({
        data_views: new HashMap(), prediction_views: new HashMap(), label_colors: []
    })

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
            let nativeViews = this.driver.getOpenDataViews().map(nv => ({name: nv.name, url: Url.parse(nv.url)}))
            this.setDataViews(nativeViews)
        }
        this.driver.onViewportsChanged(onViewportsChangedHandler)
        this.setDataViews(
            this.driver.getOpenDataViews().map(nv => ({name: nv.name, url: Url.parse(nv.url)}))
        )
    }

    public setDataViews(nativeViews: Array<{name: string, url: Url}>){
        console.log(`Setting data views to\n${
            JSON.stringify(toJsonValue(nativeViews), null, 2)
        }`)
        this.doRPC("set_data_views", {frontend_timestamp: new Date().getTime(), native_views: nativeViews})
    }

    private async onNewState(newState: ViewerAppletState){
        console.log(`Got new state:\n${
            JSON.stringify(
                {
                    data_views: newState.data_views.values().map(dv => ({name: dv.name, url: dv.url.toString()})),
                    prediction_views: newState.prediction_views.values().map(dv => ({name: dv.name, url: dv.url.toString()}))
                },
                null,
                2
            )
        }`)

        let oldState = this.state
        this.state = newState

        let nativeViewsMap = new HashMap<Url, INativeView, string>()
        for(let nativeView of this.driver.getOpenDataViews()){
            nativeViewsMap.set(Url.parse(nativeView.url), nativeView);
        }

        // Close all stale Predictions native views
        for(let [nativeViewUrl, nativeView] of nativeViewsMap.entries()){
            if(oldState.prediction_views.has(nativeViewUrl) && !newState.prediction_views.has(nativeViewUrl)){
                console.log(`Removing stale predictions: ${nativeViewUrl}`)
                this.driver.closeView({native_view: nativeView})
            }
        }

        let channel_colors: vec3[] = newState.label_colors.map(c => vec3.fromValues(c.r, c.g, c.b))

        // open all missing PredictionView's
        for(let view of newState.prediction_views.values()){
            if(!nativeViewsMap.has(view.url)){
                this.driver.refreshView({native_view: view.toNative(), channel_colors: channel_colors})
            }
        }

        for(let handler of this.onViewportsChangedHandlers){
            // call handlers so they can react the actual Views coming down from upstream
            handler() //FIXME
        }
    }

    public getViews(): Array<View>{
        return [...this.state.data_views.values(), ...this.state.prediction_views.values()]
    }

    public findView(view: View) : View | undefined{
        //FIXME: is this safe? think auto-context
        //also, training on raw data that has a single scale?
        return this.state.data_views.get(view.url) || this.state.prediction_views.get(view.url)
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
        let viewUrl = Url.parse(native_view.url)
        return this.state.data_views.get(viewUrl) || this.state.prediction_views.get(viewUrl)
    }

    public destroy(){
        //FIXME: unregister events from native viewer using the driver
    }
}
