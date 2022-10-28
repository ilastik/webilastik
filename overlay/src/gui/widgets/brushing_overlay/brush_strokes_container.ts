import { vec3 } from "gl-matrix";
import { Applet } from "../../../client/applets/applet";
import { Color, DataSource, Session } from "../../../client/ilastik";
import * as schema from "../../../client/message_schema";
import { HashMap } from "../../../util/hashmap";
import { createElement, createInput, createInputParagraph, InlineCss, removeElement, vecToString } from "../../../util/misc";
import { JsonValue } from "../../../util/serialization";
import { CssClasses } from "../../css_classes";
import { ColorPicker } from "../color_picker";
import { ErrorPopupWidget, PopupWidget } from "../popup";
import { PopupSelect } from "../selector_widget";
import { BrushStroke } from "./brush_stroke";

export type resolution = vec3;

class Label{
    public readonly name: string
    public readonly color: Color
    public readonly annotations: BrushStroke[]

    public constructor(params: {
        name: string,
        color: Color,
        annotations: BrushStroke[],
    }){
        this.name = params.name
        this.color = params.color
        this.annotations = params.annotations
    }

    public static fromMessage(gl: WebGL2RenderingContext, message: schema.LabelMessage): Label{
        return new Label({
            annotations: message.annotations.map(a => BrushStroke.fromMessage(gl, a)),
            color: Color.fromMessage(message.color),
            name: message.name,
        })
    }
}

type State = {labels: Array<Label>}


export class BrushingApplet extends Applet<State>{
    public readonly element: HTMLDivElement;
    private labelWidgets = new Map<string, LabelWidget>()
    private labelSelectorContainer: HTMLSpanElement;
    private labelSelector: PopupSelect<{name: string, color: Color}> | undefined
    private onDataSourceClicked?: (datasource: DataSource) => void
    private onLabelSelected?: () => void;


    constructor(params: {
        session: Session,
        applet_name: string,
        parentElement: HTMLElement,
        onDataSourceClicked?: (datasource: DataSource) => void,
        onLabelSelected?: () => void;
        gl: WebGL2RenderingContext
    }){
        super({
            name: params.applet_name,
            deserializer: (value: JsonValue) => {
                const state = schema.BrushingAppletState.fromJsonValue(value)
                if(state instanceof Error){
                    throw `FIXME`
                }
                return {labels: state.labels.map(l => Label.fromMessage(params.gl, l))}
            },
            session: params.session,
            onNewState: (new_state) => this.onNewState(new_state)
        })

        this.onDataSourceClicked = params.onDataSourceClicked
        this.onLabelSelected = params.onLabelSelected
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
                    this.doRPC("create_label",  new schema.CreateLabelParams({
                        label_name: labelNameInput.value,
                        color: colorPicker.value.toMessage()
                    }))
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
        return Array.from(this.labelWidgets.values()).map(widget => [widget.color, widget.getBrushStrokes(datasource)])
    }

    public get labels(): Label[]{
        return Array.from(this.labelWidgets.values()).map(labelWidget => labelWidget.label)
    }

    public addBrushStroke(brushStroke: BrushStroke){
        let currentLabelWidget = this.currentLabelWidget
        if(currentLabelWidget === undefined){
            new ErrorPopupWidget({message: `No active label`})
            return
        }
        let newState: State = {labels: this.labels}
        for(let label of newState.labels){
            if(currentLabelWidget.name == label.name){
                label.annotations.push(brushStroke)
                break
            }
        }
        //Mask communication delay by updating GUI immediately
        this.onNewState(newState)
        this.doRPC("add_annotation", new schema.AddPixelAnnotationParams({
            label_name: currentLabelWidget.name, pixel_annotation: brushStroke.toMessage()
        }))
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
                brushStrokes: annotations,
                onLabelDeleteClicked: (labelName: string) => this.doRPC("remove_label", new schema.RemoveLabelParams({label_name: labelName})),
                onLabelSelected: (label: Label) => {
                    if(this.labelSelector){
                        this.labelSelector.value = label
                    }
                    if(this.onLabelSelected){
                        this.onLabelSelected()
                    }
                },
                onBrushStrokeDeleteClicked: (_color, brushStroke) => this.doRPC(
                    "remove_annotation", new schema.RemovePixelAnnotationParams({
                        label_name: name, pixel_annotation: brushStroke.toMessage()
                    })
                ),
                onColorChange: (newColor: Color) => {
                    this.doRPC("recolor_label", new schema.RecolorLabelParams({label_name: name, new_color: newColor.toMessage()}))
                    return true
                },
                onNameChange: (newName: string) => {
                    this.doRPC("rename_label", new schema.RenameLabelParams({old_name: name, new_name: newName}))
                },
                onDataSourceClicked: this.onDataSourceClicked,
            })
            this.labelWidgets.set(name, colorGroupWidget)
        }

        let previousLabel = this.labelSelector?.value;
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
            onChange: () => {
                if(this.onLabelSelected){
                    this.onLabelSelected()
                }
            }
        })
        if(!previousLabel){
            return
        }
        let currentLabelByName = this.labelWidgets.get(previousLabel.name)
        if(currentLabelByName){
            this.labelSelector.value = currentLabelByName
            return
        }
        for(let labelWidget of this.labelWidgets.values()){
            if(labelWidget.color.equals(previousLabel.color)){
                this.labelSelector.value = {name: labelWidget.name, color: labelWidget.color}
                return
            }
        };
    }

    public destroy(){
        for(let labelWidget of this.labelWidgets.values()){
            labelWidget.destroy()
        }
        removeElement(this.element)
    }
}

class LabelWidget{
    public readonly element: HTMLDivElement;
    private colorPicker: ColorPicker;
    private nameInput: HTMLInputElement;
    private brushStrokesTables: HashMap<DataSource, BrushStokeTable, string>;

    constructor(params: {
        name: string,
        color: Color,
        brushStrokes: BrushStroke[],
        parentElement: HTMLElement,
        onLabelDeleteClicked: (labelName: string) => void,
        onLabelSelected: (label: Label) => void,
        onBrushStrokeDeleteClicked: (color: Color, stroke: BrushStroke) => void,
        onColorChange: (newColor: Color) => void,
        onNameChange: (newName: string) => void,
        onDataSourceClicked?: (datasource: DataSource) => void,
    }){
        this.element = createElement({tagName: "div", parentElement: params.parentElement, cssClasses: ["ItkLabelWidget"]});

        let labelControlsContainer = createElement({tagName: "p", parentElement: this.element})
        this.colorPicker = new ColorPicker({
            parentElement: labelControlsContainer, color: params.color, onChange: colors => params.onColorChange(colors.newColor)
        })
        createInput({
            inputType: "button", parentElement: labelControlsContainer, value: "Select Label", onClick: () => params.onLabelSelected(this.label)
        })
        this.nameInput = createInput({inputType: "text", parentElement: labelControlsContainer, value: params.name})
        this.nameInput.addEventListener("focusout", () => params.onNameChange(this.nameInput.value))
        createInput({
            inputType: "button", parentElement: labelControlsContainer, value: "Delete Label", onClick: () => params.onLabelDeleteClicked(this.name)
        })

        let strokesPerDataSource = new HashMap<DataSource, BrushStroke[], string>();
        let brushStrokes = params.brushStrokes.slice()
        brushStrokes.sort((a, b) => a.annotated_data_source.getDisplayString().localeCompare(b.annotated_data_source.getDisplayString()))
        for(let stroke of brushStrokes){
            let strokeGroup = strokesPerDataSource.get(stroke.annotated_data_source)
            if(strokeGroup === undefined){
                strokeGroup = new Array<BrushStroke>();
                strokesPerDataSource.set(stroke.annotated_data_source, strokeGroup)
            }
            strokeGroup.push(stroke)
        }

        this.brushStrokesTables = new HashMap();

        if(strokesPerDataSource.size == 0){
            createElement({tagName: "p", parentElement: this.element, cssClasses: [CssClasses.InfoText], innerText: "No Annotations"})
            return
        }

        for(let [datasource, strokes] of strokesPerDataSource.entries()){
            this.brushStrokesTables.set(datasource, new BrushStokeTable({
                parentElement: this.element,
                caption: datasource.getDisplayString(),
                onBrushStrokeDeleteClicked: (stroke) => params.onBrushStrokeDeleteClicked(this.colorPicker.value, stroke),
                onCaptionCliked: () => {
                    if(params.onDataSourceClicked){
                        params.onDataSourceClicked(datasource)
                    }
                },
                strokes: strokes,
                inlineCss: {border: `solid 2px ${this.colorPicker.value.hexCode}`,}
            }))
        }
    }

    public get label(): Label{
        let brushStrokes = new Array<BrushStroke>();
        for(let strokes of this.brushStrokesTables.values().map(bst => bst.brushStrokes)){
            brushStrokes.push(...strokes)
        }
        return {
            annotations: brushStrokes,
            color: this.colorPicker.value,
            name: this.nameInput.value
        }
    }

    public get name(): string{
        return this.nameInput.value
    }

    public get color(): Color{
        return this.colorPicker.value
    }

    public getBrushStrokes(datasource: DataSource | undefined): Array<BrushStroke>{
        if(datasource === undefined){
            let out = new Array<BrushStroke>()
            for(let strokesTable of this.brushStrokesTables.values()){
                out.push(...strokesTable.brushStrokes)
            }
            return out
        }else{
            return this.brushStrokesTables.get(datasource)?.brushStrokes || []
        }
    }

    public destroy(){
        for(let tableWidget of this.brushStrokesTables.values()){
            tableWidget.destroy()
        }
        removeElement(this.element)
    }
}


class BrushStokeTable{
    public readonly element: HTMLTableElement;
    private strokeWidgets: BrushStrokeWidget[]

    constructor(params: {
        parentElement: HTMLElement,
        caption: string,
        strokes: BrushStroke[],
        onBrushStrokeDeleteClicked: (stroke: BrushStroke) => void,
        onCaptionCliked?: () => void,
        inlineCss?: InlineCss,
    }){
        this.element = createElement({
            tagName: "table", parentElement: params.parentElement, inlineCss: params.inlineCss, cssClasses: ["ItkBrushStrokeTable"]
        });
        createElement({
            tagName: "caption",
            parentElement: this.element,
            innerText: params.caption,
            cssClasses: [CssClasses.ItkBrushStrokeTableCaption],
            onClick: () => {
                if(params.onCaptionCliked){
                    params.onCaptionCliked()
                }
            },
            inlineCss: {
                textDecoration: params.onCaptionCliked ? "underline" : "none",
                cursor: params.onCaptionCliked ? "pointer" : "auto",
            }
        })
        this.strokeWidgets = params.strokes.map(stroke => new BrushStrokeWidget({
                brushStroke: stroke,
                parentElement: this.element,
                onLabelClicked: (_) => {}, //FIXME: snap viewer to coord
                onDeleteClicked: () => params.onBrushStrokeDeleteClicked(stroke)
        }))
    }

    public get brushStrokes(): BrushStroke[]{
        return this.strokeWidgets.map(widget => widget.brushStroke)
    }

    public destroy(){
        for(let strokeWiget of this.strokeWidgets){
            strokeWiget.destroy()
        }
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
