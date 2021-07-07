import { vec3 } from "gl-matrix";
import { createElement, createInput, hexColorToVec3, vec3ToHexColor } from "../../util/misc";

export class Vec3ColorPicker{
    private picker: HTMLInputElement
    private color: vec3 = vec3.create();
    private onChange?: (new_color: vec3) => void;

    constructor({parentElement, onChange, color=vec3.fromValues(0, 1, 0), label}:{
        parentElement: HTMLElement,
        onChange?: (color: vec3) => void,
        color?: vec3,
        label?: string
    }){
        this.color = vec3.clone(color)
        this.onChange = onChange
        if(label != undefined){
            parentElement = createElement({tagName: "p", parentElement})
            createElement({tagName: "label", innerHTML: label, parentElement})
        }
        this.picker = createInput({inputType: "color", parentElement})
        this.picker.addEventListener("change", () => {this.setColor(this.picker.value)})
        this.setColor(color)
    }

    public getColor() : vec3{
        return vec3.clone(this.color)
    }

    public setColor(value: string | vec3){
        if(typeof value == "string"){
            this.color =  hexColorToVec3(value)
            this.picker.value = value
        }else{
            this.color = vec3.clone(value)
            this.picker.value = vec3ToHexColor(value)
        }
        if(this.onChange){
            this.onChange(this.color)
        }
    }
}
