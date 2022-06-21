import { createElement, createInput } from "../../util/misc";
import { Path } from "../../util/parsed_url";

export class PathInput{
    private inputElement: HTMLInputElement;
    constructor(params: {parentElement: HTMLElement, value?: Path, disabled?: boolean, required?: boolean}){
        let required = params.required === undefined ? true : params.required;
        this.inputElement = createInput({inputType: "text", parentElement: params.parentElement, required})
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

    public set value(path: Path | undefined){
        if(path){
            this.inputElement.value = path.toString()
        }else{
            this.inputElement.value = ""
        }
    }

    public static createLabeled(params: {label: string} & ConstructorParameters<typeof PathInput>[0]): PathInput{
        let span = createElement({tagName: "span", parentElement: params.parentElement})
        createElement({tagName: "label", parentElement: span, innerHTML: params.label})
        return new PathInput({...params, parentElement: span})
    }
}