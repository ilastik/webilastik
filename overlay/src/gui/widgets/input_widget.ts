import { ContainerWidget, Paragraph, Widget } from "./widget";
import { PopupWidget } from "./popup";
import { CssClasses } from "../css_classes";
import { InlineCss } from "../../util/misc";


export type InputType = "button" | "text" | "search" | "checkbox" | "submit" | "url" | "radio" | "number" | "color" | "range";

export type InputWidgetParams = {
    parentElement:HTMLElement | ContainerWidget<any> | undefined,
    title?: string,
    cssClasses?: Array<CssClasses>,
    inlineCss?: InlineCss,
    onClick?: (event: MouseEvent) => void,
    onDblClick?: (event: MouseEvent) => void,
    disabled?: boolean,
    required?: boolean,
}

export abstract class InputWidget<IT extends InputType> extends Widget<"input">{
    constructor(params: InputWidgetParams & {inputType: IT}){
        super({...params, tagName: "input"})
        this.element.type = params.inputType
        this.disabled = params.disabled === undefined ? false : params.disabled
        this.required = params.required === undefined ? false : params.required
    }

    public get disabled(): boolean{
        return this.element.disabled
    }

    public set disabled(val: boolean){
        this.element.disabled = val
        super.disabled = val
    }

    public get required(): boolean{
        return this.element.required
    }

    public set required(val: boolean){
        this.element.required = val
    }
}


export class Button<T extends "button" | "submit"> extends InputWidget<T>{
    constructor(params: InputWidgetParams & {inputType: T, text: string}){
        super(params)
        this.element.classList.add(CssClasses.ItkButton)
        this.text = params.text
    }

    public get text(): string{
        return this.element.value
    }

    public set text(val: string){
        this.element.value = val
    }
}


export class ButtonSpan extends Widget<"span">{
    constructor(params: InputWidgetParams & {content: Widget<"span">}){
        super({...params, tagName: "span"})
        this.element.classList.add(CssClasses.ItkButton)
        this.setContent(params.content)
    }

    public setContent(content: Widget<"span">){
        this.element.innerHTML = ""
        this.element.appendChild(content.element)
    }
}

export class Select<T> extends ButtonSpan{
    private _value: T
    private readonly renderer: (val: T) => Widget<"span">;
    private _options: T[];

    constructor(params: InputWidgetParams & {
        popupTitle: string,
        options: Array<T>,
        renderer: (val: T) => Widget<"span">,
        onChange?: (opt: T) => void,
        value?: T,
    }){
        super({
            ...params,
            cssClasses: [CssClasses.ItkSelectButton, ...(params.cssClasses || [])],
            content: params.renderer(params.options[0]),
            onClick: () => {
                const popup = PopupWidget.ClosablePopup({title: params.popupTitle});
                if(params.options.length == 0){
                    new Paragraph({parentElement: popup.contents, innerText: "No options available"})
                    return
                }
                for(const opt of params.options){
                    new Paragraph({
                        parentElement: popup.contents,
                        children: [params.renderer(opt)],
                        cssClasses: [CssClasses.ItkButton],
                        inlineCss: {display: "block"},
                        onClick: () => {
                            this.value = opt
                            if(params.onChange){
                                params.onChange(opt)
                            }
                            popup.destroy()
                        }
                    })
                }
            },
        })
        this.renderer = params.renderer
        this._value = params.value === undefined? params.options[0] : params.value
        this._options = params.options
        this.value = this._value
    }

    public get value(): T{
        return this._value
    }

    public set value(val: T){
        this._value = val
        this.setContent(this.renderer(val))
    }

    public get options(): T[]{
        return this._options.slice()
    }
}