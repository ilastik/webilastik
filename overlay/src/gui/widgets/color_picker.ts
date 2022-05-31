import { Color } from "../../client/ilastik";
import { createElement, createInput} from "../../util/misc";

export class ColorPicker{
    private picker: HTMLInputElement
    private color: Color;
    private onChange?: (colors: {oldColor: Color, newColor: Color}) => void;

    constructor({parentElement, onChange, color=new Color({r: 0, g: 255, b:0}), label}:{
        parentElement: HTMLElement,
        onChange?: (colors: {oldColor: Color, newColor: Color}) => void,
        color?: Color,
        label?: string
    }){
        this.color = color
        this.onChange = onChange
        if(label != undefined){
            parentElement = createElement({tagName: "p", parentElement})
            createElement({tagName: "label", innerHTML: label, parentElement})
        }
        this.picker = createInput({inputType: "color", parentElement})
        this.picker.addEventListener("change", () => {
            let oldColor = this.color
            this.color = Color.fromHexCode(this.picker.value)
            if(this.onChange){
                this.onChange({oldColor, newColor: this.color})
            }
        })
        this.setColor(color)
    }

    public getColor() : Color{
        return this.color
    }

    public get value(): Color{
        return this.color
    }

    public setColor(color: Color){
        this.color = color
        this.picker.value = color.hexCode
    }
}
