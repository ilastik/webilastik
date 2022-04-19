import { vec3 } from "gl-matrix";
import { createElement } from "../../util/misc";
import { NumberInput } from "./number_input";

export class Vec3Input{
    private xInput: NumberInput;
    private yInput: NumberInput;
    private zInput: NumberInput;

    constructor(params: {
        parentElement: HTMLElement,
        inlineFields: boolean,
        disabled?: boolean,
        value?: vec3,
        min?: {x?: number, y?: number, z?: number},
        max?: {x?: number, y?: number, z?: number},
        step?: {x?: number, y?: number, z?: number},
    }){
        let parent = createElement({tagName: "div", parentElement: params.parentElement})
        let disabled = params.disabled === undefined ? false : params.disabled

        this.xInput = NumberInput.createLabeled({
            parentElement: parent, label: " x: ", disabled, min: params.min?.x, max: params.max?.x, step: params.step?.x
        })
        this.yInput = NumberInput.createLabeled({
            parentElement: parent, label: " y: ", disabled, min: params.min?.y, max: params.max?.y, step: params.step?.y
        })
        this.zInput = NumberInput.createLabeled({
            parentElement: parent, label: " z: ", disabled, min: params.min?.z, max: params.max?.z, step: params.step?.z
        })

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

    public static createLabeledFieldset(params: {legend: string} & ConstructorParameters<typeof Vec3Input>[0]): Vec3Input{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new Vec3Input({...params, parentElement: fieldset})
    }
}
