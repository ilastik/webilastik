import { Shape5D } from "../../client/ilastik";
import { createElement } from "../../util/misc";
import { NumberInput } from "./number_input";

export class Shape5DInput{
    public readonly xInput: NumberInput;
    public readonly yInput: NumberInput;
    public readonly zInput: NumberInput;
    public readonly tInput: NumberInput;
    public readonly cInput: NumberInput;
    constructor(params: {parentElement: HTMLElement, value?: Shape5D, disabled?: boolean}){
        let disabled = params.disabled === undefined ? false : params.disabled

        this.xInput = NumberInput.createLabeled({parentElement: params.parentElement, disabled, label: " x :"})
        this.yInput = NumberInput.createLabeled({parentElement: params.parentElement, disabled, label: " y :"})
        this.zInput = NumberInput.createLabeled({parentElement: params.parentElement, disabled, label: " z :"})
        this.tInput = NumberInput.createLabeled({parentElement: params.parentElement, disabled, label: " t :"})
        this.cInput = NumberInput.createLabeled({parentElement: params.parentElement, disabled, label: " c :"})

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

    public static createLabeledFieldset(params: {legend: string} & ConstructorParameters<typeof Shape5DInput>[0]): Shape5DInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new Shape5DInput({...params, parentElement: fieldset})
    }
}