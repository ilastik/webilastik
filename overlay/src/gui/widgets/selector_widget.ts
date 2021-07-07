import { createElement, createInput, removeElement, uuidv4 } from "../../util/misc";

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
