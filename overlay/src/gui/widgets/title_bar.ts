import { CssClasses } from "../css_classes";
import { ContainerWidget, Span, Widget, WidgetParams } from "./widget";

export class TitleBar<T extends keyof HTMLElementTagNameMap> extends ContainerWidget<T>{
    constructor(params: WidgetParams & {
        tagName: T,
        text: string,
        widgetsLeft?: Array<Widget<any>>
        widgetsRight?: Array<Widget<any>>
    }){
        super({
            ...params,
            cssClasses: [CssClasses.ItkTitleBar, ...(params.cssClasses || [])],
        })
        for(const widget of params.widgetsLeft || []){
            this.appendChild(widget)
        }
        new Span({parentElement: this.element, innerText: params.text, cssClasses: [CssClasses.ItkTitleBarText]});
        for(const widget of params.widgetsRight || []){
            this.appendChild(widget)
        }
    }
}