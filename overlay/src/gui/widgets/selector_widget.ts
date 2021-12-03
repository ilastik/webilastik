import { createElement, createInput, removeElement, uuidv4 } from "../../util/misc";

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


export class SelectorWidget<T>{
    public readonly element: HTMLElement;
    private selection: T;
    constructor({options, optionRenderer, onSelection, parentElement}: {
        options: Array<T>,
        optionRenderer: (option: T, option_index: number) => string,
        onSelection: (selection: T) => void,
        parentElement: HTMLElement,
    }){
        if(options.length == 0){
            throw `Trying to create selector widget with empty options list`
        }
        this.selection = options[0]
        this.element = createElement({tagName: "form", parentElement, cssClasses: ["ItkSelector"]})
        options.forEach((opt, opt_index) => {
            const p = createElement({tagName: "p", parentElement: this.element, onClick: () => {
                this.selection = opt
            }})
            let radio = createInput({inputType: "radio", name: "option_selection", parentElement: p, onClick: () => {
                onSelection(opt)
            }})
            radio.id = uuidv4()
            const label =createElement({tagName: "label", parentElement: p, innerHTML: " " + optionRenderer(opt, opt_index)}) as HTMLLabelElement;
            label.htmlFor = radio.id
            if(opt_index == 0){
                label.click()
            }
        })
    }

    public getSelection() : T{
        return this.selection
    }
}

export class OneShotSelectorWidget<T> extends SelectorWidget<T>{
    constructor({options, optionRenderer, onSelection = (_) => {}, parentElement, onOk}: {
        options: Array<T>,
        optionRenderer: (option: T) => string,
        onSelection?: (selection: T) => void,
        parentElement: HTMLElement,
        onOk: (option: T) => void,
    }){
        super({options, optionRenderer, onSelection, parentElement})
        let p = createElement({tagName: "p", parentElement: this.element})
        createInput({inputType: "button", parentElement: p, value: "Ok", onClick: () => {
            removeElement(this.element)
            onOk(this.getSelection())
        }});
        createInput({inputType: "button", parentElement: p, value: "Cancel", onClick: () => {
            removeElement(this.element)
        }});
    }
}

