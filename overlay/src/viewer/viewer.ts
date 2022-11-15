// import { vec3 } from "gl-matrix";
import { quat, vec3 } from "gl-matrix";
import { Applet } from "../client/applets/applet";
import { DataSource, PredictionsView, Session, View, DataView, RawDataView, StrippedPrecomputedView, DataViewUnion, Color } from "../client/ilastik";
import { MakeDataViewParams, ViewerAppletStateDto } from "../client/message_schema";
import { INativeView, IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { ErrorPopupWidget } from "../gui/widgets/popup";
import { HashMap } from "../util/hashmap";
import { createInput, removeElement } from "../util/misc";
import { Url } from "../util/parsed_url";


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

    public static fromDto(message: ViewerAppletStateDto): ViewerAppletState{
        let data_views = new HashMap<Url, DataViewUnion, string>();
        for(let rawViewMsg of message.data_views){
            const dataView = DataView.fromDto(rawViewMsg)
            data_views.set(dataView.url, dataView)
        }

        let prediction_views = new HashMap<Url, PredictionsView, string>();
        for(let predViewMsg of message.prediction_views){
            const predView = PredictionsView.fromDto(predViewMsg)
            prediction_views.set(predView.url, predView)
        }

        return new ViewerAppletState({
            data_views,
            prediction_views,
            label_colors: message.label_colors.map(color_msg => Color.fromDto(color_msg))
        })
    }
}

export class Viewer extends Applet<ViewerAppletState>{
    public readonly driver: IViewerDriver;
    private onViewportsChangedHandlers = new Array<() => void>();
    private state: ViewerAppletState = new ViewerAppletState({
        data_views: new HashMap(), prediction_views: new HashMap(), label_colors: []
    })
    recenterButton: HTMLInputElement;

    public constructor(params: {
        name: string,
        driver: IViewerDriver,
        ilastik_session: Session
    }){
        super({
            name: params.name,
            session: params.ilastik_session,
            deserializer: value => {
                let stateDto = ViewerAppletStateDto.fromJsonValue(value)
                if(stateDto instanceof Error){
                    throw `FIXME!`
                }
                return ViewerAppletState.fromDto(stateDto)
            },
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
        this.recenterButton = createInput({
            inputType: "button",
            parentElement: document.body,
            cssClasses: ["ItkRecenterButton"],
            value: "Recenter",
            onClick: () => {
                if(!this.driver.snapTo){
                    return
                }
                this.driver.snapTo({
                    position_uvw: vec3.div(vec3.create(), this.getVolume(), vec3.fromValues(2,2,2)),
                    orientation_uvw: quat.identity(quat.create()),
                })
            }
        })
    }

    public getVolume(): vec3{
        let max = vec3.fromValues(0,0,0)
        for(let dv of this.state.data_views.values()){
            for(let datasource of (dv.getDatasources() || [])){
                vec3.max(max, max, vec3.fromValues(datasource.shape.x, datasource.shape.y, datasource.shape.z))
            }
        }
        return max
    }

    public setDataViews(nativeViews: Array<{name: string, url: Url}>){
        for(let nv of nativeViews){
            if(!this.state.data_views.has(nv.url) && !this.state.prediction_views.has(nv.url)){
                this.doRPC("set_data_views", {frontend_timestamp: new Date().getTime(), native_views: nativeViews})
                return
            }
        }
    }



    private async onNewState(newState: ViewerAppletState){
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
        for(let predictionView of newState.prediction_views.values()){
            if(nativeViewsMap.has(predictionView.url)){
                continue
            }
            for(let [nativeUrl, nativeView] of nativeViewsMap.entries()){
                let dataView = newState.data_views.get(nativeUrl);
                let datasourceInView: DataSource;
                if(dataView instanceof RawDataView && dataView.datasources.length == 1){
                    datasourceInView = dataView.datasources[0]
                }else if(dataView instanceof StrippedPrecomputedView){
                    datasourceInView = dataView.datasource
                }else{
                    continue
                }
                if(datasourceInView.equals(predictionView.raw_data)){
                    this.driver.refreshView({native_view: predictionView.toNative(`Predicting on ${nativeView.name}`), channel_colors: channel_colors})
                    break
                }
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

    public openDataView(view: DataView){
        this.driver.refreshView({native_view: view.toNative()})
    }

    public async openDataViewFromDataSource(datasource: DataSource){
        let name = datasource.url.path.name + " " + datasource.resolutionString
        let dataViewResult = await this.session.makeDataView(new MakeDataViewParams({view_name: name, url: datasource.url.toDto()}))
        if(dataViewResult instanceof Error){
            new ErrorPopupWidget({message: `Could not create a view for ${datasource.url}: ${dataViewResult.message}`})
            return
        }
        this.openDataView(dataViewResult)
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
        removeElement(this.recenterButton)
        //FIXME: unregister events from native viewer using the driver
    }
}
