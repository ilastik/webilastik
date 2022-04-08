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

    public get value(): T{
        return this._value
    }
}

export class DropdownSelect<T>{
    private _value: T
    private allOptions: T[]
    private readonly element: HTMLSelectElement
    private optionComparator: (a: T, b: T) => boolean
    private optionRenderer: (opt: T) => string;

    constructor(params: {
        parentElement: HTMLElement,
        firstOption: T,
        otherOptions: T[],
        optionRenderer: (opt: T) => string,
        optionComparator?: (a: T, b: T) => boolean,
        disabled?: boolean,
    }){
        this.optionComparator = params.optionComparator || ((a, b) => {return a == b})
        this.optionRenderer = params.optionRenderer
        this.element = createElement({tagName: "select", parentElement: params.parentElement})
        this.element.disabled = params.disabled === undefined ? false : params.disabled
        this._value = params.firstOption
        this.allOptions = [params.firstOption].concat(params.otherOptions)
        for(let optionValue of this.allOptions){
            createElement({tagName: "option", parentElement: this.element, innerText: params.optionRenderer(optionValue)})
        }
        this.element.addEventListener("change", () => {
        })
    }

    public get value(): T{
        return this._value
    }

    public set value(val: T){
        let index = this.allOptions.findIndex((opt) => this.optionComparator(opt, val))
        if(index < 0){
            throw Error(`Could not find option ${this.optionRenderer(val)}`)
        }
        this._value = val
        this.element.selectedIndex = index
    }
}

export class SelectorWidget<T>{
    public readonly element: HTMLElement;
    protected selector_options: SelectorOption<T>[];
    private readonly onSelection: (selection: T, selection_index: number) => void;
    private readonly comparator: (a: T, b:T) => boolean;
    private readonly options: T[];

    constructor(params: {
        parentElement: HTMLElement,
        options: Array<T>,
        optionRenderer: (option: T, option_index: number) => string,
        onSelection?: (selection: T, selection_index: number) => void,
        initial_selection?: T,
        comparator?: (a: T, b:T) => boolean,
    }){
        this.options = params.options
        this.onSelection = params.onSelection || (() => {})
        this.comparator = params.comparator || ((a, b) => a == b)
        if(params.options.length == 0){
            throw `Trying to create selector widget with empty options list`
        }
        this.element = createElement({tagName: "div", parentElement: params.parentElement, cssClasses: ["ItkSelector"]})
        const radio_group_name = uuidv4()
        this.selector_options = params.options.map((opt, opt_index) => new SelectorOption({
            parentElement: this.element,
            value: opt,
            label: params.optionRenderer(opt, opt_index),
            name: radio_group_name,
            checked: params.initial_selection !== undefined && this.comparator(opt, params.initial_selection),
            onClick: _ => this.onSelection(opt, opt_index)
        }))
    }

    public getSelection() : T | undefined{
        return this.selector_options.find(so => so.isChecked())?.value
    }

    public getOptions(): T[]{
        return this.options.slice()
    }

    public contains(value: T) : boolean{
        return this.options.find(item => this.comparator(item, value)) !== undefined
    }

    public setSelection(params: {
        selection: T,
        comparator?: (a: T, b: T) => boolean
    }){
        let comparator = params.comparator || this.comparator
        this.selector_options.find(sel_opt => {
            comparator(params.selection, sel_opt.value)
        })!.check(true)
    }
}

export class OneShotSelectorWidget<T> extends SelectorWidget<T>{
    constructor(params: {
        parentElement: HTMLElement,
        options: Array<T>,
        optionRenderer: (option: T, option_index: number) => string,
        onSelection?: (selection: T, selection_index: number) => void,
        initial_selection?: T,
        comparator?: (a: T, b:T) => boolean,
        onOk: (option: T) => void,
        onCancel?: () => void,
    }){
        super(params)
        let p = createElement({tagName: "p", parentElement: this.element})
        createInput({inputType: "button", parentElement: p, value: "Ok", onClick: () => {
            const value = this.getSelection()
            if(value === undefined){
                return
            }
            removeElement(this.element)
            params.onOk(value)
        }});

        let onCancel = params.onCancel || (() => {})
        createInput({inputType: "button", parentElement: p, value: "Cancel", onClick: () => {
            removeElement(this.element)
            onCancel()
        }});
    }
}

