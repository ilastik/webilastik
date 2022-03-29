import { vec3 } from "gl-matrix";
import { createElement } from "../../util/misc";
import { NumberInput } from "./number_input";

export class Vec3Input{
    private xInput: NumberInput;
    private yInput: NumberInput;
    private zInput: NumberInput;

    constructor(params: {
        parentElement: HTMLElement, inlineFields: boolean, disabled?: boolean, value?: vec3
    }){
        let parent = createElement({tagName: "div", parentElement: params.parentElement})
        let disabled = params.disabled === undefined ? false : params.disabled

        this.xInput = new NumberInput({parentElement: parent, withParagraph: !params.inlineFields, label: "x: ", disabled})
        this.yInput = new NumberInput({parentElement: parent, withParagraph: !params.inlineFields, label: "y: ", disabled})
        this.zInput = new NumberInput({parentElement: parent, withParagraph: !params.inlineFields, label: "z: ", disabled})

        this.value = params.value
    }

    public set value(val: vec3 | undefined){
        this.xInput.value = val && val[0]
        this.yInput.value = val && val[1]
        this.zInput.value = val && val[2]
    }

    public get value(): vec3 | undefined{
        let x = this.xInput.value
        let y = this.yInput.value
        let z = this.zInput.value
        if(x === undefined || y === undefined || z === undefined){
            return undefined
        }
        return vec3.fromValues(x,y,z)
    }
}