import { createElement, createInput } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { PopupWidget } from "./popup";

export class CollapsableWidget{
    public readonly element: HTMLDetailsElement;
    public readonly summary: HTMLElement;
    public readonly help_button?: HTMLInputElement;
    public constructor({display_name, parentElement, help, open}:{
        display_name: string, parentElement: HTMLElement, help?: string[], open?: boolean
    }){
        this.element = createElement({tagName: "details", parentElement, cssClasses: ["ItkCollapsableApplet"]})
        this.summary = createElement({
            tagName: "summary", parentElement: this.element, cssClasses: [CssClasses.ItkTitleBar]
        });
        createElement({tagName: "span", innerText: display_name, parentElement: this.summary})
        if(help !== undefined){
            this.help_button = createInput({
                inputType: "button",
                parentElement: this.summary,
                value: "?",
                onClick: () => {
                    PopupWidget.OkPopup({title: `Help: ${display_name}`, paragraphs: help})
                }
            })
        }
        this.element.open = open === undefined ? false : open
    }
}
