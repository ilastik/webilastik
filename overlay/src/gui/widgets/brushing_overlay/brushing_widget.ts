import { quat, vec3 } from "gl-matrix"
import { BrushStroke } from "../../.."
import { Color, DataSource, Session } from "../../../client/ilastik"
import { createElement, createInputParagraph, removeElement } from "../../../util/misc"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { OneShotSelectorWidget } from "../selector_widget"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushStrokesContainer } from "./brush_strokes_container"
import { Viewer } from "../../../viewer/viewer"
import { PredictionsView, RawDataView, TrainingView } from "../../../viewer/view"
import { Applet } from "../../../client/applets/applet"
import { ensureJsonArray, ensureJsonBoolean, ensureJsonObject, JsonValue } from "../../../util/serialization"
import { HashMap } from "../../../util/hashmap"
import { PredictingWidget } from "../predicting_widget";
import { ColorPicker } from "../color_picker"


type State = {brushing_enabled: boolean, annotations: Array<BrushStroke>}

export class BrushingWidget extends Applet<State>{
    public readonly viewer: Viewer
    public readonly element: HTMLElement
    private readonly status_display: HTMLElement
    private readonly resolutionSelectionContainer: HTMLElement
    private readonly trainingWidget: HTMLDivElement
    private readonly colorPicker: ColorPicker
    private readonly brushingEnabledCheckbox: HTMLInputElement
    private readonly brushDisplayContainer: HTMLParagraphElement

    private animationRequestId: number = 0
    session: Session
    public overlay?: BrushingOverlay
    public staging_brush_stroke: BrushStroke | undefined = undefined
    public readonly gl: WebGL2RenderingContext
    public readonly canvas: HTMLCanvasElement
    private brushStrokeContainers = new HashMap<DataSource, BrushStrokesContainer, string>({
        hash_function: (ds => ds.getDisplayString()) //FIXME
    });


    constructor({
        applet_name,
        session,
        parentElement,
        viewer,
        help,
    }: {
        applet_name: string,
        session: Session,
        parentElement: HTMLElement,
        viewer: Viewer,
        help: string[],
    }){
        super({
            name: applet_name,
            deserializer: (value: JsonValue) => {
                let data_obj = ensureJsonObject(value)
                let raw_annotations = ensureJsonArray(data_obj["annotations"]);
                return {
                    brushing_enabled: ensureJsonBoolean(data_obj["brushing_enabled"]),
                    annotations: raw_annotations.map(a => BrushStroke.fromJsonValue(this.gl, a))
                }
            },
            session,
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.session = session
        this.canvas = createElement({tagName: "canvas", parentElement: document.body, inlineCss: {display: "none"}})
        this.gl = this.canvas.getContext("webgl2", {depth: true, stencil: true})!

        this.element = new CollapsableWidget({display_name: "Training", parentElement, help}).element
        this.element.classList.add("ItkBrushingWidget")
        this.viewer = viewer


        this.status_display = createElement({tagName:"p", parentElement: this.element, cssClasses: ["ItkBrushingWidget_status_display"]})

        this.resolutionSelectionContainer = createElement({tagName: "p", parentElement: this.element})

        this.trainingWidget = createElement({tagName: "div", parentElement: this.element})
            new PredictingWidget({session, viewer: this.viewer, parentElement: this.trainingWidget})

            this.brushingEnabledCheckbox = createInputParagraph({
                parentElement: this.trainingWidget,
                label_text: "Enable Brushing: ",
                inputType: "checkbox",
                title: "Enable to draw annotations by clicking and dragging. Disable to use the viewer's controls to navigate over the data.",
                onClick: () => this.overlay?.setBrushingEnabled(this.brushingEnabledCheckbox.checked)
            })

            let p = createElement({tagName: "p", parentElement: this.trainingWidget})
                createElement({tagName: "label", innerHTML: "Brush Color: ", parentElement: p})
                this.colorPicker = new ColorPicker({parentElement: p})

            this.brushDisplayContainer = createElement({tagName: "p", parentElement: this.trainingWidget})

        viewer.onViewportsChanged(() => this.handleViewerDataDisplayChange())
        this.handleViewerDataDisplayChange()
    }

    public hideTrainingUi(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.trainingWidget.style.display = "none"
        this.canvas.style.display = "none"
        this.overlay?.destroy()
        this.overlay = undefined
    }

    public showTrainingUi({trainingDatasource, brushStrokesGetter}: {trainingDatasource: DataSource, brushStrokesGetter: () => Array<BrushStroke>}){
        this.trainingWidget.style.display = "block"
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
                    this.addBrushStroke(stroke)
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
            overlay.render(strokes, new BrushelBoxRenderer({gl: this.gl, highlightCrossSection: false, onlyCrossSection: true})) //FIXME? remove this optional override?
            this.animationRequestId = window.requestAnimationFrame(render)
        }
        render()
    }

    public showStatus(message: string){
        this.status_display.innerHTML = message
    }

    public clearStatus(){
        this.status_display.innerHTML = ""
    }

    private resetWidgets(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.hideTrainingUi()
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
            return this.showStatus("No data")
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
        this.showStatus(`Viewing multi-resolution datasource`)

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

    public addBrushStroke(brushStroke: BrushStroke){
        this.doAddBrushStroke(brushStroke)
        this.doRPC("add_annotations", {annotations: [brushStroke]})
    }

    private doAddBrushStroke(brushStroke: BrushStroke){
        let container = this.brushStrokeContainers.get(brushStroke.annotated_data_source)
        if(container === undefined){
            container = new BrushStrokesContainer({
                parentElement: this.brushDisplayContainer,
                datasource: brushStroke.annotated_data_source,
                onBrushColorClicked: (color: Color) => this.colorPicker.setColor(color),
                onBrushRemoved: (brushStroke: BrushStroke) => {
                    //mask loading time by updating local state
                    let container = this.brushStrokeContainers.get(brushStroke.annotated_data_source)
                    if(!container){
                        return
                    }
                    if(container.getBrushStrokes().length == 0){
                        this.brushStrokeContainers.delete(brushStroke.annotated_data_source)
                        container.destroy()
                    }
                    this.doRPC("remove_annotations", {annotations: [brushStroke]})
                }
            })
            this.brushStrokeContainers.set(brushStroke.annotated_data_source, container)
        }
        container.addBrushStroke(brushStroke) //mask loading time by updating local state
    }

    public removeBrushStroke(brushStroke: BrushStroke){
        //mask loading time by updating local state
        let container = this.brushStrokeContainers.get(brushStroke.annotated_data_source)
        if(!container){
            return
        }
        console.log(`Brush strokes before removing: ${container.getBrushStrokes().length}`)
        container.removeBrushStroke(brushStroke)
        console.log(`Brush strokes AFTER removing: ${container.getBrushStrokes().length}`)

        if(container.getBrushStrokes().length == 0){
            console.log(`REACHED 0 ANNOTAIONS!!!!!!!!!!!!!!!`)
            this.brushStrokeContainers.delete(brushStroke.annotated_data_source)
            container.destroy()
        }
        this.doRPC("remove_annotations", {annotations: [brushStroke]})
    }

    protected onNewState(newState: State){
        this.brushDisplayContainer.innerHTML = ""
        createElement({tagName: "label", innerHTML: "Brush Strokes:", parentElement: this.brushDisplayContainer})

        this.brushStrokeContainers.values().forEach(bsc => bsc.destroy())
        this.brushStrokeContainers = new HashMap({
            hash_function: (ds) => ds.getDisplayString()
        })

        for(let brushStroke of newState.annotations){
            this.doAddBrushStroke(brushStroke)
        }
    }

    private startTraining(datasource: DataSource){
        this.resetWidgets()
        this.showTrainingUi({
            trainingDatasource: datasource,
            brushStrokesGetter: () => {
                let container = this.brushStrokeContainers.get(datasource)
                if(container){
                    return container.getBrushStrokes()
                }
                return []
            }
        })
        this.showStatus(`Now training on ${datasource.getDisplayString()}`)
    }

    public destroy(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.overlay?.destroy()
        removeElement(this.gl.canvas)
        removeElement(this.element)

        this.brushStrokeContainers.values().forEach(bsc => bsc.destroy())
        removeElement(this.element)
        //FIXME: remove event from viewer
    }
}