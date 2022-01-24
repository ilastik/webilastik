import { createElement, createInput } from "../../util/misc";
import { PopupWidget } from "./popup";

export class CollapsableWidget{
    public readonly element: HTMLElement;
    public readonly header: HTMLElement;
    public readonly help_button?: HTMLInputElement;
    public readonly collapse_button: HTMLInputElement;
    private _is_collapsed: boolean = false
    public constructor({display_name, parentElement, help}:{display_name: string, parentElement: HTMLElement, help?: string[]}){
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
        if(help !== undefined){
            this.help_button = createInput({
                inputType: "button",
                parentElement: this.header,
                value: "?",
                inlineCss: {float: "right"},
                onClick: () => {
                    PopupWidget.OkPopup({title: `Help: ${display_name}`, paragraphs: help})
                }
            })
        }
        this.set_collapsed(false)
    }

    public get is_collapsed(): boolean{
        return this._is_collapsed
    }

    public set_collapsed(collapse: boolean){
        this._is_collapsed = collapse
        this.collapse_button.value = collapse ? "□" : "-"
        this.collapse_button.title = collapse ? "Expand" : "Collapse"
        this.element.querySelectorAll("*").forEach(element => {
            if(!(element instanceof HTMLElement)){
                console.error("Found bad element in applet:")
                console.error(element)
                return
            }
            if(element != this.header && element != this.collapse_button && element != this.help_button){
                if(collapse){
                    element.classList.add("itk_hidden_element")
                }else{
                    element.classList.remove("itk_hidden_element")
                }
            }
        })
    }
}
