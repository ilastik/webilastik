import { createElement, createInput } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";

export class UrlInput{
    public readonly input: HTMLInputElement;

    constructor(params: {parentElement: HTMLElement, disabled?: boolean}){
        let disabled = params.disabled === undefined ? false : params.disabled
        this.input = createInput({inputType: "url", parentElement: params.parentElement, disabled})
        this.input.addEventListener("keyup", () => this.validateInput())
        this.input.addEventListener("focusout", () => this.validateInput())

    }

    private validateInput = () => {
        this.input.classList.remove(CssClasses.ItkInvalidTextInput)
        if(this.input.value.trim() !== "" && this.value === undefined){
            this.input.classList.add(CssClasses.ItkInvalidTextInput)
        }
    }

    public get value(): Url | undefined{
        try{
            return Url.parse(this.input.value)
        }catch(e){
            return undefined
        }
    }

    public set value(value: Url | undefined){
        if(value === undefined){
            this.input.value = ""
            return
        }
        this.input.value = value.toString()
    }

    public static createLabeled(params: {label: string} & ConstructorParameters<typeof UrlInput>[0]): UrlInput{
        let span = createElement({tagName: "span", parentElement: params.parentElement})
        createElement({tagName: "label", parentElement: span, innerHTML: params.label})
        return new UrlInput({parentElement: span, disabled: params.disabled})
    }
}