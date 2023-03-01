// import { vec3 } from "gl-matrix";
// import { quat, vec3 } from "gl-matrix";
import { Color, FsDataSource, Session } from "../client/ilastik";
import { INativeView, IViewerDriver, IViewportDriver } from "../drivers/viewer_driver";
import { CssClasses } from "../gui/css_classes";
import { Button } from "../gui/widgets/input_widget";
import { ErrorPopupWidget } from "../gui/widgets/popup";
// import { ErrorPopupWidget } from "../gui/widgets/popup";
import { ContainerWidget, Div, Paragraph, Span } from "../gui/widgets/widget";
import { generationalAwait, StaleResult, uuidv4 } from "../util/misc";
// import { PredictionsView, DataView, ViewUnion, RawDataView, StrippedPrecomputedView } from "./view";

export class LaneWidget<VIEW extends INativeView>{
    private session: Session;
    private driver: IViewerDriver<VIEW>;

    private rawDataView: VIEW;
    private rawData: FsDataSource

    private predictionsView: VIEW | undefined
    private classifierGeneration = -1
    private predictionChannelColors?: Color[]

    public readonly element: Paragraph;
    protected nameWidget: Span;
    protected visibilityButton: Button<"button">;
    private _isVisible: boolean

    public get isVisible(): boolean{
        return this._isVisible
    }

    private constructor(params: {
        driver: IViewerDriver<VIEW>,
        session: Session,
        name: string,
        parentElement: ContainerWidget<any>,
        rawData: FsDataSource,
        rawDataView: VIEW,
        isVisible: boolean,
        onVisibilityChanged: (lane: LaneWidget<VIEW>) => void,
        onViewDeleted: (lane: LaneWidget<VIEW>) => void,
    }){
        this.driver = params.driver
        this.session = params.session
        this.rawData = params.rawData
        this.rawDataView = params.rawDataView
        this._isVisible = params.isVisible
        this.element = new Paragraph({parentElement: params.parentElement, children: [
            this.nameWidget = new Span({
                parentElement: undefined, innerText: params.name, title: this.rawData.url.raw
            }),
            this.visibilityButton = new Button({inputType: "button", text: this.rawDataView.getVisible() ? "👁️" : "🫥", parentElement: undefined, onClick: () => {
                let isVisible = !this.rawDataView.getVisible()
                this.rawDataView.reconfigure({isVisible})
                this.predictionsView?.reconfigure({isVisible})
                this.visibilityButton.text = isVisible ? "👁️" : "🫥"
                params.onVisibilityChanged(this)
            }}),
            new Button({inputType: "button", text: "✖", parentElement: undefined, onClick: () => {
                this.destroy()
                params.onViewDeleted(this)
            }})
        ]})
    }

    public closePredictions(){
        this.predictionsView?.close()
    }

    public reconfigure(params: {
        isVisible?: boolean,
        predictionsOpacity?: number,
        predictionChannelColors?: Color[],
    }){
        this._isVisible = params.isVisible === undefined ? this.isVisible : params.isVisible
        this.rawDataView.reconfigure({})
        this.predictionsView?.reconfigure({
            channelColors: params.predictionChannelColors,
            opacity: params.predictionsOpacity,
        })
    }

    public static async open<VIEW extends INativeView>(params: {
        driver: IViewerDriver<VIEW>,
        session: Session,
        name: string,
        parentElement: ContainerWidget<any>,
        rawData: FsDataSource,
        predictionsView?: VIEW,
        isVisible: boolean,
        onVisibilityChanged: (lane: LaneWidget<VIEW>) => void,
        onViewDeleted: (lane: LaneWidget<VIEW>) => void,
    }): Promise<LaneWidget<VIEW> | Error>{
        const nativeViewResult = await params.driver.openDataSource({
            datasource: params.rawData,
            name: uuidv4(),
            opacity: 1,
            session: params.session,
            isVisible: params.isVisible,
        })
        if(nativeViewResult instanceof Error){
            return nativeViewResult
        }
        return new this({
            ...params,
            rawDataView: nativeViewResult
        })
    }

    public async refreshPredictons(params: {classifierGeneration: number, channelColors?: Color[]}){
        if(this.classifierGeneration >= params.classifierGeneration){
            return
        }
        const predictionsUrl = this.session.sessionUrl
            .updatedWith({datascheme: "precomputed"})
            .joinPath(`predictions/raw_data=${this.rawData.toBase64()}/generation=${params.classifierGeneration}`)
        if(this.predictionsView){
            this.predictionsView.reconfigure({
                url: predictionsUrl,
                channelColors: params.channelColors || this.predictionChannelColors,
            })
            return
        }
        let nativeViewResult = await generationalAwait({
            setGen: () => {this.classifierGeneration = params.classifierGeneration},
            getGen: () => this.classifierGeneration,
            promise: this.driver.openUrl({
                name: `predictions for ${this.rawDataView.getName()}`,
                url: predictionsUrl,
                opacity: 0.5,
                isVisible: this.isVisible,
                channelColors: params.channelColors,
            })
        })
        if(nativeViewResult instanceof StaleResult){
            if(!(nativeViewResult.result instanceof Error)){
                nativeViewResult.result.close()
            }
            return
        }
        if(nativeViewResult instanceof Error){
            new ErrorPopupWidget({message: nativeViewResult.message})
            return
        }
        this.predictionsView = nativeViewResult
    }

    public destroy(){
        this.element.destroy()
        this.rawDataView.close()
        this.predictionsView?.close()
    }
}

export class Viewer<VIEW extends INativeView>{
    public readonly driver: IViewerDriver<VIEW>;
    public readonly session: Session;

    private recenterButton: Button<"button">;
    private onViewportsChangedHandlers: Array<() => void> = []
    private onDataChangedHandlers: Array<() => void> = []

    private laneWidgetsContainer: Div;
    private laneWidgets: LaneWidget<VIEW>[] = []

    public constructor(params: {
        driver: IViewerDriver<VIEW>,
        session: Session,
        parentElement: HTMLElement
    }){
        this.session = params.session
        this.driver = params.driver

        this.laneWidgetsContainer = new Div({parentElement: params.parentElement})
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

    public getLaneWidgets(): Array<LaneWidget<VIEW>>{
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
        opacity: number,
        isVisible: boolean,
    }): Promise<LaneWidget<VIEW> | Error>{
        const viewWidgetResult = await LaneWidget.open({
            ...params,
            session: this.session,
            driver: this.driver,
            parentElement: this.laneWidgetsContainer,
            onVisibilityChanged: () => {}, //FIXME
            onViewDeleted: () => {}, //FIXME
        })
        if(viewWidgetResult instanceof Error){
            return viewWidgetResult
        }
        this.laneWidgets.push(viewWidgetResult)
        return viewWidgetResult
    }

    public getActiveLaneWidget(): LaneWidget<VIEW> | undefined{
        for(const widget of this.getLaneWidgets()){
            if(widget.isVisible){
                return widget
            }
        }
        return undefined
    }

    public destroy(){
        this.recenterButton.destroy()
        this.laneWidgetsContainer.destroy()
        this.onViewportsChangedHandlers.forEach(handler => this.driver.removeViewportsChangedHandler(handler))
        this.driver.removeViewportsChangedHandler(this.viewportsChangedHandler)
    }
}
