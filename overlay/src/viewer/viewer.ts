// import { vec3 } from "gl-matrix";
// import { quat, vec3 } from "gl-matrix";
import { FsDataSource, Session } from "../client/ilastik";
import { IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { CssClasses } from "../gui/css_classes";
import { Button } from "../gui/widgets/input_widget";
import { PixelClassificationLaneWidget } from "../gui/widgets/layer_widget";
// import { ErrorPopupWidget } from "../gui/widgets/popup";
import { Table, Th, THead } from "../gui/widgets/widget";
import { Quat, Vec3 } from "../util/ooglmatrix";


export class Viewer{
    public readonly driver: IViewerDriver;
    public readonly session: Session;

    private recenterButton: Button<"button">;
    private onViewportsChangedHandlers: Array<() => void> = []
    private onDataChangedHandlers: Array<() => void> = []

    private element: Table;
    private laneWidgets: PixelClassificationLaneWidget[] = []

    public constructor(params: {
        driver: IViewerDriver,
        session: Session,
        parentElement: HTMLElement
    }){
        this.session = params.session
        this.driver = params.driver

        this.element = new Table({parentElement: params.parentElement, cssClasses: [CssClasses.ItkTable], children: [
            new THead({parentElement: undefined, children: [
                new Th({parentElement: undefined, innerText: "Name"}),
                new Th({parentElement: undefined, innerText: "Visible"}),
                new Th({parentElement: undefined, innerText: "Controls"}),
            ]})
        ]})
        this.recenterButton = new Button({
            inputType: "button",
            parentElement: document.body,
            cssClasses: [CssClasses.ItkRecenterButton],
            text: "Recenter",
            onClick: () => {
                let activeDataSource = this.getActiveLaneWidget()?.rawData
                if(!this.driver.snapTo || !activeDataSource){
                    return
                }


                const dataset_center_voxel = new Vec3<"voxel">(activeDataSource.shape.toXyzVec3()).scale(0.5)
                const dataset_center_world = dataset_center_voxel.transformedWith(
                    //FIXME: assumes first viewport is special. The architecture assumes independent viewports but in NG they are locked
                    //to each other
                    this.driver.getViewportDrivers()[0].getVoxelToWorldMatrix({voxelSizeInNm: activeDataSource.spatial_resolution})
                )

                this.driver.snapTo({
                    position_w: dataset_center_world, orientation_w: Quat.identity<"world">(),
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

    public handleLaneVisibilityChange(changedLane: PixelClassificationLaneWidget){
        const otherLanes = this.laneWidgets.filter(lw => lw != changedLane)
        let visibleLane: PixelClassificationLaneWidget | undefined;
        if(changedLane.isVisible){
            visibleLane = changedLane
            otherLanes.forEach(lw => lw.setVisible(false))
        }else{
            otherLanes[0]?.setVisible(true)
            visibleLane = otherLanes[0]
        }

        if(visibleLane){
            this.driver.enable3dNavigation(visibleLane.rawData.shape.z > 1)
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
            onVisibilityChanged: (lane) => this.handleLaneVisibilityChange(lane),
            onDestroyed: (lane) => {
                let laneIndex = this.laneWidgets.indexOf(lane);
                (this.laneWidgets[laneIndex + 1] || this.laneWidgets[laneIndex - 1])?.setVisible(true)
                this.laneWidgets.splice(laneIndex, 1)
            },
        })
        if(laneResult instanceof Error){
            return laneResult
        }
        this.laneWidgets.push(laneResult)
        this.handleLaneVisibilityChange(laneResult)
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
