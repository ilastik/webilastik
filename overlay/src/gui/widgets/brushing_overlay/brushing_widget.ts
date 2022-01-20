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
    public readonly viewer: Viewer
    public readonly element: HTMLElement
    public readonly status_display: HTMLElement

    public readonly brushStrokeContainer: BrushStrokesContainer
    private readonly resolutionSelectionContainer: HTMLElement
    private animationRequestId: number = 0
    private trainingWidget: TrainingWidget
    session: Session

    constructor({
        session,
        parentElement,
        viewer,
    }: {
        session: Session,
        parentElement: HTMLElement,
        viewer: Viewer,
    }){
        this.session = session
        this.element = new CollapsableWidget({display_name: "Training", parentElement}).element
        this.element.classList.add("ItkBrushingWidget")
        this.viewer = viewer

        this.status_display = createElement({tagName:"p", parentElement: this.element, cssClasses: ["ItkBrushingWidget_status_display"]})

        this.trainingWidget = new TrainingWidget({
            parentElement: this.element,
            onNewBrushStroke: stroke => this.brushStrokeContainer.addBrushStroke(stroke),
            viewer: this.viewer
        })

        this.resolutionSelectionContainer = createElement({tagName: "p", parentElement: this.element})

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Brush Strokes:", parentElement: p})
        this.brushStrokeContainer = new BrushStrokesContainer({
            session,
            parentElement: this.element,
            applet_name: "brushing_applet",
            gl: this.trainingWidget.gl,
            onBrushColorClicked: (color: vec3) => this.trainingWidget?.colorPicker.setColor(color)
        })

        viewer.onViewportsChanged(() => this.handleViewerDataDisplayChange())
        this.handleViewerDataDisplayChange()
    }

    public showStatus(message: string){
        this.status_display.innerHTML = message
    }

    public clearStatus(){
        this.status_display.innerHTML = ""
    }

    private resetWidgets(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.trainingWidget.hide()
        this.resolutionSelectionContainer.innerHTML = ""
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

        createElement({tagName: "label", innerHTML: "Select a voxel size to annotate on:", parentElement: this.resolutionSelectionContainer});
        new OneShotSelectorWidget<DataSource>({
            parentElement: this.resolutionSelectionContainer,
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
        this.trainingWidget.show({
            trainingDatasource: datasource,
            brushStrokesGetter: () => {
                return this.brushStrokeContainer.getBrushStrokes()
                    .filter(stroke => stroke.annotated_data_source.equals(datasource))
            }
        })
        this.showStatus(`Now training on ${datasource.getDisplayString()}`)
    }

    public destroy(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.trainingWidget?.destroy()
        this.brushStrokeContainer.destroy()
        removeElement(this.element)
    }
}


export class TrainingWidget{
    public readonly element: HTMLElement
    public overlay?: BrushingOverlay
    public staging_brush_stroke: BrushStroke | undefined = undefined
    public readonly rendererSelector: SelectorWidget<BrushRenderer>
    public readonly colorPicker: Vec3ColorPicker
    public readonly brushingEnabledCheckbox: HTMLInputElement
    public readonly viewer: Viewer
    public readonly gl: WebGL2RenderingContext
    public readonly canvas: HTMLCanvasElement
    public readonly onNewBrushStroke: (stroke: BrushStroke) => void
    private animationRequestId: number = 0

    constructor({parentElement, viewer, onNewBrushStroke}: {
        parentElement: HTMLElement,
        viewer: Viewer,
        onNewBrushStroke: (stroke: BrushStroke) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, inlineCss: {display: "none"}})
        this.canvas =  createElement({tagName: "canvas", parentElement: document.body, inlineCss: {display: "none"}})
        this.gl = this.canvas.getContext("webgl2", {depth: true, stencil: true})!
        this.viewer = viewer
        this.onNewBrushStroke = onNewBrushStroke

        this.brushingEnabledCheckbox = createInputParagraph({
            label_text: "Enable Brushing: ", inputType: "checkbox", parentElement: this.element, onClick: () => {
                this.overlay?.setBrushingEnabled(this.brushingEnabledCheckbox.checked)
            }
        })

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Brush Color: ", parentElement: p})
        this.colorPicker = new Vec3ColorPicker({parentElement: p})

        p = createElement({tagName: "p", parentElement: this.element, inlineCss: {
            display: (window as any).ilastik_debug ? "block" : "none"}
        })
        createElement({tagName: "label", innerHTML: "Rendering style: ", parentElement: p})
        const renderers = [
            new BrushelBoxRenderer({gl: this.gl, highlightCrossSection: false, onlyCrossSection: true}),
            new BrushelLinesRenderer(this.gl),
            new BrushelBoxRenderer({gl: this.gl, debugColors: false, highlightCrossSection: false, onlyCrossSection: false}),
            new BrushelBoxRenderer({gl: this.gl, debugColors: true, highlightCrossSection: true, onlyCrossSection: false}),
        ];
        this.rendererSelector = new SelectorWidget<BrushRenderer>({
            parentElement: p,
            options: renderers,
            optionRenderer: (_, index) => ["Boxes - Cross Section", "Lines", "Boxes", "Boxes (debug colors)"][index],
            onSelection: (_) => {},
            initial_selection: renderers[0],
        })
    }

    public hide(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.element.style.display = "none"
        this.canvas.style.display = "none"
        this.overlay?.destroy()
        this.overlay = undefined
    }

    public show({trainingDatasource, brushStrokesGetter}: {trainingDatasource: DataSource, brushStrokesGetter: () => Array<BrushStroke>}){
        this.element.style.display = "block"
        this.canvas.style.display = "block"
        let overlay = this.overlay = new BrushingOverlay({
            gl: this.gl,
            trackedElement: this.viewer.getTrackedElement(),
            viewport_drivers: this.viewer.getViewportDrivers(),
            brush_stroke_handler: {
                handleNewBrushStroke: (params: {start_position_uvw: vec3, camera_orientation_uvw: quat}) => {
                    this.staging_brush_stroke = BrushStroke.create({
                        gl: this.gl,
                        start_postition_uvw: params.start_position_uvw, //FIXME put scale somewhere
                        color: this.colorPicker.getColor(),
                        annotated_data_source: trainingDatasource,
                        camera_orientation: params.camera_orientation_uvw, //FIXME: realy data space? rename param in BrushStroke?
                    })
                    return this.staging_brush_stroke
                },
                handleFinishedBrushStroke: (stroke) => {
                    this.staging_brush_stroke = undefined
                    this.onNewBrushStroke(stroke)
                }
            },
        })
        overlay.setBrushingEnabled(this.brushingEnabledCheckbox.checked)

        window.cancelAnimationFrame(this.animationRequestId)
        const render = () => {
            let strokes = brushStrokesGetter();
            if(this.staging_brush_stroke){
                strokes.push(this.staging_brush_stroke)
            }
            overlay.render(strokes, this.rendererSelector.getSelection()!) //FIXME? remove this optional override?
            this.animationRequestId = window.requestAnimationFrame(render)
        }
        render()
    }

    public destroy(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.overlay?.destroy()
        removeElement(this.canvas)
        removeElement(this.element)
    }
}
