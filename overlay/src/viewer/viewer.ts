// import { vec3 } from "gl-matrix";
import { quat, vec3 } from "gl-matrix";
import { FsDataSource, Session } from "../client/ilastik";
import { IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { CssClasses } from "../gui/css_classes";
import { Button } from "../gui/widgets/input_widget";
import { ErrorPopupWidget } from "../gui/widgets/popup";
import { HashMap } from "../util/hashmap";
import { Url } from "../util/parsed_url";
import { View, PredictionsView, DataView, FailedView, ViewUnion } from "./view";


export class Viewer{
    public readonly driver: IViewerDriver;
    public readonly session: Session;

    private readonly cached_views = new HashMap<Url, ViewUnion, string>();
    private views = new HashMap<Url, ViewUnion, string>();
    private dataViewsGeneration = 0;
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
                let activeView = this.getActiveView()
                if(!activeView){
                    return
                }
                let activeDataSource: FsDataSource
                if(activeView instanceof DataView){
                    let datasources = activeView.getDatasources()
                    if(!datasources){
                        return
                    }
                    datasources.sort((a,b) => a.shape.volume - b.shape.volume)
                    activeDataSource = datasources[0]
                }else{
                    activeDataSource = activeView.raw_data
                }

                const position_uvw = vec3.create();
                vec3.div(position_uvw, activeDataSource.shape.toXyzVec3(), vec3.fromValues(2,2,2)),
                vec3.mul(position_uvw, position_uvw, activeDataSource.spatial_resolution),

                this.driver.snapTo({
                    position_uvw, orientation_uvw: quat.identity(quat.create()),
                })
            }
        })

        this.driver.addViewportsChangedHandler(this.synchronizeWithNativeViews)
        this.updateZScrolling()
        this.synchronizeWithNativeViews()
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

    public synchronizeWithNativeViews = async () => {
        console.log("Synchronizing with native views............")
        let nativeViews = this.driver.getOpenDataViews().map(nv => ({name: nv.name, url: Url.parse(nv.url), opacity: nv.opacity}))
        const new_views = new HashMap<Url, ViewUnion, string>();
        const dataViewsGeneration = this.dataViewsGeneration = this.dataViewsGeneration + 1;
        for(const {name, url, opacity} of nativeViews){
            const cached_view = this.cached_views.get(url)
            if(cached_view !== undefined){
                new_views.set(url, cached_view)
                cached_view.opacity = opacity
                continue
            }
            const dataView = await View.tryOpen({name: name, url: url, session: this.session, opacity})
            if(!this.cached_views.has(dataView.url) || this.cached_views.get(dataView.url) instanceof FailedView){
                this.cached_views.set(dataView.url, dataView)
            }
            if(this.dataViewsGeneration != dataViewsGeneration){
                return
            }
            new_views.set(dataView.url, dataView)
        }
        this.views = new_views;
        this.updateZScrolling()
        for(const handler of this.onDataChangedHandlers){
            handler()
        }
    }

    private updateZScrolling(){
        if(this.driver.enableZScrolling){
            this.driver.enableZScrolling(this.getVolume()[2] > 1)
        }
    }

    public getViews(): Array<ViewUnion>{
        return [...this.views.values()]
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

    public addViewportsChangedHandler(handler: () => void){
        this.onViewportsChangedHandlers.push(handler)
        this.driver.addViewportsChangedHandler(handler)
    }

    public addDataChangedHandler(handler: () => void){
        this.onDataChangedHandlers.push(handler)
    }

    public removeDataChangedHandler(handler: () => void){
        let handlerIndex = this.onDataChangedHandlers.indexOf(handler)
        if(handlerIndex != -1){
            this.onDataChangedHandlers.splice(handlerIndex, 1)
            this.driver.removeDataChangedHandler(handler)
        }
    }

    public openDataView(view: ViewUnion){
        this.cached_views.set(view.url, view)
        this.driver.refreshView({
            native_view: view.toNative(),
            channel_colors: view instanceof PredictionsView ? view.channel_colors.map(c => c.vec3i) : undefined
        })
    }

    public async openDataViewFromDataSource({datasource, opacity}: {datasource: FsDataSource, opacity: number}){
        let name = datasource.url.path.name + " " + datasource.resolutionString
        const dataViewResult = await DataView.tryOpen({name, session: this.session, url: datasource.url, opacity})
        if(dataViewResult instanceof Error){
            new ErrorPopupWidget({message: `Could not create a view for ${datasource.url}: ${dataViewResult.message}`})
            return
        }
        this.openDataView(dataViewResult)
    }

    public getActiveView(): ViewUnion | undefined{
        const native_view = this.driver.getDataViewOnDisplay()
        if(native_view === undefined){
            return undefined
        }
        let viewUrl = Url.parse(native_view.url)
        return this.views.get(viewUrl)
    }

    public destroy(){
        this.recenterButton.destroy()
        this.onViewportsChangedHandlers.forEach(handler => this.driver.removeViewportsChangedHandler(handler))
        this.driver.removeDataChangedHandler(this.synchronizeWithNativeViews)
        if(this.driver.enableZScrolling){
            this.driver.enableZScrolling(true)
        }
    }
}
