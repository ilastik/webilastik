import { createElement, createInput } from "../../util/misc";

export class CollapsableWidget{
    public readonly element: HTMLElement;
    public readonly header: HTMLElement;
    public readonly collapse_button: HTMLInputElement;
    private _is_collapsed: boolean = false
    public constructor({display_name, parentElement}:{display_name: string, parentElement: HTMLElement}){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkCollapsableApplet"]})
        this.header = createElement({
            tagName: "h2", parentElement: this.element, innerHTML: display_name, cssClasses: ["ItkCollapsableApplet_header"]
        })
        this.collapse_button = createInput({
            inputType: "button",
            parentElement: this.header,
            value: "-",
            inlineCss: {float: "right"},
            onClick: () => this.set_collapsed(!this._is_collapsed)
        })
    }

    public get is_collapsed(): boolean{
        return this._is_collapsed
    }

    public set_collapsed(collapse: boolean){
        this._is_collapsed = collapse
        this.collapse_button.value = collapse ? "□" : "-"
        this.element.querySelectorAll("*").forEach(element => {
            if(!(element instanceof HTMLElement)){
                console.error("Found bad element in applet:")
                console.error(element)
                return
            }
            if(element != this.header && element != this.collapse_button){
                if(collapse){
                    element.classList.add("itk_hidden_element")
                }else{
                    element.classList.remove("itk_hidden_element")
                }
            }
        })
    }
}
