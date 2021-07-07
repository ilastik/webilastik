import { quat, vec3 } from "gl-matrix"
import { BrushStroke } from "../../.."
import { DataSource, Session } from "../../../client/ilastik"
import { createElement, createInput, removeElement } from "../../../util/misc"
import { PredictionsPrecomputedChunks, StrippedPrecomputedChunks } from "../../../datasource/precomputed_chunks"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { OneShotSelectorWidget, SelectorWidget } from "../selector_widget"
import { Vec3ColorPicker } from "../vec3_color_picker"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushelLinesRenderer } from "./brush_lines_renderer"
import { BrushRenderer } from "./brush_renderer"
import { BrushStrokesContainer } from "./brush_strokes_container"
import { IDataScale } from "../../../datasource/datasource"
import { Viewer } from "../../viewer"

export class BrushingWidget{
    public static training_view_name_prefix = "ilastik training: "

    public readonly gl: WebGL2RenderingContext
    public readonly viewer: Viewer
    public readonly element: HTMLElement
    public readonly canvas: HTMLCanvasElement
    public readonly status_display: HTMLElement

    private brushStrokeContainer: BrushStrokesContainer
    private readonly controlsContainer: HTMLElement
    private animationRequestId: number = 0
    private trainingWidget: TrainingWidget | undefined = undefined
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
        this.canvas =  createElement({tagName: "canvas", parentElement: document.body}) as HTMLCanvasElement;
        this.gl = this.canvas.getContext("webgl2", {depth: true, stencil: true})!
        this.viewer = viewer

        this.status_display = createElement({tagName:"p", parentElement: this.element, cssClasses: ["ItkBrushingWidget_status_display"]})
        this.controlsContainer = createElement({tagName: "p", parentElement: this.element})

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", innerHTML: "Brush Strokes:", parentElement: p})
        this.brushStrokeContainer = new BrushStrokesContainer({
            session,
            parentElement: this.element,
            applet_name: "brushing_applet",
            gl: this.gl,
            onBrushColorClicked: (color: vec3) => this.trainingWidget?.colorPicker.setColor(color)
        })

        this.showCanvas(false)
        if(viewer.onViewportsChanged){
            viewer.onViewportsChanged(() => this.handleViewerDataDisplayChange())
        }
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

    private async handleViewerDataDisplayChange(){
        this.resetWidgets()

        //FIXME: can racing mess this up?
        const data_view = await this.viewer.getActiveView()
        if(data_view === undefined){
            return
        }
        if(data_view instanceof Error){
            return this.showStatus(`${data_view}`)
        }
        if(data_view.datasource instanceof StrippedPrecomputedChunks){
            let originalDataProvider = data_view.datasource.original
            let scale = originalDataProvider.findScale(data_view.datasource.scales[0].resolution)!
            return this.startTraining(scale.toDataSource())
        }
        if(data_view.datasource instanceof PredictionsPrecomputedChunks){
            //FIXME: allow more annotations?
            return this.showStatus(`Showing predictions for ${data_view.datasource.raw_data_url.getSchemedHref("://")}`)
        }
        if(data_view.datasource.scales.length == 1){
            return this.startTraining(data_view.datasource.scales[0].toIlastikDataSource())
        }

        createElement({tagName: "label", innerHTML: "Select a voxel size to annotate on:", parentElement: this.controlsContainer});
        new OneShotSelectorWidget<IDataScale>({
            parentElement: this.controlsContainer,
            options: data_view.datasource.scales,
            optionRenderer: (scale) => scale.toDisplayString(),
            onOk: async (scale) => {
                const stripped_precomp_chunks = await scale.toStrippedMultiscaleDataSource(this.session) //FIXME: race condition?
                this.viewer.refreshView({
                    name: BrushingWidget.training_view_name_prefix + `${data_view.name} (${scale.toDisplayString()})`,
                    url: stripped_precomp_chunks.url.getSchemedHref("://"),
                    similar_url_hint: data_view.datasource.url.getSchemedHref("://"),
                })
            },
        })
    }

    private startTraining(datasource: DataSource){
        this.resetWidgets()
        this.showCanvas(true)

        const resolution = datasource.spatial_resolution
        this.trainingWidget = new TrainingWidget({
            gl: this.gl,
            parentElement: this.controlsContainer,
            onNewBrushStroke: stroke => this.brushStrokeContainer.addBrushStroke(stroke),
            datasource,
            viewer: this.viewer
        })
        this.showStatus(`Now training on ${datasource.url}(${resolution[0]} x ${resolution[1]} x ${resolution[2]} nm)`)
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
