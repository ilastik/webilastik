import { vec3 } from "gl-matrix";
import { DataSource } from "../../../client/ilastik";
import { createElement, createInput, removeElement, vec3ToHexColor, vec3ToRgb, vecToString } from "../../../util/misc";
import { BrushStroke } from "./brush_stroke";

export type resolution = vec3;


export class BrushStrokesContainer{
    public readonly element: HTMLDivElement;
    public readonly table: HTMLTableElement;

    public readonly datasource: DataSource
    private brushStrokeWidgets: BrushStrokeWidget[] = [];
    private onBrushColorClicked: (color: vec3) => void;
    private onBrushRemoved: (stroke: BrushStroke) => void;

    constructor({datasource, parentElement, onBrushColorClicked, onBrushRemoved}: {
        datasource: DataSource,
        parentElement: HTMLElement,
        onBrushColorClicked: (color: vec3) => void,
        onBrushRemoved: (stroke: BrushStroke) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkBrushStrokesContainer"]});
        createElement({tagName: "label", parentElement: this.element, innerHTML: `Annotations on ${datasource.getDisplayString()}`});
        this.table = createElement({tagName: "table", parentElement: this.element, cssClasses: ["ItkBrushStrokesContainer"]});
        this.datasource = datasource
        this.onBrushColorClicked = onBrushColorClicked
        this.onBrushRemoved = onBrushRemoved
    }

    public getBrushStrokes(): Array<BrushStroke>{
        return this.brushStrokeWidgets.map(bsw => bsw.brushStroke)
    }

    public addBrushStroke(brushStroke: BrushStroke){
        let brush_widget = new BrushStrokeWidget({
            brushStroke,
            parentElement: this.table,
            onColorClicked: this.onBrushColorClicked,
            onLabelClicked: (_) => {}, //FIXME: snap viewer to coord
            onDeleteClicked: (stroke) => this.removeBrushStroke(stroke)
        })
        this.brushStrokeWidgets.push(brush_widget)
    }

    public removeBrushStroke(brushStroke: BrushStroke){
        this.brushStrokeWidgets = this.brushStrokeWidgets.filter( bsw => {
            if(bsw.brushStroke == brushStroke){
                bsw.destroy()
                return false
            }
            return true
        })
        this.onBrushRemoved(brushStroke)
    }

    public destroy(){
        this.brushStrokeWidgets.forEach(bsw => bsw.destroy())
        removeElement(this.element)
    }
}


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
            title: `Pick this color (${vec3ToHexColor(brushStroke.color)})`,
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
            title: "Delete this annotation",
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
