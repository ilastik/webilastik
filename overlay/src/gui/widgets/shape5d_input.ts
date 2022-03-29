import { Shape5D } from "../../client/ilastik";
import { createElement } from "../../util/misc";
import { NumberInput } from "./number_input";

export class Shape5DInput{
    public readonly xInput: NumberInput;
    public readonly yInput: NumberInput;
    public readonly zInput: NumberInput;
    public readonly tInput: NumberInput;
    public readonly cInput: NumberInput;
    constructor(params: {
        parentElement: HTMLElement, inlineFields: boolean, label?: string, value?: Shape5D, disabled?: boolean
    }){
        let container: HTMLElement
        if(params.label){
            container = createElement({tagName: "fieldset", parentElement: params.parentElement})
            createElement({tagName: "legend", innerHTML: params.label, parentElement: container})
        }else{
            container = params.parentElement
        }

        let disabled = params.disabled === undefined ? false : params.disabled
        let withParagraph = !params.inlineFields

        this.xInput = new NumberInput({parentElement: container, withParagraph, label: "x: ", disabled})
        this.yInput = new NumberInput({parentElement: container, withParagraph, label: "y: ", disabled})
        this.zInput = new NumberInput({parentElement: container, withParagraph, label: "z: ", disabled})
        this.tInput = new NumberInput({parentElement: container, withParagraph, label: "t: ", disabled})
        this.cInput = new NumberInput({parentElement: container, withParagraph, label: "c: ", disabled})

        this.value = params.value
    }

    public set value(shape: Shape5D | undefined){
        this.xInput.value = shape && shape.x
        this.yInput.value = shape && shape.y
        this.zInput.value = shape && shape.z
        this.tInput.value = shape && shape.t
        this.cInput.value = shape && shape.c
    }

    public get value(): Shape5D | undefined{
        let x = this.xInput.value
        let y = this.yInput.value
        let z = this.zInput.value
        let t = this.tInput.value
        let c = this.cInput.value
        if(x === undefined || y === undefined || z === undefined || t === undefined || c === undefined){
            return undefined
        }
        return new Shape5D({x, y, z, t, c})
    }
}