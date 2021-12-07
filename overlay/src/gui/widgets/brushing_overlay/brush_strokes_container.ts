import { vec3 } from "gl-matrix";
import { Applet } from "../../../client/applets/applet";
import { createElement, createInput, removeElement, vec3ToRgb, vecToString } from "../../../util/misc";
import { ensureJsonArray, ensureJsonBoolean, ensureJsonObject } from "../../../util/serialization";
import { BrushStroke } from "./brush_stroke";

export type resolution = vec3;


export class BrushStrokesContainer extends Applet<{brushing_enabled: boolean, annotations: Array<BrushStroke>}>{
    public readonly element: HTMLTableElement;

    private brushStrokeWidgets: BrushStrokeWidget[] = [];
    private onBrushColorClicked: (color: vec3) => void;

    constructor({applet_name, gl, parentElement, socket, onBrushColorClicked}: {
        applet_name: string,
        gl: WebGL2RenderingContext,
        parentElement: HTMLElement,
        socket: WebSocket,
        onBrushColorClicked: (color: vec3) => void,
    }){
        super({
            name: applet_name,
            deserializer: (data) => {
                let data_obj = ensureJsonObject(data)
                let brushing_enabled = ensureJsonBoolean(data_obj["brushing_enabled"])
                let raw_annotations = ensureJsonArray(data_obj["annotations"]);
                return {
                    brushing_enabled,
                    annotations: raw_annotations.map(a => BrushStroke.fromJsonValue(gl, a))
                }
            },
            socket,
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = createElement({tagName: "table", parentElement, cssClasses: ["ItkBrushStrokesContainer"]}) as HTMLTableElement;
        this.onBrushColorClicked = onBrushColorClicked
    }

    public addBrushStroke(brushStroke: BrushStroke){
        this.doRPC("add_annotations", {annotations: [brushStroke]})
    }

    public removeBrushStroke(brushStroke: BrushStroke){
        this.doRPC("remove_annotations", {annotations: [brushStroke]})
    }

    public getBrushStrokes(): Array<BrushStroke>{
        return this.brushStrokeWidgets.map(bsw => bsw.brushStroke)
    }

    protected onNewState(state: {brushing_enabled: boolean, annotations: Array<BrushStroke>}){
        this.brushStrokeWidgets.forEach(bsw => bsw.destroy())
        this.brushStrokeWidgets = []
        for(let brushStroke of state.annotations){
            let brush_widget = new BrushStrokeWidget({
                brushStroke,
                parentElement: this.element,
                onColorClicked: this.onBrushColorClicked,
                onLabelClicked: (_) => {}, //FIXME: snap viewer to coord
                onDeleteClicked: (stroke) => this.removeBrushStroke(stroke)
            })
            this.brushStrokeWidgets.push(brush_widget)
        }
    }

    public destroy(){
        this.brushStrokeWidgets.forEach(bsw => bsw.destroy())
        removeElement(this.element)
    }
}

// class BrushStrokeScaleGroup{
//     public readonly element: HTMLTableElement;
//     constructor(parentElement: HTMLElement, scale: IDataSourceScale){
//         this.element = createElement({tagName: "table", parentElement}) as HTMLTableElement
//     }
// }

class BrushStrokeWidget{
    public readonly element: HTMLElement
    public readonly brushStroke: BrushStroke

    constructor({brushStroke, parentElement, onLabelClicked, onColorClicked, onDeleteClicked}:{
        brushStroke: BrushStroke,
        parentElement: HTMLTableElement,
        onLabelClicked : (stroke: BrushStroke) => void,
        onColorClicked : (color: vec3) => void,
        onDeleteClicked : (stroke: BrushStroke) => void,
    }){
        this.brushStroke = brushStroke
        this.element = createElement({tagName: "tr", parentElement, cssClasses: ["BrushStrokeWidget"], inlineCss: {
            listStyleType: "none",
        }})

        const color_container = createElement({tagName: "td", parentElement: this.element})
        createInput({
            inputType: "button",
            value: "🖌",
            parentElement: color_container,
            inlineCss: {
                backgroundColor: vec3ToRgb(brushStroke.color),
            },
            onClick: () => onColorClicked(brushStroke.color),
        })

        createElement({
            parentElement: this.element,
            tagName: "td",
            innerHTML: `at voxel ${vecToString(brushStroke.getVertRef(0), 0)}`,
            onClick: () => onLabelClicked(brushStroke),
            inlineCss: {
                cursor: "pointer"
            }
        })

        const close_button_cell = createElement({parentElement: this.element, tagName: "td"})
        createInput({
            inputType: "button",
            value: "✖",
            parentElement: close_button_cell,
            cssClasses: ["delete_brush_button"],
            onClick: () => onDeleteClicked(brushStroke),
        })
    }

    public destroy(){
        this.brushStroke.destroy()
        removeElement(this.element)
    }
}
