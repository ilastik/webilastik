import { createElement, createInput } from "../../util/misc"

export class NumberInput{
    private input: HTMLInputElement

    constructor(params: {
        parentElement: HTMLElement,
        withParagraph: boolean,
        label?: string,
        value?: number,
        step?: number,
        min?: number,
        max?: number,
        disabled?: boolean,
    }){
        let parent: HTMLElement
        if(params.withParagraph){
            parent = createElement({tagName: "p", parentElement: params.parentElement})
        }else{
            parent = params.parentElement
        }

        let disabled = params.disabled === undefined ? false : true

        if(params.label){
            createElement({tagName: "label", parentElement: parent, innerHTML: params.label})
        }
        this.input = createInput({inputType: "number", parentElement: parent, disabled})
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
}