import { createElement, createInput } from "../../util/misc"
import { CssClasses } from "../css_classes"

export class NumberInput{
    private input: HTMLInputElement

    constructor(params: {
        parentElement: HTMLElement,
        value?: number,
        step?: number,
        min?: number,
        max?: number,
        disabled?: boolean,
    }){
        let disabled = params.disabled === undefined ? false : true
        this.input = createInput({inputType: "number", parentElement: params.parentElement, disabled})
        if(params.value !== undefined){
            this.input.value = params.value.toString()
        }
        if(params.step !== undefined){
            this.input.step = params.step.toString()
        }
        if(params.min !== undefined){
            this.input.min = params.min.toString()
        }
        if(params.max !== undefined){
            this.input.max = params.max.toString()
        }
    }

    public get value(): number | undefined{
        let parsed = parseFloat(this.input.value)
        if(isNaN(parsed)){
            return undefined
        }
        return parsed
    }

    public set value(value: number | undefined){
        if(value === undefined){
            this.input.value = ""
            return
        }
        this.input.value = value.toString()
    }

    public static createLabeled(params: {parentElement: HTMLElement, label: string, disabled: boolean}): NumberInput{
        let span = createElement({tagName: "span", parentElement: params.parentElement})
        createElement({tagName: "label", parentElement: span, innerHTML: " x: "})
        return new NumberInput({parentElement: span, disabled: params.disabled})
    }
}