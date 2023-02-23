// import { vec3 } from "gl-matrix";
import { quat, vec3 } from "gl-matrix";
import { FsDataSource, Session } from "../client/ilastik";
import { IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { CssClasses } from "../gui/css_classes";
import { Button } from "../gui/widgets/input_widget";
import { ErrorPopupWidget } from "../gui/widgets/popup";
import { HashMap } from "../util/hashmap";
import { Url } from "../util/parsed_url";
import { PredictionsView, DataView, ViewUnion, RawDataView, StrippedPrecomputedView } from "./view";


export class Viewer{
    public readonly driver: IViewerDriver;
    public readonly session: Session;

    private views = new HashMap<Url, ViewUnion, string>();
    private recenterButton: Button<"button">;
    private onViewportsChangedHandlers: Array<() => void> = []
    private onDataChangedHandlers: Array<() => void> = []

    public constructor(params: {
        driver: IViewerDriver,
        session: Session,
    }){
        this.session = params.session
        this.driver = params.driver
        this.recenterButton = new Button({
            inputType: "button",
            parentElement: document.body,
            cssClasses: [CssClasses.ItkRecenterButton],
            text: "Recenter",
            onClick: () => {
                if(!this.driver.snapTo){
                    return
                }
                let activeDataSource = this.getBiggestActiveDatasource();
                if(!activeDataSource){
                    return
                }

                const position_vx = vec3.create();
                vec3.div(position_vx, activeDataSource.shape.toXyzVec3(), vec3.fromValues(2,2,2)),

                this.driver.snapTo({
                    position_vx, voxel_size_nm: activeDataSource.spatial_resolution, orientation_w: quat.identity(quat.create()),
                })
            }
        })
        this.driver.addViewportsChangedHandler(this.viewportsChangedHandler)
    }

    private viewportsChangedHandler = () => {
        console.log(`VIEWER: viewportsChangedHandler is firing`)
        for(const handler of this.onViewportsChangedHandlers){
            handler()
        }
    }

    public getVolume(): vec3{
        let max = vec3.fromValues(0,0,0)
        for(let dv of this.views.values()){
            if(dv instanceof PredictionsView){ //FIXME: would be better if we didn't need this knowledge
                continue
            }
            for(let datasource of (dv.getDatasources() || [])){
                vec3.max(max, max, vec3.fromValues(datasource.shape.x, datasource.shape.y, datasource.shape.z))
            }
        }
        return max
    }

    private getBiggestActiveDatasource(): FsDataSource | undefined{
        let activeView = this.getActiveView()
        if(!activeView){
            return
        }
        if(activeView instanceof DataView){
            let datasources = activeView.getDatasources()
            if(!datasources){
                return
            }
            datasources.sort((a,b) => b.shape.volume - a.shape.volume)
            return datasources[0]
        }else{
            return activeView.raw_data
        }
    }

    public getViews(): Array<ViewUnion>{
        return [...this.views.values()]
    }

    public getViewportDrivers(): Array<IViewportDriver>{
        return this.driver.getViewportDrivers()
    }

    public getTrackedElement(): HTMLElement{
        return this.driver.getTrackedElement()
    }

    public addViewportsChangedHandler(handler: () => void){
        this.onViewportsChangedHandlers.push(handler)
        this.driver.addViewportsChangedHandler(handler)
    }

    public removeViewportsChangedHandler(handler: () => void){
        let handlerIndex = this.onViewportsChangedHandlers.indexOf(handler)
        if(handlerIndex != -1){
            this.onViewportsChangedHandlers.splice(handlerIndex, 1)
            this.driver.removeViewportsChangedHandler(handler)
        }
    }

    public addDataChangedHandler(handler: () => void){
        this.onDataChangedHandlers.push(handler)
    }

    public removeDataChangedHandler(handler: () => void){
        let handlerIndex = this.onDataChangedHandlers.indexOf(handler)
        if(handlerIndex != -1){
            this.onDataChangedHandlers.splice(handlerIndex, 1)
        }
    }

    public reconfigure(views: {toOpen?: ViewUnion[], toClose?: ViewUnion[]}){
        if((!views.toOpen || views.toOpen.length == 0) && (!views.toClose || views.toClose.length == 0)){
            return
        }
        console.log(`VIEWER: disabling viewportsChangedHandler`)
        this.driver.removeViewportsChangedHandler(this.viewportsChangedHandler)
        try{
            for(const view of views.toOpen || []){
                if(this.views.get(view.url)){
                    continue
                }
                this.views.set(view.url, view)
                this.driver.refreshView({
                    native_view: view.toNative(),
                    channel_colors: view instanceof PredictionsView ? view.channel_colors.map(c => c.vec3i) : undefined
                })
            }
            for(const view of views.toClose || []){
                if(!this.views.delete(view.url)){
                    continue
                }
                this.driver.closeView({native_view: view.toNative()})
                if(!(view instanceof RawDataView) && !(view instanceof StrippedPrecomputedView)){
                    continue
                }
                let predictionsRawData: FsDataSource
                if(view instanceof StrippedPrecomputedView){
                    predictionsRawData = view.datasource
                }else if(view instanceof RawDataView && view.datasources.length == 1){
                    predictionsRawData = view.datasources[0]
                }else{
                    continue
                }
                for(const v of this.getViews()){
                    if(v instanceof PredictionsView && v.raw_data.equals(predictionsRawData)){
                        console.log(`VIEWER: auto-closing predictions view: ${v.url.raw}`)
                        this.driver.closeView({native_view: v.toNative()})
                        break
                    }
                }
            }
        }finally{
            console.log(`VIEWER: re-enabling viewportsChangedHandler`)
            this.driver.addViewportsChangedHandler(this.viewportsChangedHandler)
        }
        console.log(`VIEWER: firing data-changed handlers`)
        for(const handler of this.onDataChangedHandlers){
            handler()
        }
        this.viewportsChangedHandler()
    }

    public async openDataViewFromDataSource({datasource, opacity, visible}: {
        datasource: FsDataSource, opacity: number, visible: boolean
    }){
        let name = datasource.url.path.name + " " + datasource.resolutionString
        const dataViewResult = await DataView.tryOpen({name, session: this.session, url: datasource.url, opacity, visible})
        if(dataViewResult instanceof Error){
            new ErrorPopupWidget({message: `Could not create a view for ${datasource.url}: ${dataViewResult.message}`})
            return
        }
        this.reconfigure({toOpen: [dataViewResult]})
    }

    public getActiveView(): ViewUnion | undefined{
        const native_view = this.driver.getDataViewOnDisplay()
        if(native_view === undefined){
            return undefined
        }
        let viewUrl = Url.parse(native_view.url)
        return this.views.get(viewUrl)
    }

    public getFirstDataView(): RawDataView | StrippedPrecomputedView | undefined{
        for(let view of this.views.values()){
            if(!view.visible){
                continue
            }
            if(view instanceof StrippedPrecomputedView || view instanceof RawDataView && view.datasources.length == 1){
                return view
            }
        }
        return undefined
    }

    public getPredictionView(): PredictionsView | undefined{
        for(let view of this.views.values()){
            if(view instanceof PredictionsView){
                return view
            }
        }
        return undefined
    }

    public destroy(){
        this.recenterButton.destroy()
        this.onViewportsChangedHandlers.forEach(handler => this.driver.removeViewportsChangedHandler(handler))
        this.driver.removeViewportsChangedHandler(this.viewportsChangedHandler)
    }
}
