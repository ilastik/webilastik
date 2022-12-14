import { createElement, createInput, removeElement, uuidv4 } from "../../util/misc";
import { InputPopupWidget } from "./popup";

export class SelectorOption<T>{
    private _value: T;
    public readonly radio: HTMLInputElement;
    constructor(params: {
        parentElement: HTMLElement,
        value: T,
        valueRenderer: (params: {value: T, parentElement: HTMLElement}) => void,
        checked: boolean,
        name: string,
        onClick: (value: T) => void
    }){
        this._value = params.value
        const p = createElement({tagName: "p", parentElement: params.parentElement})
        let label = createElement({tagName: "label", parentElement: p})
        this.radio = createInput({
            inputType: "radio",
            parentElement: label,
            name: params.name,
            onClick: () => params.onClick(this._value)
        })
        params.valueRenderer({value: params.value, parentElement: label})
        if(params.checked){
            this.radio.checked = true
        }
    }

    public check(checked: boolean){
        this.radio.checked = checked
    }

    public isChecked(): boolean{
        return this.radio.checked
    }

    public get value(): T{
        return this._value
    }
}

export class SelectorWidget<T>{
    public readonly element: HTMLElement;
    private _value: T
    private optionWidgets: SelectorOption<T>[];
    private comparator: (a: T, b: T) => boolean;

    constructor(params: {
        parentElement: HTMLElement,
        options: Array<T>,
        currentSelection?: T,
        optionRenderer: (params: {option: T, parentElement: HTMLElement}) => void,
        onSelection?: (selection: T) => void,
        comparator?: (a: T, b: T) => boolean,
    }){
        this.comparator = params.comparator || function (a,b): boolean {return a === b}
        this._value = params.currentSelection !== undefined ? params.currentSelection : params.options[0]
        this.element = createElement({tagName: "div", parentElement: params.parentElement, cssClasses: ["ItkSelector"]})
        const radio_group_name = uuidv4()
        this.optionWidgets = params.options.map(opt => new SelectorOption({
            parentElement: this.element,
            value: opt,
            valueRenderer: (args) => params.optionRenderer({option: opt, parentElement: args.parentElement}),
            name: radio_group_name,
            checked: opt == this._value,
            onClick: _ => {
                if(params.onSelection){
                    params.onSelection(opt)
                }
                this._value = opt
            }
        }))
    }

    public getSelection() : T{
        return this._value
    }

    public get value(): T{
        return this.getSelection()
    }

    public set value(val: T){
        for(let widget of this.optionWidgets){
            if(this.comparator(widget.value, val)){
                widget.check(true)
                this._value = val
                return
            }
        }
        throw `Could not find value: ${val}`
    }
}

export class PopupSelect<T>{
    private _value: T
    private _options: Array<T>
    private readonly element: HTMLSpanElement
    private optionRenderer: (params: {option: T, parentElement: HTMLElement}) => void

    constructor(params: {
        parentElement: HTMLElement,
        options: Array<T>,
        currentSelection?: T,
        optionRenderer: (params: {option: T, parentElement: HTMLElement}) => void,
        comparator?: (a: T, b: T) => boolean,

        popupTitle: string,
        onChange?: (newValue: T) => void,
        disabled?: boolean,
    }){
        this._value = params.options[0]
        this._options = params.options
        this.optionRenderer = params.optionRenderer

        this.element = createElement({
            tagName: "span",
            parentElement: params.parentElement,
            cssClasses: ["ItkPopupSelectTrigger"],
            onClick: () => {
                new InputPopupWidget<T>({
                    title: params.popupTitle,
                    inputWidgetFactory: (parentElement) => {
                        let selector = new SelectorWidget({...params, parentElement,});
                        selector.value = this._value;
                        return selector
                    },
                    onConfirm: (val: T) => {
                        this.value = val
                        if(params.onChange){
                            params.onChange(val)
                        }
                    },
                });
            }
        })
        this.value = params.options[0]
        let disabled = params.disabled === undefined ? false : params.disabled
        if(disabled){
            this.element.classList.add("ItkGrayedOut") // FIXME: double check this
        }
    }

    public get value(): T{
        return this._value
    }

    public set value(val: T){
        this._value = val
        this.element.innerHTML = ""
        this.optionRenderer({option: val, parentElement: this.element})
        createElement({tagName: "span", parentElement: this.element, innerText: "▼"})
    }

    public get options(): Array<T>{
        return this._options.slice()
    }

    public destroy(){
        removeElement(this.element)
    }
}