import { createElement, createInput, createInputParagraph, removeElement, uuidv4 } from "../../util/misc";

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
        label: string,
        checked: boolean,
        name: string,
        onClick: (value: T) => void
    }){
        this._value = params.value
        this.radio = createInputParagraph({
            inputType: "radio",
            parentElement: params.parentElement,
            label_text: params.label,
            name: params.name,
            onClick: () => params.onClick(this._value)
        })
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

    public getValue(): T{
        return this._value
    }
}

export class SelectorWidget<T>{
    public readonly element: HTMLElement;
    protected selector_options: SelectorOption<T>[];
    constructor({options, optionRenderer, onSelection=() => {}, parentElement, initial_selection, comparator=(a: T, b: T) => a == b}: {
        options: Array<T>,
        optionRenderer: (option: T, option_index: number) => string,
        onSelection?: (selection: T, selection_index: number) => void,
        parentElement: HTMLElement,
        initial_selection?: T,
        comparator?: (a: T, b:T) => boolean,
    }){
        if(options.length == 0){
            throw `Trying to create selector widget with empty options list`
        }
        const define_checked = (opt: T): boolean => {
            if(initial_selection === undefined){
                return false
            }
            return comparator ? comparator(initial_selection, opt) : initial_selection == opt
        }
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSelector"]})
        const radio_group_name = uuidv4()
        this.selector_options = options.map((opt, opt_index) => new SelectorOption({
            parentElement: this.element,
            value: opt,
            label: optionRenderer(opt, opt_index),
            name: radio_group_name,
            checked: define_checked(opt),
            onClick: _ => onSelection(opt, opt_index)
        }))
    }

    public getSelection() : T | undefined{
        return this.selector_options.find(so => so.isChecked())!.getValue()
    }

    public setSelection({selection, comparator=(a, b) => {return a == b}}: {
        selection: T, comparator?: (a: T, b: T) => boolean
    }){
        this.selector_options.find(sel_opt => comparator(selection, sel_opt.getValue()))!.check(true)
    }
}

export class OneShotSelectorWidget<T> extends SelectorWidget<T>{
    constructor({options, optionRenderer, onSelection = (_) => {}, parentElement, onOk, onCancel = () => {}}: {
        options: Array<T>,
        optionRenderer: (option: T, option_index: number) => string,
        onSelection?: (selection: T) => void,
        parentElement: HTMLElement,
        onOk: (option: T) => void,
        onCancel?: () => void,
    }){
        super({options, optionRenderer, onSelection, parentElement})
        let p = createElement({tagName: "p", parentElement: this.element})
        createInput({inputType: "button", parentElement: p, value: "Ok", onClick: () => {
            const value = this.getSelection()
            if(value === undefined){
                return
            }
            removeElement(this.element)
            onOk(value)
        }});
        createInput({inputType: "button", parentElement: p, value: "Cancel", onClick: () => {
            removeElement(this.element)
            onCancel()
        }});
    }
}

