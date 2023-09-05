import { vec3 } from "gl-matrix";
import { Applet } from "../../../client/applets/applet";
import { Color, FsDataSource, Session } from "../../../client/ilastik";
import * as schema from "../../../client/dto";
import { HashMap } from "../../../util/hashmap";
import { vecToString } from "../../../util/misc";
import { JsonValue } from "../../../util/serialization";
import { CssClasses } from "../../css_classes";
import { ErrorPopupWidget, PopupWidget } from "../popup";
import { BrushStroke } from "./brush_stroke";
import { Paragraph, Span, Label as LabelElement, Div, ContainerWidget, Form } from "../widget";
import { Button, ButtonWidget, Select } from "../input_widget";
import { ColorPicker, TextInput } from "../value_input_widget";

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

    public static fromDto(gl: WebGL2RenderingContext, message: schema.LabelDto): Label{
        return new Label({
            annotations: message.annotations.map(a => BrushStroke.fromDto(gl, a)),
            color: Color.fromDto(message.color),
            name: message.name,
        })
    }
}

type State = {labels: Array<Label>}


export class BrushingApplet extends Applet<State>{
    public readonly element: Div;
    private labelWidgets = new Map<string, PixelLabelWidget>()
    private labelSelectorContainer: Span;
    private labelSelector: Select<{name: string, color: Color}> | undefined
    private onDataSourceClicked?: (datasource: FsDataSource) => void
    private onLabelSelected?: () => void;


    constructor(params: {
        session: Session,
        applet_name: string,
        parentElement: HTMLElement,
        onDataSourceClicked?: (datasource: FsDataSource) => void,
        onLabelSelected?: () => void;
        gl: WebGL2RenderingContext
    }){
        super({
            name: params.applet_name,
            deserializer: (value: JsonValue) => {
                const state = schema.BrushingAppletStateDto.fromJsonValue(value)
                if(state instanceof Error){
                    throw `FIXME`
                }
                return {labels: state.labels.map(l => Label.fromDto(params.gl, l))}
            },
            session: params.session,
            onNewState: (new_state) => this.onNewState(new_state)
        })

        this.onDataSourceClicked = params.onDataSourceClicked
        this.onLabelSelected = params.onLabelSelected
        this.element = new Div({parentElement: params.parentElement, children: [
            this.labelSelectorContainer = new Span({parentElement: undefined}),
        ]});


        new Button({inputType: "button", text: "✚ New Label", parentElement: this.element, onClick: () => {
            let popup = new PopupWidget("Create Label")
            let labelNameInput: TextInput;
            let colorPicker: ColorPicker;

            new Form({parentElement: popup.contents, children: [
                new Paragraph({parentElement: undefined, children: [
                    new LabelElement({parentElement: undefined, innerText: "Label Name: "}),
                    labelNameInput = new TextInput({parentElement: undefined, required: true}),
                ]}),
                new Paragraph({parentElement: undefined, children: [
                    new LabelElement({parentElement: undefined, innerText: "Label Color: "}),
                    colorPicker = new ColorPicker({parentElement: undefined, value: new Color({r: 255, g: 0, b:0})}),
                ]}),
                new Paragraph({parentElement: undefined, children: [
                    new ButtonWidget({buttonType: "submit", contents: "Ok", parentElement: undefined, onClick: () => {}}),
                    new ButtonWidget({buttonType: "button", contents: "Cancel", parentElement: undefined, onClick: (ev): false => {
                        ev.preventDefault()
                        ev.stopPropagation()
                        popup.destroy()
                        return false
                    }})
                ]}),
            ]}).preventSubmitWith(() => {
                if(!labelNameInput.value){
                    new ErrorPopupWidget({message: `Missing input name`})
                }else if(this.labelWidgets.has(labelNameInput.value)){
                    new ErrorPopupWidget({message: `There is already a label with color ${colorPicker.value.hexCode}`})
                }else {
                    this.doRPC("create_label",  new schema.CreateLabelParams({
                        label_name: labelNameInput.value,
                        color: colorPicker.value.toDto()
                    }))
                    popup.destroy()
                }
            })
        }})
    }

    public get currentLabelWidget(): PixelLabelWidget | undefined{
        let label = this.labelSelector?.value;
        if(label === undefined){
            return undefined
        }
        return this.labelWidgets.get(label.name)
    }

    public get currentColor(): Color | undefined{
        return this.currentLabelWidget?.color
    }

    public getBrushStrokes(datasource: FsDataSource | undefined): Array<[Color, BrushStroke[]]>{
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
            label_name: currentLabelWidget.name, pixel_annotation: brushStroke.toDto()
        }))
    }

    private onNewState(newState: State){
        for(let labelWidget of this.labelWidgets.values()){
            labelWidget.destroy()
        }
        this.labelWidgets = new Map()

        for(let {name, color, annotations} of newState.labels){
            let colorGroupWidget = new PixelLabelWidget({
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
                        label_name: name, pixel_annotation: brushStroke.toDto()
                    })
                ),
                onColorChange: (newColor: Color) => {
                    this.doRPC("recolor_label", new schema.RecolorLabelParams({label_name: name, new_color: newColor.toDto()}))
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
        this.labelSelectorContainer.clear()
        if(newState.labels.length == 0){
            this.labelSelector = undefined
            return
        }

        new LabelElement({parentElement: this.labelSelectorContainer, innerText: "Current label: "})
        this.labelSelector = new Select<{name: string, color: Color}>({
            popupTitle: "Select a label",
            parentElement: this.labelSelectorContainer,
            options: newState.labels,
            renderer: (val) => new Span({
                parentElement: undefined,
                children: [
                    new Span({parentElement: undefined, innerText: val.name + " "}),
                    new Span({parentElement: undefined, innerText: "🖌️", inlineCss: {
                        backgroundColor: val.color.hexCode,
                        padding: "2px",
                        border: "solid 1px black"
                    }}),
                ]
            }),
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
        this.element.destroy()
    }
}

class PixelLabelWidget{
    public readonly element: Div;
    private colorPicker: ColorPicker;
    private nameInput: TextInput;
    private brushStrokesTables: HashMap<FsDataSource, BrushStokeTable, string>;
    private originalName: string;

    constructor(params: {
        name: string,
        color: Color,
        brushStrokes: BrushStroke[],
        parentElement: ContainerWidget<any>,
        onLabelDeleteClicked: (labelName: string) => void,
        onLabelSelected: (label: Label) => void,
        onBrushStrokeDeleteClicked: (color: Color, stroke: BrushStroke) => void,
        onColorChange: (newColor: Color) => void,
        onNameChange: (newName: string) => void,
        onDataSourceClicked?: (datasource: FsDataSource) => void,
    }){
        this.originalName = params.name
        this.element = new Div({parentElement: params.parentElement, children: [
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                this.colorPicker = new ColorPicker({
                    parentElement: undefined, value: params.color, onChange: newColor => params.onColorChange(newColor)
                }),
                new Button({
                    inputType: "button", parentElement: undefined, text: "Select", onClick: () => params.onLabelSelected(this.label)
                }),
                this.nameInput = new TextInput({parentElement: undefined, value: params.name}),
                new Button({
                    inputType: "button",
                    parentElement: undefined,
                    text: "✖",
                    title: "Delete this label and all annotations within",
                    onClick: () => params.onLabelDeleteClicked(this.name),
                }),
            ]}),
        ]});

        this.nameInput.element.addEventListener("focusout", () => {
            if(!this.nameInput.value){
                this.nameInput.value = params.name
            }else{
                params.onNameChange(this.nameInput.value)
            }
        })

        let strokesPerDataSource = new HashMap<FsDataSource, BrushStroke[], string>();
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
            new Paragraph({parentElement: this.element, cssClasses: [CssClasses.InfoText], innerText: "No Annotations"})
            return
        }

        for(let [datasource, strokes] of strokesPerDataSource.entries()){
            this.brushStrokesTables.set(datasource, new BrushStokeTable({
                parentElement: this.element.element,
                datasource: datasource,
                onBrushStrokeDeleteClicked: (stroke) => params.onBrushStrokeDeleteClicked(this.colorPicker.value, stroke),
                onCaptionCliked: () => {
                    if(params.onDataSourceClicked){
                        params.onDataSourceClicked(datasource)
                    }
                },
                strokes: strokes,
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
            name: this.name,
        }
    }

    public get name(): string{
        return this.nameInput.value || this.originalName //FIXME: double check this
    }

    public get color(): Color{
        return this.colorPicker.value
    }

    public getBrushStrokes(datasource: FsDataSource | undefined): Array<BrushStroke>{
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
        this.element.destroy()
    }
}


class BrushStokeTable extends Div{
    private strokeWidgets: BrushStrokeWidget[]

    constructor(params: {
        parentElement: HTMLElement,
        datasource: FsDataSource,
        strokes: BrushStroke[],
        onBrushStrokeDeleteClicked: (stroke: BrushStroke) => void,
        onCaptionCliked: () => void,
    }){
        super({...params, children: [
            new Paragraph({
                parentElement: undefined,
                innerText: params.datasource.getDisplayString(),
                title: params.datasource.url.raw,
                cssClasses: [CssClasses.ItkBrushDatasourceLink],
                onClick: params.onCaptionCliked,
            })
        ]})
        this.strokeWidgets = params.strokes.map(stroke => new BrushStrokeWidget({
                brushStroke: stroke,
                parentElement: this,
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
        super.destroy()
    }
}

class BrushStrokeWidget extends Paragraph{
    public readonly brushStroke: BrushStroke

    constructor(params: {
        brushStroke: BrushStroke,
        parentElement: Div,
        onLabelClicked : (stroke: BrushStroke) => void,
        onDeleteClicked : (stroke: BrushStroke) => void,
    }){
        super({...params, cssClasses: [CssClasses.ItkBrushStrokeWidget], children: [
            new Span({
                parentElement: undefined,
                cssClasses: [CssClasses.ItkBrushStrokeCoords],
                innerText: `🖌️ at ${vecToString(params.brushStroke.getVertRef(0), 0)}`,
                onClick: () => params.onLabelClicked(params.brushStroke),
                inlineCss: {cursor: "pointer"}
            }),
            new Button({
                inputType: "button",
                text: "✖",
                title: "Delete this annotation",
                parentElement: undefined,
                onClick: () => {
                    params.onDeleteClicked(params.brushStroke)
                    this.destroy()
                },
            })
        ]})
        this.brushStroke = params.brushStroke
    }

    public destroy(){
        //some animation frame might still have ref to this brush stroke,
        //so we trust the GC to dealloc the GPU buffer
        // this.brushStroke.destroy()
        super.destroy()
    }
}
