import { quat, vec3 } from "gl-matrix"
import { BrushStroke } from "../../.."
import { DataSource, Session } from "../../../client/ilastik"
import { awaitStalable, createElement, createInput, removeElement, StaleResult } from "../../../util/misc"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { OneShotSelectorWidget, SelectorWidget } from "../selector_widget"
import { Vec3ColorPicker } from "../vec3_color_picker"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushelLinesRenderer } from "./brush_lines_renderer"
import { BrushRenderer } from "./brush_renderer"
import { BrushStrokesContainer } from "./brush_strokes_container"
import { IDataScale } from "../../../datasource/datasource"
import { PixelPredictionsView, PixelTrainingView, Viewer } from "../../viewer"

export class BrushingWidget{
    public static training_view_name_prefix = "ilastik training: "

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
        this.trainingWidget?.destroy()
        this.controlsContainer.innerHTML = ""
        this.showCanvas(false)
        this.clearStatus()
    }

    private async openTrainingView(training_view: PixelTrainingView){
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
        if(view instanceof Error){
            return this.showStatus(`${view}`)
        }
        if(view instanceof PixelTrainingView){
            return this.startTraining(view.raw_data)
        }
        if(view instanceof PixelPredictionsView){
            //FIXME: allow more annotations?
            return this.showStatus(`Showing predictions for ${view.raw_data.getDisplayString()}`)
        }

        if(view.multiscale_datasource.scales.length == 1){
            const scale = view.multiscale_datasource.scales[0]
            const multiscale_datasource = await awaitStalable({referenceKey: "brushingGetMultiscaleDataSource", callable: () => scale.toStrippedMultiscaleDataSource(this.session)})
            if(multiscale_datasource instanceof StaleResult){
                return
            }
            const training_view = new PixelTrainingView({
                multiscale_datasource: multiscale_datasource,
                name: `pixel classification: ${scale.toDisplayString()}`,
                raw_data: scale.toIlastikDataSource()
            })
            this.openTrainingView(training_view)
            return this.startTraining(training_view.raw_data)
        }

        createElement({tagName: "label", innerHTML: "Select a voxel size to annotate on:", parentElement: this.controlsContainer});
        new OneShotSelectorWidget<IDataScale>({
            parentElement: this.controlsContainer,
            options: view.multiscale_datasource.scales,
            optionRenderer: (scale) => scale.toDisplayString(),
            onOk: async (scale) => {
                const training_view = new PixelTrainingView({
                    multiscale_datasource: await scale.toStrippedMultiscaleDataSource(this.session),
                    name: `pixel classification: ${scale.toDisplayString()}`,
                    raw_data: scale.toIlastikDataSource()
                })
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
            viewer: this.viewer
        })
        this.showStatus(`Now training on ${datasource.getDisplayString()}`)
        window.cancelAnimationFrame(this.animationRequestId)
        const render = () => {
            this.trainingWidget?.render(this.brushStrokeContainer.getBrushStrokes())
            this.animationRequestId = window.requestAnimationFrame(render)
        }
        this.animationRequestId = window.requestAnimationFrame(render)
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

    constructor({gl, parentElement, datasource, viewer, onNewBrushStroke}: {
        gl: WebGL2RenderingContext,
        parentElement: HTMLElement,
        datasource: DataSource,
        viewer: Viewer,
        onNewBrushStroke: (stroke: BrushStroke) => void,
    }){
        this.element = createElement({tagName: "div", parentElement})
        this.datasource = datasource

        let p: HTMLElement;

        p = createElement({tagName:"p", parentElement: this.element})
        const brushing_enabled_checkbox = createInput({inputType: "checkbox", parentElement: p, onClick: () => {
            this.overlay.setBrushingEnabled(brushing_enabled_checkbox.checked)
        }})
        const enable_brushing_label = createElement({tagName: "label", innerHTML: "Enable Brushing", parentElement: p});
        (enable_brushing_label as HTMLLabelElement).htmlFor = brushing_enabled_checkbox.id = "brushing_enabled_checkbox"

        p = createElement({tagName: "p", parentElement: this.element})
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
                handleFinishedBrushStroke: onNewBrushStroke
            },
        })
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
