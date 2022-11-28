import { createElement, createInput } from "../../util/misc";
import { CssClasses } from "../css_classes";

export class BooleanInput{
    private readonly checkbox: HTMLInputElement;
    private readonly valueExplanations: {on: string, off: string}
    private readonly valueExplanationSpan: HTMLSpanElement;


    constructor(params: {
        parentElement: HTMLElement,
        value?: boolean,
        title?: string,
        onClick?: () => void, disabled?: boolean,
        valueExplanations?: {on: string, off: string}
    }){
        this.valueExplanations = params.valueExplanations || {on: "", off: ""}
        this.checkbox = createInput({
            inputType: "checkbox",
            parentElement: params.parentElement,
            title: params.title,
            disabled: params.disabled,
            cssClasses: [CssClasses.ItkCheckbox],
            onClick: () => {
                this.value = this.checkbox.checked
                if(params.onClick){
                    params.onClick()
                }
            },
        })
        this.valueExplanationSpan = createElement({tagName: "span", parentElement: params.parentElement, cssClasses: [CssClasses.InfoText]})
        this.value = params.value === undefined ? false : params.value
    }

    public get value(): boolean{
        return this.checkbox.checked
    }

    public set value(val: boolean){
        this.checkbox.checked = val
        this.valueExplanationSpan.innerText = this.valueExplanations[val ? "on" : "off"]
    }

    public get disabled(): boolean{
        return this.checkbox.disabled
    }

    public set disabled(value: boolean){
        this.checkbox.disabled = value
    }
}