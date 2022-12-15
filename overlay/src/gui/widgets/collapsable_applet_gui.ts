import { createElement } from "../../util/misc";
import { Button } from "./input_widget";
import { PopupWidget } from "./popup";
import { TitleBar } from "./title_bar";

export class CollapsableWidget{
    public readonly element: HTMLDetailsElement;
    public readonly summary: TitleBar<"summary">;
    public readonly help_button?: HTMLInputElement;
    public constructor({display_name, parentElement, help, open}:{
        display_name: string, parentElement: HTMLElement, help?: string[], open?: boolean
    }){
        this.element = createElement({tagName: "details", parentElement, cssClasses: ["ItkCollapsableApplet"]})
        this.summary = new TitleBar({
            tagName: "summary",
            parentElement: this.element,
            text: display_name,
            widgetsRight: help === undefined ? [] : [
                new Button({
                    text: "?",
                    inputType: "button",
                    parentElement: undefined,
                    onClick: () => {
                        PopupWidget.OkPopup({title: `Help: ${display_name}`, paragraphs: help})
                    }
                })
            ]
        });
        this.element.open = open === undefined ? false : open
    }
}
