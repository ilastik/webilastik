import { Color } from "../../client/ilastik";
import { createElement, createInput} from "../../util/misc";

export class ColorPicker{
    private picker: HTMLInputElement
    private color: Color;
    private onChange?: (new_color: Color) => void;

    constructor({parentElement, onChange, color=new Color({r: 0, g: 255, b:0}), label}:{
        parentElement: HTMLElement,
        onChange?: (color: Color) => void,
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
        this.picker.addEventListener("change", () => {this.setColor(Color.fromHexCode(this.picker.value))})
        this.setColor(color)
    }

    public getColor() : Color{
        return this.color
    }

    public setColor(color: Color){
        this.color = color
        this.picker.value = color.hexCode
        if(this.onChange){
            this.onChange(this.color)
        }
    }
}
