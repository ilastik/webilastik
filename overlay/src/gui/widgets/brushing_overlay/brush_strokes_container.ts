import { vec3 } from "gl-matrix";
import { Applet } from "../../../client/applets/applet";
import { Color, DataSource, Session } from "../../../client/ilastik";
import { HashMap } from "../../../util/hashmap";
import { createElement, createInput, removeElement, vecToString } from "../../../util/misc";
import { ensureJsonArray, ensureJsonObject, JsonValue } from "../../../util/serialization";
import { ColorPicker } from "../color_picker";
import { ErrorPopupWidget, PopupWidget } from "../popup";
import { DropdownSelect } from "../selector_widget";
import { BrushStroke } from "./brush_stroke";

export type resolution = vec3;

type State = {labels: Array<{color: Color, annotations: BrushStroke[]}>}


export class BrushingApplet extends Applet<State>{
    public readonly element: HTMLDivElement;
    private labelWidgets = new HashMap<Color, LabelWidget, number>()
    private labelSelectorContainer: HTMLDivElement;
    private colorSelector: DropdownSelect<Color> | undefined

    constructor(params: {
        session: Session,
        applet_name: string,
        parentElement: HTMLElement,
        gl: WebGL2RenderingContext
    }){
        super({
            name: params.applet_name,
            deserializer: (value: JsonValue) => {
                let data_obj = ensureJsonObject(value)
                return {
                    labels: ensureJsonArray(data_obj["labels"]).map(raw_label_class => {
                        let label_class = ensureJsonObject(raw_label_class)
                        return {
                            color: Color.fromJsonValue(label_class["color"]),
                            annotations: ensureJsonArray(label_class["annotations"]).map(raw_annot => BrushStroke.fromJsonValue(params.gl, raw_annot))
                        }
                    })
                }
            },
            session: params.session,
            onNewState: (new_state) => this.onNewState(new_state)
        })

        this.element = createElement({tagName: "div", parentElement: params.parentElement, cssClasses: ["ItkBrushStrokesContainer"]});

        createInput({inputType: "button", value: "Create Label", parentElement: this.element, onClick: () => {
            let popup = new PopupWidget("Create Label")

            let colorPicker = new ColorPicker({
                parentElement: popup.element,
                label: "Label Color: ",
            })

            let p = createElement({tagName: "p", parentElement: popup.element})
            createInput({inputType: "button", parentElement: p, value: "Ok", onClick: () => {
                if(this.labelWidgets.has(colorPicker.value)){
                    new ErrorPopupWidget({message: `There is already a label with color ${colorPicker.value.hexCode}`})
                    return
                }
                this.doRPC("create_label",  {color: colorPicker.value})
                popup.destroy()
            }})
            createInput({inputType: "button", parentElement: p, value: "Cancel", onClick: () => {
                popup.destroy()
            }})
        }})

        this.labelSelectorContainer = createElement({tagName: "div", parentElement: this.element})
    }

    public get currentColor(): Color | undefined{
        return this.colorSelector?.value
    }

    public getBrushStrokes(datasource: DataSource | undefined): Array<[Color, BrushStroke[]]>{
        return this.labelWidgets.values().map(widget => [widget.color, widget.getBrushStrokes(datasource)])
    }

    public addBrushStroke(brushStroke: BrushStroke){
        if(!this.colorSelector){
            new ErrorPopupWidget({message: `No label selected`}) //FIXME?
            return
        }
        this.labelWidgets.get(this.colorSelector.value)?.addBrushStroke(brushStroke)
        this.doRPC("add_annotation", {color: this.colorSelector.value, annotation: brushStroke})
    }

    private onNewState(newState: State){
        this.labelWidgets.values().forEach(bsw => bsw.destroy())
        this.labelWidgets = new HashMap()

        for(let {color, annotations} of newState.labels){
            let colorGroupWidget = new LabelWidget({
                parentElement: this.element,
                color,
                onBrushStrokeDeleteClicked: (color, brushStroke) => this.doRPC(
                    "remove_annotation", {color, annotation: brushStroke}
                ),
                onColorChange: (colors: {oldColor: Color, newColor: Color}) => {
                    if(this.labelWidgets.has(colors.newColor)){
                        new ErrorPopupWidget({message: `The color ${colors.newColor.hexCode} is already in use`})
                        return false
                    }
                    this.doRPC("recolor_label", {old_color: colors.oldColor, new_color: colors.newColor})
                    return true
                }
            })
            for(let brushStroke of annotations){
                colorGroupWidget.addBrushStroke(brushStroke)
            }
            this.labelWidgets.set(color, colorGroupWidget)
        }


        let currentColor = this.colorSelector?.value;
        let currentColorIndex = this.colorSelector?.selectedIndex

        this.labelSelectorContainer.innerHTML = ""
        let colors = newState.labels.map(label => label.color)
        if(colors.length == 0){
            this.colorSelector = undefined
            return
        }
        this.colorSelector = new DropdownSelect({
            parentElement: this.labelSelectorContainer,
            firstOption: colors[0],
            otherOptions: colors.slice(1),
            optionRenderer: (color) => ({text: color.hexCode, inlineCss: {color: color.hexCode}}),
            optionComparator: (color1, color2) => color1.equals(color2),
        })
        if(currentColor){
            if(this.labelWidgets.has(currentColor)){
                this.colorSelector.value = currentColor
            }else if (currentColorIndex != undefined && currentColorIndex < this.colorSelector.values.length){
                this.colorSelector.value = this.colorSelector.values[currentColorIndex]
            }
        }
    }

    public destroy(){
        this.labelWidgets.values().forEach(bsw => bsw.destroy())
        removeElement(this.element)
    }
}

class LabelWidget{
    public readonly table: HTMLTableElement;

    private brushStrokeWidgets: BrushStrokeWidget[] = []
    private onBrushStrokeDeleteClicked: (color: Color, stroke: BrushStroke) => void;
    public readonly element: HTMLDivElement;
    private colorPicker: ColorPicker;

    constructor({color, parentElement, onBrushStrokeDeleteClicked, onColorChange}: {
        color: Color,
        parentElement: HTMLElement,
        onBrushStrokeDeleteClicked: (color: Color, stroke: BrushStroke) => void,
        onColorChange: (colors: {oldColor: Color, newColor: Color}) => boolean,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkBrushStrokesContainer"]});
        this.colorPicker = new ColorPicker({
            parentElement: this.element, color, label: "Label Color: ", onChange: colors => {
                if(!onColorChange(colors)){
                    this.colorPicker.setColor(colors.oldColor)
                }
            }
        })

        this.table = createElement({
            tagName: "table", parentElement: this.element, cssClasses: ["ItkBrushStrokesContainer"], inlineCss: {
                border: `solid 2px ${color.hexCode}`,
            }
        });
        this.onBrushStrokeDeleteClicked = onBrushStrokeDeleteClicked
    }

    public get color(): Color{
        return this.colorPicker.value
    }

    public getBrushStrokes(datasource: DataSource | undefined): Array<BrushStroke>{
        let brushStrokes = this.brushStrokeWidgets.map(bsw => bsw.brushStroke)
        if(datasource){
            return brushStrokes.filter(bs => bs.annotated_data_source.equals(datasource))
        }else{
            return brushStrokes
        }
    }

    public addBrushStroke(brushStroke: BrushStroke){
        let brush_widget = new BrushStrokeWidget({
            brushStroke,
            parentElement: this.table,
            onLabelClicked: (_) => {}, //FIXME: snap viewer to coord
            onDeleteClicked: () => this.onBrushStrokeDeleteClicked(this.colorPicker.value, brushStroke)
        })
        this.brushStrokeWidgets.push(brush_widget)
    }

    public clear(){
        this.brushStrokeWidgets.forEach(bsw => bsw.destroy())
    }

    public destroy(){
        this.clear()
        removeElement(this.element)
    }
}


class BrushStrokeWidget{
    public readonly element: HTMLElement
    public readonly brushStroke: BrushStroke

    constructor({brushStroke, parentElement, onLabelClicked, onDeleteClicked}:{
        brushStroke: BrushStroke,
        parentElement: HTMLTableElement,
        onLabelClicked : (stroke: BrushStroke) => void,
        onDeleteClicked : (stroke: BrushStroke) => void,
    }){
        this.brushStroke = brushStroke
        this.element = createElement({tagName: "tr", parentElement, cssClasses: ["BrushStrokeWidget"], inlineCss: {
            listStyleType: "none",
        }})

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
            onClick: () => {
                onDeleteClicked(brushStroke)
                this.destroy()
            },
        })
    }

    public destroy(){
        this.brushStroke.destroy()
        removeElement(this.element)
    }
}
