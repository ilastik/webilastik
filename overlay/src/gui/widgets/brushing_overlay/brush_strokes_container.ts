import { vec3 } from "gl-matrix";
import { Applet } from "../../../client/applets/applet";
import { Color, DataSource, Session } from "../../../client/ilastik";
import { createElement, createInput, createInputParagraph, removeElement, vecToString } from "../../../util/misc";
import { ensureJsonArray, ensureJsonObject, ensureJsonString, JsonValue } from "../../../util/serialization";
import { CssClasses } from "../../css_classes";
import { ColorPicker } from "../color_picker";
import { ErrorPopupWidget, PopupWidget } from "../popup";
import { PopupSelect } from "../selector_widget";
import { BrushStroke } from "./brush_stroke";

export type resolution = vec3;

type State = {labels: Array<{name: string, color: Color, annotations: BrushStroke[]}>}


export class BrushingApplet extends Applet<State>{
    public readonly element: HTMLDivElement;
    private labelWidgets = new Map<string, LabelWidget>()
    private labelSelectorContainer: HTMLSpanElement;
    private labelSelector: PopupSelect<{name: string, color: Color}> | undefined

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
                            name: ensureJsonString(label_class["name"]),
                            color: Color.fromJsonValue(label_class["color"]),
                            annotations: ensureJsonArray(label_class["annotations"]).map(raw_annot => BrushStroke.fromJsonValue(params.gl, raw_annot))
                        }
                    })
                }
            },
            session: params.session,
            onNewState: (new_state) => this.onNewState(new_state)
        })

        this.element = createElement({tagName: "div", parentElement: params.parentElement});

        this.labelSelectorContainer = createElement({tagName: "span", parentElement: this.element})

        createInput({inputType: "button", value: "Create Label", parentElement: this.element, onClick: () => {
            let popup = new PopupWidget("Create Label")
            let labelForm = createElement({tagName: "form", parentElement: popup.element})
            let labelNameInput = createInputParagraph({inputType: "text", parentElement: labelForm, label_text: "Input Name: ", required: true})
            let colorPicker = new ColorPicker({label: "Label Color: ", parentElement: labelForm})

            let p = createElement({tagName: "p", parentElement: popup.element})
            createInputParagraph({inputType: "submit", value: "Ok", parentElement: labelForm})
            createInput({inputType: "button", parentElement: p, value: "Cancel", onClick: () => {
                popup.destroy()
            }})

            labelForm.addEventListener("submit", (ev) => { //use submit to leverage native form validation
                if(!labelNameInput.value){
                    new ErrorPopupWidget({message: `Missing input name`})
                }else if(this.labelWidgets.has(labelNameInput.value)){
                    new ErrorPopupWidget({message: `There is already a label with color ${colorPicker.value.hexCode}`})
                }else {
                    this.doRPC("create_label",  {label_name: labelNameInput.value, color: colorPicker.value})
                    popup.destroy()
                }
                //don't submit synchronously
                ev.preventDefault()
                return false
            })
        }})
    }

    public get currentLabelWidget(): LabelWidget | undefined{
        let label = this.labelSelector?.value;
        if(label === undefined){
            return undefined
        }
        return this.labelWidgets.get(label.name)
    }

    public get currentColor(): Color | undefined{
        return this.currentLabelWidget?.color
    }

    public getBrushStrokes(datasource: DataSource | undefined): Array<[Color, BrushStroke[]]>{
        let out: Array<[Color, BrushStroke[]]> = []
        for(let widget of this.labelWidgets.values()){
            out.push([widget.color, widget.getBrushStrokes(datasource)])
        }
        return out
    }

    public addBrushStroke(brushStroke: BrushStroke){
        let labelWidget = this.currentLabelWidget
        if(!labelWidget){
            new ErrorPopupWidget({message: `No label selected`}) //FIXME?
            return
        }
        labelWidget.addBrushStroke(brushStroke) // mask load time by modifying client state
        this.doRPC("add_annotation", {label_name: labelWidget.name, color: labelWidget.color, annotation: brushStroke})
    }

    private onNewState(newState: State){
        for(let labelWidget of this.labelWidgets.values()){
            labelWidget.destroy()
        }
        this.labelWidgets = new Map()

        let labelOptions = new Array<{name: string, color: Color}>();
        for(let {name, color, annotations} of newState.labels){
            labelOptions.push({name, color})
            let colorGroupWidget = new LabelWidget({
                name,
                parentElement: this.element,
                color,
                onLabelDeleteClicked: (labelName: string) => this.doRPC("remove_label", {label_name: labelName}),
                onBrushStrokeDeleteClicked: (_color, brushStroke) => this.doRPC(
                    "remove_annotation", {label_name: name, annotation: brushStroke}
                ),
                onColorChange: (newColor: Color) => {
                    this.doRPC("recolor_label", {label_name: name, new_color: newColor})
                    return true
                },
                onNameChange: (newName: string) => {
                    this.doRPC("rename_label", {old_name: name, new_name: newName})
                }
            })
            for(let brushStroke of annotations){
                colorGroupWidget.addBrushStroke(brushStroke)
            }
            this.labelWidgets.set(name, colorGroupWidget)
        }

        let currentLabel = this.labelSelector?.value;
        this.labelSelectorContainer.innerHTML = ""
        if(labelOptions.length == 0){
            this.labelSelector = undefined
            return
        }

        createElement({tagName: "label", parentElement: this.labelSelectorContainer, innerText: "Current label: "})
        this.labelSelector = new PopupSelect<{name: string, color: Color}>({
            popupTitle: "Select a label",
            parentElement: this.labelSelectorContainer,
            options: labelOptions,
            comparator: (label1, label2) => label1.name == label2.name,
            optionRenderer: (args) => {
                createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option.name + " "})
                createElement({tagName: "span", parentElement: args.parentElement, innerText: "🖌️", inlineCss: {
                    backgroundColor: args.option.color.hexCode,
                    padding: "2px",
                    border: "solid 1px black"
                }})
            },
        })
        if(currentLabel){
            if(this.labelWidgets.has(currentLabel.name)){
                this.labelSelector.value = currentLabel
                return
            }
            for(let labelWidget of this.labelWidgets.values()){
                if(labelWidget.color.equals(currentLabel.color)){
                    this.labelSelector.value = {name: labelWidget.name, color: labelWidget.color}
                    return
                }
            };
        }
    }

    public destroy(){
        for(let labelWidget of this.labelWidgets.values()){
            labelWidget.destroy()
        }
        removeElement(this.element)
    }
}

class LabelWidget{
    public readonly table: HTMLTableElement;

    private brushStrokeWidgets: BrushStrokeWidget[] = []
    private onBrushStrokeDeleteClicked: (color: Color, stroke: BrushStroke) => void;
    public readonly element: HTMLDivElement;
    private colorPicker: ColorPicker;
    private nameInput: HTMLInputElement;
    private readonly noAnnotationsMessage: HTMLParagraphElement;

    constructor({name, color, parentElement, onLabelDeleteClicked, onBrushStrokeDeleteClicked, onColorChange, onNameChange}: {
        name: string,
        color: Color,
        parentElement: HTMLElement,
        onLabelDeleteClicked: (labelName: string) => void,
        onBrushStrokeDeleteClicked: (color: Color, stroke: BrushStroke) => void,
        onColorChange: (newColor: Color) => void,
        onNameChange: (newName: string) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkLabelWidget"]});

        let labelControlsContainer = createElement({tagName: "p", parentElement: this.element})
        this.colorPicker = new ColorPicker({
            parentElement: labelControlsContainer, color, onChange: colors => onColorChange(colors.newColor)
        })
        this.nameInput = createInput({inputType: "text", parentElement: labelControlsContainer, value: name})
        this.nameInput.addEventListener("focusout", () => onNameChange(this.nameInput.value))
        createInput({inputType: "button", parentElement: labelControlsContainer, value: "Delete Annotations", onClick: () => onLabelDeleteClicked(this.name)})

        this.table = createElement({
            tagName: "table", parentElement: this.element, inlineCss: {
                border: `solid 2px ${color.hexCode}`,
                display: "none",
            },
        });
        this.noAnnotationsMessage = createElement({
            tagName: "p", parentElement: this.element, cssClasses: [CssClasses.InfoText], innerText: "No Annotations"
        })
        this.onBrushStrokeDeleteClicked = onBrushStrokeDeleteClicked
    }

    public get name(): string{
        return this.nameInput.value
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
        this.table.style.display = "table"
        this.noAnnotationsMessage.style.display = "none"
    }

    public clear(){
        this.brushStrokeWidgets.forEach(bsw => bsw.destroy())
        this.noAnnotationsMessage.style.display = "block"
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
        this.element = createElement({tagName: "tr", parentElement, cssClasses: ["ItkBrushStrokeWidget"], inlineCss: {
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
