import { createElement, createInput, removeElement, uuidv4 } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { InputPopupWidget } from "./popup";

export class WidgetSelector<T extends {element: HTMLElement}>{
    public readonly element: HTMLElement;
    private selection: T;
    constructor({options, onSelection, parentElement, radio_name}: {
        options: Array<T>,
        onSelection: (selection: T) => void,
        parentElement: HTMLElement,
        radio_name: string
    }){
        if(options.length == 0){
            throw `Trying to create selector widget with empty options list`
        }
        this.selection = options[0]
        this.element = createElement({tagName: "form", parentElement, cssClasses: ["ItkSelector"]})
        let radio_buttons = new Array<HTMLInputElement>();
        let widget_containers = new Array<HTMLDivElement>();
        for(let opt of options){
            const container = createElement({
                tagName: "div",
                parentElement: this.element,
                inlineCss: {display: "grid", gridTemplateRows: "1", gridTemplateColumns: "2"},
            })

            let widget_container = createElement({
                tagName: "div", parentElement: container, inlineCss: {gridRow: "1", gridColumn: "2"}
            })
            widget_container.appendChild(opt.element)
            widget_containers.push(widget_container)

            radio_buttons.push(createInput({
                inputType: "radio",
                name: radio_name,
                parentElement: container,
                inlineCss: {gridRow: "1", gridColumn: "1"},
                onClick: () => {
                    widget_containers.forEach(wc => wc.classList.add("ItkGrayedOut"))
                    widget_container.classList.remove("ItkGrayedOut")
                    this.selection = opt
                    onSelection(opt)
                },
            }))
        }
        radio_buttons[0].click()
    }

    public getSelection() : T{
        return this.selection
    }
}

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
        this.optionRenderer = params.optionRenderer

        this.element = createElement({
            tagName: "span",
            parentElement: params.parentElement,
            cssClasses: [CssClasses.ItkButton],
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
        params.optionRenderer({option: params.options[0], parentElement: this.element})
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
    }

    public destroy(){
        removeElement(this.element)
    }
}