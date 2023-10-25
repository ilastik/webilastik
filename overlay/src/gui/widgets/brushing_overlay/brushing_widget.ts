z dsaxZimport { BrushStroke } from "../../.."
import { Color, Session } from "../../../client/ilastik"
import { createElement, removeElement } from "../../../util/misc"
import { CollapsableWidget } from "../collapsable_applet_gui"
import { BrushingOverlay } from "./brushing_overlay"
import { BrushelBoxRenderer } from "./brush_boxes_renderer"
import { BrushingApplet } from "./brush_strokes_container"
import { Viewer } from "../../../viewer/viewer"
import { PredictingWidget } from "../predicting_widget";
import { Vec3, Quat } from "../../../util/ooglmatrix"
import { Paragraph, Widget } from "../widget"
import { CssClasses } from "../../css_classes"


export class BrushingWidget{
    public readonly viewer: Viewer
    public readonly element: HTMLElement

    private animationRequestId: number = 0
    session: Session
    public overlay?: BrushingOverlay
    public stagingStroke: BrushStroke | undefined = undefined
    public readonly gl: WebGL2RenderingContext
    public readonly canvas: HTMLCanvasElement
    private brushingApplet: BrushingApplet
    private predictingWidget: PredictingWidget
    private brushStrokeRenderer: BrushelBoxRenderer
    private clearEventListeners: () => void
    private brushingEnabled: boolean = false

    render: () => void

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
        help: Array<string | Widget<any>>,
    }){
        this.session = session
        this.canvas = createElement({tagName: "canvas", parentElement: document.body, inlineCss: {display: "none"}})
        this.gl = this.canvas.getContext("webgl2", {depth: true, stencil: true})!
        this.brushStrokeRenderer = new BrushelBoxRenderer({gl: this.gl, highlightCrossSection: false, onlyCrossSection: true})

        this.element = new CollapsableWidget({display_name: "Training", parentElement, help}).element
        this.element.classList.add("ItkBrushingWidget")
        this.viewer = viewer

        this.predictingWidget = new PredictingWidget({session, viewer: this.viewer, parentElement: this.element})
        new Paragraph({parentElement: this.element, innerText: "Hold Alt to brush!", cssClasses: [CssClasses.InfoText]})
        this.brushingApplet = new BrushingApplet({
            parentElement: this.element,
            session,
            applet_name,
            gl: this.gl,
            onDataSourceClicked: async (rawData) => this.viewer.openLane({
                name: rawData.url.name, rawData, isVisible: true
            }),
        });

        (() => {
            const enableBrushingOnAltDown = (ev: KeyboardEvent) => {
                if(ev.code == "AltLeft" || ev.code == "AltRight"){
                    this.setBrushingEnabled(true)
                }
            };
            window.addEventListener("keydown", enableBrushingOnAltDown)

            const disableBrushingOnAltUp = (ev: KeyboardEvent) => {
                if(ev.code == "AltLeft" || ev.code == "AltRight"){
                    this.setBrushingEnabled(false)
                }
            }
            window.addEventListener("keyup", disableBrushingOnAltUp)

            const disableBrushingOnDocumentHidden = () => {
                this.setBrushingEnabled(false)
            }
            document.addEventListener("visibilitychange", disableBrushingOnDocumentHidden);
            window.addEventListener("blur", disableBrushingOnDocumentHidden);

            this.clearEventListeners = () => {
                window.removeEventListener("keydown", enableBrushingOnAltDown)
                window.removeEventListener("keyup", disableBrushingOnAltUp)
                document.removeEventListener("visibilitychange", disableBrushingOnDocumentHidden)
                window.removeEventListener("blur", disableBrushingOnDocumentHidden);
            }
        })();


        this.render = () => {
            this.animationRequestId = window.requestAnimationFrame(this.render)
            if(!this.overlay){
                return
            }
            let strokes = new Array<[Color, BrushStroke[]]>();
            if(this.stagingStroke && this.brushingApplet.currentColor){
                strokes.push([this.brushingApplet.currentColor, [this.stagingStroke]])
            }
            strokes = strokes.concat(this.brushingApplet.getBrushStrokes(this.overlay.datasource))
            this.overlay.render(strokes, this.brushStrokeRenderer)
        }
        this.render()

        viewer.addDataChangedHandler(this.handleViewerDataDisplayChange)
        viewer.addViewportsChangedHandler(this.handleViewerDataDisplayChange)
        this.handleViewerDataDisplayChange()
    }

    private setBrushingEnabled(enabled: boolean){
        this.brushingEnabled = enabled;
        this.overlay?.setBrushingEnabled(enabled)
    }

    private handleViewerDataDisplayChange = async () => {
        const lane = this.viewer.getActiveLaneWidget()
        if(lane === undefined){
            this.canvas.style.display = "none"
            this.overlay?.destroy()
            this.overlay = undefined
            return
        }
        this.canvas.style.display = "block"
        this.overlay?.destroy()
        this.overlay = new BrushingOverlay({
            datasource: lane.rawData,
            gl: this.gl,
            trackedElement: this.viewer.getTrackedElement(),
            viewport_drivers: this.viewer.getViewportDrivers(),
            brush_stroke_handler: {
                handleNewBrushStroke: (params: {start_position: Vec3<"voxel">, camera_orientation: Quat<"voxel">}) => {
                    this.stagingStroke = BrushStroke.create({
                        gl: this.gl,
                        start_postition_uvw: params.start_position.raw, //FIXME put scale somewhere
                        annotated_data_source: lane.rawData,
                        camera_orientation: params.camera_orientation.raw, //FIXME: realy data space? rename param in BrushStroke?
                    })
                    return this.stagingStroke
                },
                handleFinishedBrushStroke: (stagingStroke: BrushStroke) => {
                    this.stagingStroke = undefined
                    this.brushingApplet.addBrushStroke(stagingStroke)
                }
            },
        })
        this.overlay.setBrushingEnabled(this.brushingEnabled)
    }

    public destroy(){
        this.clearEventListeners()
        window.cancelAnimationFrame(this.animationRequestId)
        this.overlay?.destroy()
        removeElement(this.gl.canvas as HTMLElement) //FIXME?
        removeElement(this.element)

        this.predictingWidget.destroy()
        this.brushingApplet.destroy()
        removeElement(this.element)

        this.viewer.removeDataChangedHandler(this.handleViewerDataDisplayChange)
        this.viewer.removeViewportsChangedHandler(this.handleViewerDataDisplayChange)

        //FIXME: remove event from viewer
    }
}