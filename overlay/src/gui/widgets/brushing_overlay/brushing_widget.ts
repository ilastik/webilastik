import { quat, vec3 } from "gl-matrix"
import { BrushStroke } from "../../.."
import { Color, FsDataSource, Session } from "../../../client/ilastik"
import { createElement, removeElement } from "../../../util/misc"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushingApplet } from "./brush_strokes_container"
import { Viewer } from "../../../viewer/viewer"
import { PredictingWidget } from "../predicting_widget";
import { BooleanInput } from "../value_input_widget"


export class BrushingWidget{
    public readonly viewer: Viewer
    public readonly element: HTMLElement
    private readonly status_display: HTMLElement
    private readonly resolutionSelectionContainer: HTMLElement
    private readonly trainingWidget: HTMLDivElement
    private readonly brushingEnabledCheckbox: BooleanInput

    private animationRequestId: number = 0
    session: Session
    public overlay?: BrushingOverlay
    public stagingStroke: BrushStroke | undefined = undefined
    public readonly gl: WebGL2RenderingContext
    public readonly canvas: HTMLCanvasElement
    private brushingApplet: BrushingApplet
    private predictingWidget: PredictingWidget
    private brushStrokeRenderer: BrushelBoxRenderer
    private readonly toggleBrushingKeyHandler: (e: KeyboardEvent) => void

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
        this.session = session
        this.canvas = createElement({tagName: "canvas", parentElement: document.body, inlineCss: {display: "none"}})
        this.gl = this.canvas.getContext("webgl2", {depth: true, stencil: true})!
        this.brushStrokeRenderer = new BrushelBoxRenderer({gl: this.gl, highlightCrossSection: false, onlyCrossSection: true})

        this.element = new CollapsableWidget({display_name: "Training", parentElement, help}).element
        this.element.classList.add("ItkBrushingWidget")
        this.viewer = viewer


        this.status_display = createElement({tagName:"p", parentElement: this.element, cssClasses: ["ItkBrushingWidget_status_display"]})

        this.resolutionSelectionContainer = createElement({tagName: "p", parentElement: this.element})

        this.trainingWidget = createElement({tagName: "div", parentElement: this.element})
            this.predictingWidget = new PredictingWidget({session, viewer: this.viewer, parentElement: this.trainingWidget})

            let brushingEnabledParagraph = createElement({tagName: "p", parentElement: this.trainingWidget})
            createElement({tagName: "label", parentElement: brushingEnabledParagraph, innerText: "Enable Brushing: "})
            this.brushingEnabledCheckbox = new BooleanInput({
                parentElement: brushingEnabledParagraph,
                title: "(B) Enable to draw annotations by clicking and dragging. Disable to use the viewer's controls to navigate over the data.",
                valueExplanations: {on: "Navigating is disabled", off: "Navigating is enabled"},
                disabled: true,
                onClick: () => {
                    this.setBrushingEnabled(this.brushingEnabledCheckbox.value)
                }
            })
            this.toggleBrushingKeyHandler = (e: KeyboardEvent) => {
                if(e.key == "b"){
                    this.setBrushingEnabled(!this.brushingEnabledCheckbox.value)
                }
            }
            window.addEventListener("keyup", this.toggleBrushingKeyHandler)

            this.brushingApplet = new BrushingApplet({
                parentElement: this.trainingWidget,
                session,
                applet_name,
                gl: this.gl,
                onDataSourceClicked: async (rawData) => this.viewer.openLane({
                    name: rawData.url.name, rawData, isVisible: true
                }),
                onLabelSelected: () => {
                    if(!this.brushingEnabledCheckbox.disabled){
                        this.setBrushingEnabled(true)
                    }
                }
            })

        viewer.addDataChangedHandler(() => this.handleViewerDataDisplayChange())
        viewer.addViewportsChangedHandler(() => this.handleViewerDataDisplayChange())
        // this.setBrushingEnabled(false)
        this.handleViewerDataDisplayChange()
    }

    private setBrushingEnabled(brushingEnabled: boolean){
        this.brushingEnabledCheckbox.value = brushingEnabled
        this.overlay?.setBrushingEnabled(brushingEnabled)
    }

    private setMode(
        mode: {name: "training", trainingDatasource: FsDataSource} |
              {name:"no data"}
    ){
        const lastBrushingEnabledValue = this.brushingEnabledCheckbox.value

        this.brushingEnabledCheckbox.disabled = true
        this.setBrushingEnabled(false)
        this.resolutionSelectionContainer.innerHTML = ""
        this.clearStatus()
        window.cancelAnimationFrame(this.animationRequestId)
        this.canvas.style.display = "none"
        this.overlay?.destroy()
        this.overlay = undefined

        if(mode.name == "no data"){
            //noop
        }else if(mode.name == "training"){
            this.brushingEnabledCheckbox.disabled = false
            this.canvas.style.display = "block"
            let overlay = this.overlay = new BrushingOverlay({
                datasource: mode.trainingDatasource,
                gl: this.gl,
                trackedElement: this.viewer.getTrackedElement(),
                viewport_drivers: this.viewer.getViewportDrivers(),
                brush_stroke_handler: {
                    handleNewBrushStroke: (params: {start_position_uvw: vec3, camera_orientation_uvw: quat}) => {
                        this.stagingStroke = BrushStroke.create({
                            gl: this.gl,
                            start_postition_uvw: params.start_position_uvw, //FIXME put scale somewhere
                            annotated_data_source: mode.trainingDatasource,
                            camera_orientation: params.camera_orientation_uvw, //FIXME: realy data space? rename param in BrushStroke?
                        })
                        return this.stagingStroke
                    },
                    handleFinishedBrushStroke: (stagingStroke: BrushStroke) => {
                        this.stagingStroke = undefined
                        this.brushingApplet.addBrushStroke(stagingStroke)
                    }
                },
            })
            this.setBrushingEnabled(lastBrushingEnabledValue)
            const render = () => {
                let strokes = new Array<[Color, BrushStroke[]]>();
                if(this.stagingStroke){
                    if(!this.brushingApplet.currentColor){
                        console.error("FIXME: no color selected but still brushing")
                    }else{
                        strokes.push([this.brushingApplet.currentColor, [this.stagingStroke]])
                    }
                }
                strokes = strokes.concat(this.brushingApplet.getBrushStrokes(mode.trainingDatasource))
                overlay.render(strokes, this.brushStrokeRenderer) //FIXME? remove this optional override?
                this.animationRequestId = window.requestAnimationFrame(render)
            }
            render()
        }
    }

    public showStatus(message: string){
        this.status_display.innerHTML = message
        this.status_display.style.display = "block"
    }

    public clearStatus(){
        this.status_display.innerHTML = ""
        this.status_display.style.display = "none"
    }

    private async handleViewerDataDisplayChange(){
        const lane = this.viewer.getActiveLaneWidget()
        if(lane === undefined){
            return this.setMode({name: "no data"})
        }
        return this.setMode({name: "training", trainingDatasource: lane.rawData})
    }

    public destroy(){
        window.removeEventListener("keyup", this.toggleBrushingKeyHandler)
        window.cancelAnimationFrame(this.animationRequestId)
        this.overlay?.destroy()
        removeElement(this.gl.canvas as HTMLElement) //FIXME?
        removeElement(this.element)

        this.predictingWidget.destroy()
        this.brushingApplet.destroy()
        removeElement(this.element)
        //FIXME: remove event from viewer
    }
}