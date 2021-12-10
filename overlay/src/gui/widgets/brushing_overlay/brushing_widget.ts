import { quat, vec3 } from "gl-matrix"
import { BrushStroke } from "../../.."
import { DataSource, Session } from "../../../client/ilastik"
import { createElement, createInputParagraph, removeElement } from "../../../util/misc"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { OneShotSelectorWidget, SelectorWidget } from "../selector_widget"
import { Vec3ColorPicker } from "../vec3_color_picker"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushelLinesRenderer } from "./brush_lines_renderer"
import { BrushRenderer } from "./brush_renderer"
import { BrushStrokesContainer } from "./brush_strokes_container"
import { Viewer } from "../../../viewer/viewer"
import { PredictionsView, RawDataView, TrainingView } from "../../../viewer/view"

export class BrushingWidget{
    public readonly gl: WebGL2RenderingContext
    public readonly viewer: Viewer
    public readonly element: HTMLElement
    public readonly canvas: HTMLCanvasElement
    public readonly status_display: HTMLElement

    public readonly brushStrokeContainer: BrushStrokesContainer
    private readonly controlsContainer: HTMLElement
    private animationRequestId: number = 0
    private trainingWidget: TrainingWidget | undefined = undefined
    session: Session

    constructor({
        session,
        socket,
        parentElement,
        viewer,
    }: {
        session: Session,
        socket: WebSocket,
        parentElement: HTMLElement,
        viewer: Viewer,
    }){
        this.session = session
        this.element = new CollapsableWidget({display_name: "Training", parentElement}).element
        this.element.classList.add("ItkBrushingWidget")
        this.canvas =  createElement({tagName: "canvas", parentElement: document.body}) as HTMLCanvasElement;
        this.gl = this.canvas.getContext("webgl2", {depth: true, stencil: true})!
        this.viewer = viewer

        this.status_display = createElement({tagName:"p", parentElement: this.element, cssClasses: ["ItkBrushingWidget_status_display"]})
        this.controlsContainer = createElement({tagName: "p", parentElement: this.element})

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Brush Strokes:", parentElement: p})
        this.brushStrokeContainer = new BrushStrokesContainer({
            socket,
            parentElement: this.element,
            applet_name: "brushing_applet",
            gl: this.gl,
            onBrushColorClicked: (color: vec3) => this.trainingWidget?.colorPicker.setColor(color)
        })

        this.showCanvas(false)
        viewer.onViewportsChanged(() => this.handleViewerDataDisplayChange())
        this.handleViewerDataDisplayChange()
    }

    private showCanvas(show: boolean){
        this.canvas.style.display = show ? "block" : "none"
    }

    public showStatus(message: string){
        this.status_display.innerHTML = message
    }

    public clearStatus(){
        this.status_display.innerHTML = ""
    }

    private resetWidgets(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.trainingWidget?.destroy()
        this.controlsContainer.innerHTML = ""
        this.showCanvas(false)
        this.clearStatus()
    }

    private async openTrainingView(training_view: TrainingView){
        if(!this.viewer.findView(training_view)){
            this.viewer.refreshView({view: training_view})
        }
    }

    private async handleViewerDataDisplayChange(){
        this.resetWidgets()

        const view = this.viewer.getActiveView()
        if(view === undefined){
            return
        }
        if(view instanceof Error){ //FIXME: remove this? or return error from viewer?
            return this.showStatus(`${view}`)
        }
        if(view instanceof TrainingView){
            return this.startTraining(view.raw_data)
        }
        if(view instanceof PredictionsView){
            //FIXME: allow more annotations?
            return this.showStatus(`Showing predictions for ${view.raw_data.getDisplayString()}`)
        }
        if(!(view instanceof RawDataView)){
            throw `Unexpected view type (${view.constructor.name}): ${JSON.stringify(view)}`
        }
        if(view.datasources.length == 1){
            const datasource = view.datasources[0]
            const training_view = view.toTrainingView({resolution: datasource.spatial_resolution, session: this.session})
            this.openTrainingView(training_view)
            return this.startTraining(training_view.raw_data)
        }

        createElement({tagName: "label", innerHTML: "Select a voxel size to annotate on:", parentElement: this.controlsContainer});
        new OneShotSelectorWidget<DataSource>({
            parentElement: this.controlsContainer,
            options: view.datasources,
            optionRenderer: (datasource) => `${datasource.spatial_resolution[0]} x ${datasource.spatial_resolution[1]} x ${datasource.spatial_resolution[2]} nm`,
            onOk: async (datasource) => {
                const training_view = view.toTrainingView({resolution: datasource.spatial_resolution, session: this.session})
                this.openTrainingView(training_view)
            },
        })
    }

    private startTraining(datasource: DataSource){
        this.resetWidgets()
        this.showCanvas(true)

        this.trainingWidget = new TrainingWidget({
            gl: this.gl,
            parentElement: this.controlsContainer,
            onNewBrushStroke: stroke => this.brushStrokeContainer.addBrushStroke(stroke),
            datasource,
            brushingEnabled: this.trainingWidget ? this.trainingWidget.getBrushingEnabled() : false,
            viewer: this.viewer
        })
        this.showStatus(`Now training on ${datasource.getDisplayString()}`)
        window.cancelAnimationFrame(this.animationRequestId)
        const render = () => {
            this.trainingWidget?.render(this.brushStrokeContainer.getBrushStrokes())
            this.animationRequestId = window.requestAnimationFrame(render)
        }
        render()
    }

    public destroy(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.trainingWidget?.destroy()
        this.brushStrokeContainer.destroy()
        removeElement(this.element)
        removeElement(this.canvas)
    }
}


export class TrainingWidget{
    public readonly element: HTMLElement
    public readonly overlay: BrushingOverlay
    public staging_brush_stroke: BrushStroke | undefined = undefined
    public readonly rendererSelector: SelectorWidget<BrushRenderer>
    public readonly colorPicker: Vec3ColorPicker
    public readonly datasource: DataSource
    public readonly brushing_enabled_checkbox: HTMLInputElement

    constructor({gl, parentElement, datasource, viewer, brushingEnabled, onNewBrushStroke}: {
        gl: WebGL2RenderingContext,
        parentElement: HTMLElement,
        datasource: DataSource,
        viewer: Viewer,
        brushingEnabled: boolean,
        onNewBrushStroke: (stroke: BrushStroke) => void,
    }){
        this.element = createElement({tagName: "div", parentElement})
        this.datasource = datasource

        this.brushing_enabled_checkbox = createInputParagraph({
            label_text: "Enable Brushing: ", inputType: "checkbox", parentElement: this.element, onClick: () => {
                this.overlay.setBrushingEnabled(this.brushing_enabled_checkbox.checked)
            }
        })

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Brush Color: ", parentElement: p})
        this.colorPicker = new Vec3ColorPicker({parentElement: p})

        p = createElement({tagName: "p", parentElement: this.element, inlineCss: {display: (window as any).ilastik_debug ? "block" : "none"}})
        createElement({tagName: "label", innerHTML: "Rendering style: ", parentElement: p})
        this.rendererSelector = new SelectorWidget<BrushRenderer>({
            parentElement: p,
            options: [
                new BrushelBoxRenderer({gl, highlightCrossSection: false, onlyCrossSection: true}),
                new BrushelLinesRenderer(gl),
                new BrushelBoxRenderer({gl, debugColors: false, highlightCrossSection: false, onlyCrossSection: false}),
                new BrushelBoxRenderer({gl, debugColors: true, highlightCrossSection: true, onlyCrossSection: false}),
            ],
            optionRenderer: (_, index) => ["Boxes - Cross Section", "Lines", "Boxes", "Boxes (debug colors)"][index],
            onSelection: (_) => {},
        })

        this.overlay = new BrushingOverlay({
            gl,
            trackedElement: viewer.getTrackedElement(),
            viewport_drivers: viewer.getViewportDrivers(),
            brush_stroke_handler: {
                handleNewBrushStroke: (params: {start_position_uvw: vec3, camera_orientation_uvw: quat}) => {
                    this.staging_brush_stroke = BrushStroke.create({
                        gl,
                        start_postition_uvw: params.start_position_uvw, //FIXME put scale somewhere
                        color: this.colorPicker.getColor(),
                        annotated_data_source: datasource,
                        camera_orientation: params.camera_orientation_uvw, //FIXME: realy data space? rename param in BrushStroke?
                    })
                    return this.staging_brush_stroke
                },
                handleFinishedBrushStroke: (stroke) => {
                    this.staging_brush_stroke = undefined
                    onNewBrushStroke(stroke)
                }
            },
        })

        if(brushingEnabled){
            this.brushing_enabled_checkbox.click()
        }
    }

    public getBrushingEnabled(): boolean{
        return this.brushing_enabled_checkbox.checked
    }

    public render(brushStrokes: Array<BrushStroke>){
        let strokes = brushStrokes.filter(stroke => stroke.annotated_data_source.equals(this.datasource))
        if(this.staging_brush_stroke){
            strokes.push(this.staging_brush_stroke)
        }
        this.overlay.render(strokes, this.rendererSelector.getSelection())
    }

    public destroy(){
        this.overlay.destroy()
        removeElement(this.element)
    }
}
