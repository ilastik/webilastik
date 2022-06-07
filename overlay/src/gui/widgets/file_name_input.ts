import { createInput } from "../../util/misc"
import { CssClasses } from "../css_classes"
import { ErrorPopupWidget } from "./popup"

export class FileNameInput{
    private input: HTMLInputElement

    constructor(params: {
        parentElement: HTMLElement,
        value?: string,
        disabled?: boolean,
        required?: boolean,
    }){
        let disabled = params.disabled === undefined ? false : params.disabled
        let required = params.required === undefined ? true : params.required;
        this.input = createInput({
            inputType: "text", parentElement: params.parentElement, disabled, required, cssClasses: [CssClasses.ItkNumberInput]
        })
        if(params.value !== undefined){
            this.input.value = params.value
        }
        this.input.addEventListener("focusout", () => {
            let value = this.input.value
            if(!value){
                return
            }
            if(value.includes(" ") || value.includes("/")){ //FIXME: maybe slashes are ok
                new ErrorPopupWidget({
                    message: "A fle name can't contain spaces or slashes",
                    onClose: () => this.input.focus()
                })
            }
        })
    }

    public get value(): string | undefined{
        return this.input.value || undefined

    }

    public set value(value: string | undefined){
        this.input.value = value || ""
    }
}