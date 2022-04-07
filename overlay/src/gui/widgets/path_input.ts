import { createElement, createInput } from "../../util/misc";
import { Path } from "../../util/parsed_url";

export class PathInput{
    private inputElement: HTMLInputElement;
    constructor(params: {parentElement: HTMLElement, value?: Path, disabled?: boolean}){
        this.inputElement = createInput({inputType: "text", parentElement: params.parentElement})
        if(params.value){
            this.inputElement.value = params.value.raw
        }
    }

    public get value(): Path | undefined{
        let raw = this.inputElement.value
        if(!raw){
            return undefined
        }
        return Path.parse(raw) //FIXME: bad path?
    }

    public static createLabeled(params: {label: string} & ConstructorParameters<typeof PathInput>[0]): PathInput{
        let span = createElement({tagName: "span", parentElement: params.parentElement})
        createElement({tagName: "label", parentElement: span, innerHTML: params.label})
        return new PathInput({parentElement: span, disabled: params.disabled})
    }
}