import { createElement } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";
import { PopupWidget } from "./popup";
import { TitleBar } from "./title_bar";
import { Paragraph, Span, Widget } from "./widget";

export class CollapsableWidget{
    public readonly container: HTMLDetailsElement;
    public readonly element: HTMLDivElement;
    public readonly summary: TitleBar<"summary">;
    public readonly extraInfoSpan: Span
    public readonly helpButton?: Button<"button">;
    public constructor({display_name, parentElement, help, open}:{
        display_name: string, parentElement: HTMLElement, help?: Array<string | Widget<any>>, open?: boolean
    }){
        this.container = createElement({tagName: "details", parentElement, cssClasses: ["ItkCollapsableApplet"]})
        const widgetsRight: Array<Widget<any>> = [
            this.extraInfoSpan = new Span({parentElement: undefined, cssClasses: [CssClasses.ItkCollapsableAppletExtraInfoSpan]})
        ]
        if(help !== undefined){
            this.helpButton = new Button({
                text: "?",
                inputType: "button",
                parentElement: undefined,
                onClick: () => {
                    let popup = PopupWidget.ClosablePopup({title: `Help: ${display_name}`});
                    for(const helpWidget of help){
                        if(typeof helpWidget == "string"){
                            new Paragraph({parentElement: popup.contents, innerText: helpWidget})
                        }else{
                            popup.contents.appendChild(helpWidget)
                        }
                    }
                }
            })
            widgetsRight.push(this.helpButton)
        }
        this.summary = new TitleBar({
            tagName: "summary",
            parentElement: this.container,
            text: display_name,
            widgetsRight,
        });
        this.container.open = open === undefined ? false : open
        this.element = createElement({tagName: "div", parentElement: this.container, cssClasses: [CssClasses.ItkAppletContents]})
    }
}
