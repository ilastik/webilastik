import { quat, vec3 } from "gl-matrix"
import { BrushStroke } from "../../.."
import { Color, FsDataSource, PrecomputedChunksDataSource, Session } from "../../../client/ilastik"
import { createElement, removeElement } from "../../../util/misc"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { PopupSelect } from "../selector_widget"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushingApplet } from "./brush_strokes_container"
import { Viewer } from "../../../viewer/viewer"
import { PredictingWidget } from "../predicting_widget";
import { CssClasses } from "../../css_classes"
import { UnsupportedDatasetView, FailedView, PredictionsView, StrippedPrecomputedView } from "../../../viewer/view"
import { ErrorPopupWidget } from "../popup"
import { BooleanInput } from "../boolean_input"


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
    private brushingEnabledInfoSpan: HTMLSpanElement
    private brushStrokeRenderer: BrushelBoxRenderer

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
                title: "Enable to draw annotations by clicking and dragging. Disable to use the viewer's controls to navigate over the data.",
                onClick: () => {
                    this.setBrushingEnabled(this.brushingEnabledCheckbox.value)
                }
            })
            this.brushingEnabledInfoSpan = createElement({
                tagName: "span",
                parentElement: brushingEnabledParagraph,
                cssClasses: [CssClasses.InfoText],
                innerText: ""
            })

            this.brushingApplet = new BrushingApplet({
                parentElement: this.trainingWidget,
                session,
                applet_name,
                gl: this.gl,
                onDataSourceClicked: async (datasource) => this.viewer.openDataViewFromDataSource(datasource),
                onLabelSelected: () => {
                    this.setBrushingEnabled(true)
                }
            })

        viewer.addDataChangedHandler(() => this.handleViewerDataDisplayChange())
        this.setBrushingEnabled(false)
        this.handleViewerDataDisplayChange()
    }

    private setBrushingEnabled(brushingEnabled: boolean){
        this.brushingEnabledCheckbox.value = brushingEnabled
        this.overlay?.setBrushingEnabled(brushingEnabled)
        this.brushingEnabledInfoSpan.innerText = brushingEnabled ? "Navigating is disabled" : "Navigating is enabled"
    }

    public hideTrainingUi(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.trainingWidget.style.display = "none"
        this.canvas.style.display = "none"
        this.overlay?.destroy()
        this.overlay = undefined
    }

    public showTrainingUi(trainingDatasource: FsDataSource){
        this.trainingWidget.style.display = "block"
        this.canvas.style.display = "block"
        let overlay = this.overlay = new BrushingOverlay({
            gl: this.gl,
            trackedElement: this.viewer.getTrackedElement(),
            viewport_drivers: this.viewer.getViewportDrivers(),
            brush_stroke_handler: {
                handleNewBrushStroke: (params: {start_position_uvw: vec3, camera_orientation_uvw: quat}) => {
                    this.stagingStroke = BrushStroke.create({
                        gl: this.gl,
                        start_postition_uvw: params.start_position_uvw, //FIXME put scale somewhere
                        annotated_data_source: trainingDatasource,
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
        overlay.setBrushingEnabled(this.brushingEnabledCheckbox.value)

        window.cancelAnimationFrame(this.animationRequestId)
        const render = () => {
            let strokes = new Array<[Color, BrushStroke[]]>();
            if(this.stagingStroke){
                if(!this.brushingApplet.currentColor){
                    console.error("FIXME: no color selected but still brushing")
                }else{
                    strokes.push([this.brushingApplet.currentColor, [this.stagingStroke]])
                }
            }
            strokes = strokes.concat(this.brushingApplet.getBrushStrokes(trainingDatasource))
            overlay.render(strokes, this.brushStrokeRenderer) //FIXME? remove this optional override?
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

    private async handleViewerDataDisplayChange(){
        this.resetWidgets()

        const view = this.viewer.getActiveView()
        if(view === undefined){
            return this.showStatus("No data")
        }
        if(view instanceof Error){ //FIXME: remove this? or return error from viewer?
            return this.showStatus(`${view}`)
        }
        if(view instanceof UnsupportedDatasetView){
            return this.showStatus(`Unsupported data: ${view.url}`)
        }
        if(view instanceof FailedView){
            return this.showStatus(`Failed opening data: ${view.url}`)
        }
        if(view instanceof PredictionsView){
            return this.startTraining(view.raw_data)
        }
        if(view instanceof StrippedPrecomputedView){
            return this.startTraining(view.datasource)
        }
        if(view.datasources.length == 1){
            return this.startTraining(view.datasources[0])
        }

        this.showStatus(`Viewing multi-resolution datasource`)

        createElement({tagName: "label", innerHTML: "Select a voxel size to annotate on:", parentElement: this.resolutionSelectionContainer});
        new PopupSelect<FsDataSource>({
            popupTitle: "Select a voxel size to annotate on",
            parentElement: this.resolutionSelectionContainer,
            options: view.datasources,
            optionRenderer: (args) => {
                let datasource = args.option
                return createElement({
                    tagName: "span",
                    parentElement: args.parentElement,
                    innerText: datasource.resolutionString
                })
            },
            onChange: async (datasource) => {
                if(!(datasource instanceof PrecomputedChunksDataSource)){
                    new ErrorPopupWidget({message: "Can't handle this type of datasource yet"})
                    return
                }
                let stripped_view = new StrippedPrecomputedView({
                    datasource,
                    name: datasource.getDisplayString(),
                    session: this.session,
                })
                this.viewer.openDataView(stripped_view)
            },
        })
    }

    private startTraining(datasource: FsDataSource){
        this.resetWidgets()
        this.showTrainingUi(datasource)
        this.showStatus(`Now training on ${datasource.getDisplayString()}`)
    }

    public destroy(){
        window.cancelAnimationFrame(this.animationRequestId)
        this.overlay?.destroy()
        removeElement(this.gl.canvas)
        removeElement(this.element)

        this.predictingWidget.destroy()
        this.brushingApplet.destroy()
        removeElement(this.element)
        //FIXME: remove event from viewer
    }
}