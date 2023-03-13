// import { vec3 } from "gl-matrix";
// import { quat, vec3 } from "gl-matrix";
import { FsDataSource, Session } from "../client/ilastik";
import { IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { CssClasses } from "../gui/css_classes";
import { Button } from "../gui/widgets/input_widget";
import { PixelClassificationLaneWidget } from "../gui/widgets/layer_widget";
// import { ErrorPopupWidget } from "../gui/widgets/popup";
import { Div } from "../gui/widgets/widget";
// import { PredictionsView, DataView, ViewUnion, RawDataView, StrippedPrecomputedView } from "./view";





export class Viewer{
    public readonly driver: IViewerDriver;
    public readonly session: Session;

    private recenterButton: Button<"button">;
    private onViewportsChangedHandlers: Array<() => void> = []
    private onDataChangedHandlers: Array<() => void> = []

    private element: Div;
    private laneWidgets: PixelClassificationLaneWidget[] = []

    public constructor(params: {
        driver: IViewerDriver,
        session: Session,
        parentElement: HTMLElement
    }){
        this.session = params.session
        this.driver = params.driver

        this.element = new Div({parentElement: params.parentElement})
        this.recenterButton = new Button({
            inputType: "button",
            parentElement: document.body,
            cssClasses: [CssClasses.ItkRecenterButton],
            text: "Recenter",
            onClick: () => {
                if(!this.driver.snapTo){
                    return
                }
                // let activeDataSource = this.getBiggestActiveDatasource();
                // if(!activeDataSource){
                //     return
                // }

                // const position_vx = vec3.create();
                // vec3.div(position_vx, activeDataSource.shape.toXyzVec3(), vec3.fromValues(2,2,2)),

                // this.driver.snapTo({
                //     position_vx, voxel_size_nm: activeDataSource.spatial_resolution, orientation_w: quat.identity(quat.create()),
                // })
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

    public getLaneWidgets(): Array<PixelClassificationLaneWidget>{
        return this.laneWidgets.slice()
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

    public async openLane(params:{
        rawData: FsDataSource,
        name: string,
        isVisible: boolean,
    }): Promise<PixelClassificationLaneWidget | Error>{
        const laneResult = await PixelClassificationLaneWidget.create({
            session: this.session,
            driver: this.driver,
            parentElement: this.element,
            isVisible: params.isVisible,
            name: params.name,
            rawData: params.rawData,
            onVisibilityChanged: (lane) => {
                const otherLanes = this.laneWidgets.filter(lw => lw != lane)
                if(lane.isVisible){
                    otherLanes.forEach(lw => lw.setVisible(false))
                }else{
                    otherLanes[0]?.setVisible(true)
                }
            },
            onDestroyed: (lane) => {
                this.laneWidgets.splice(this.laneWidgets.indexOf(lane), 1)
                this.laneWidgets[0]?.setVisible(true)
            },
        })
        if(laneResult instanceof Error){
            return laneResult
        }
        for(const lane of this.laneWidgets){
            lane.setVisible(false)
        }
        this.laneWidgets.push(laneResult)
        return laneResult
    }

    public getActiveLaneWidget(): PixelClassificationLaneWidget | undefined{
        for(const widget of this.getLaneWidgets()){
            if(widget.isVisible){
                return widget
            }
        }
        return undefined
    }

    public destroy(){
        this.recenterButton.destroy()
        this.element.destroy()
        for(const laneWidget of this.laneWidgets){
            laneWidget.destroy()
        }
        this.onViewportsChangedHandlers.forEach(handler => this.driver.removeViewportsChangedHandler(handler))
        this.driver.removeViewportsChangedHandler(this.viewportsChangedHandler)
    }
}
