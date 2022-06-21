import { Color } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";
import { ColorPicker } from "./color_picker";
import { InputPopupWidget } from "./popup";

// export class ColorListInput{
//     itemsContainer: HTMLDivElement;
//     constructor(params: {parentElement: HTMLElement}){
//         this.itemsContainer = createElement({tagName: "div", parentElement: params.parentElement})
//         this.addColorButton = createInput({inputType: "button", parentElement: params.parentElement, value: "New color", onClick: () => {

//         }})

//     }
// }

export class ColorItemWidget{
    public readonly element: HTMLSpanElement;
    public readonly colorDisplay: HTMLSpanElement;
    public readonly nameDisplay: HTMLSpanElement
    public color: Color;
    public readonly name: string | undefined;

    constructor(params: {
        color: Color,
        parentElement: HTMLElement,
        name?: string,
        onColorChanged: (color: Color) => void,
        onColorClicked: (color: Color) => void,
        onDeleteClicked: (color: Color) => void,
    }){
        this.name = params.name
        this.color = params.color
        this.element = createElement({tagName: "span", parentElement: params.parentElement})
        this.colorDisplay = createElement({
            tagName: "span",
            parentElement: this.element,
            innerText: "◯",
            onClick: () => {
                new InputPopupWidget<Color>({
                    title: "Select Color",
                    inputWidgetFactory: (parentElement) => new ColorPicker({parentElement, color: params.color}),
                    onConfirm: (color) => {
                        this.setColor(color)
                        params.onColorChanged(color)
                    },
                })
            }
        })
        this.nameDisplay = createElement({tagName: "span", parentElement: this.element, innerText: params.name || params.color.hexCode})
        createInput({
            inputType: "button",
            value: "✖",
            title: "Delete color",
            parentElement: this.element,
            cssClasses: ["delete_brush_button"],
            onClick: () => params.onDeleteClicked(this.color),
        })
        this.setColor(params.color)
    }

    private setColor(color: Color){
        this.color = color
        this.colorDisplay.style.backgroundColor = color.hexCode
        if(!this.name){
            this.nameDisplay.innerText = color.hexCode
        }
    }
}