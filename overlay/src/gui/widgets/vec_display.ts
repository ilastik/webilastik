import { CreateInputParams, createElement, createInput, vecToString } from "../../util/misc";

export class VecDisplayWidget{
    public readonly element: HTMLElement;
    private readonly inputElement : HTMLInputElement
    private _value?: Float32Array | Array<number>
    constructor(params: {
        label?: string,
        value?: Float32Array
    } & Omit<CreateInputParams, "value" | "inputType" | "disabled">){
        this.element = createElement({
            tagName: "p", ...params, cssClasses: (params.cssClasses || []).concat(["VecDisplayWidget"])
        })
        if(params.label){
            createElement({tagName: "label", innerHTML: params.label, parentElement: this.element, cssClasses: ["VecDisplayWidget_input"]})
        }
        this.inputElement = createInput({inputType: "text", parentElement: this.element, disabled: true})
        if(params.value){
            this.value = params.value
        }
    }

    public set value(val: Float32Array | Array<number> | undefined){
        this._value = val ? new Float32Array(val) : undefined;
        this.inputElement.value = val ? vecToString(val) : ""
    }

    public get value(): Float32Array | Array<number> | undefined {
        return this._value ? new Float32Array(this._value) : undefined
    }
}
