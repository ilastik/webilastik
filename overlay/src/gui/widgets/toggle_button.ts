import { InlineCss, createElement, applyInlineCss } from "../../util/misc";

export class ToggleButton{
    public readonly element: HTMLElement
    private readonly checkedCssOrClasses: InlineCss | string[]
    private readonly uncheckedCssOrClasses: InlineCss | string[]
    private checked: boolean
    private readonly onChange?: (new_value: boolean) => void;

    constructor({
        value,
        parentElement,
        onChange,
        checkedCssOrClasses={
            borderStyle: "inset",
            backgroundColor: "rgba(0,0,0, 0.1)",
            userSelect: "none",
        },
        uncheckedCssOrClasses={
            borderStyle: "outset",
            backgroundColor: "rgba(0,0,0, 0.0)",
            userSelect: "none",
        },
        checked=false,
    }:{
        value: string,
        parentElement: HTMLElement,
        onChange?: (checked: boolean) => void,
        checkedCssOrClasses?: InlineCss | string[],
        uncheckedCssOrClasses?: InlineCss | string[],
        checked?: boolean,
    }){
        this.onChange = onChange
        this.checkedCssOrClasses = checkedCssOrClasses
        this.uncheckedCssOrClasses = uncheckedCssOrClasses
        this.element = createElement({tagName: "span", parentElement, innerHTML: value, onClick: () => {
            this.setChecked(!this.checked);
        }})
        this.checked = this.setChecked(checked) //strictPropertyInitialization
    }

    public getChecked(): boolean{
        return this.checked
    }

    public setChecked(value: boolean): boolean{
        this.checked = value
        const styling = this.checked ? this.checkedCssOrClasses : this.uncheckedCssOrClasses
        if(styling instanceof Array){
            this.element.classList.add(...styling)
        }else{
            applyInlineCss(this.element, styling)
        }
        if(this.onChange){
            this.onChange(value)
        }
        return value
    }
}
