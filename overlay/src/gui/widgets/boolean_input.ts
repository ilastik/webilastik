import { createInput } from "../../util/misc";

export class BooleanInput{
    private readonly checkbox: HTMLInputElement;

    constructor(params: {
        parentElement: HTMLElement, value?: boolean, title?: string, onClick?: () => void, disabled?: boolean
    }){
        this.checkbox = createInput({
            inputType: "checkbox", parentElement: params.parentElement, title: params.title, onClick: params.onClick, disabled: params.disabled
        })
        this.checkbox.checked = params.value === undefined ? false : params.value
    }

    public get value(): boolean{
        return this.checkbox.checked
    }

    public set value(val: boolean){
        this.checkbox.checked = val
    }

    public get disabled(): boolean{
        return this.checkbox.disabled
    }

    public set disabled(value: boolean){
        this.checkbox.disabled = value
    }
}