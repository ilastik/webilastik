import { ContainerWidget, Li, Paragraph, Span, Ul, Widget, WidgetParams } from "./widget";
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

export class ButtonWidget extends Widget<"button">{
    constructor(params: Omit<WidgetParams, "onClick"> & {
        disabled?: boolean,
        buttonType?: "button" | "submit" | "reset",
        contents?: string | Widget<any>[],
        onClick: (ev: MouseEvent, button: ButtonWidget) => void,
    }){
        super({...params, tagName: "button", cssClasses: [CssClasses.ItkButton], onClick: (ev) => {
            params.onClick(ev, this)
        }});
        this.element.type = params.buttonType || "button";
        const disabled = params.disabled === undefined ? false : params.disabled;
        if(disabled){
            this.element.disabled = true
            this.addCssClass(CssClasses.ItkDisabled)
        }
        if(typeof(params.contents) == 'string'){
            this.element.appendChild(new Span({parentElement: undefined, innerText: params.contents}).element)
        }else{
            (params.contents || []).forEach(child => this.element.appendChild(child.element))
        }
    }
}

export class ToggleButtonWidget<T> extends ButtonWidget{
    public readonly valueWhenDepressed: T;

    constructor(params: Omit<WidgetParams, "onClick"> & {
        buttonType?: "button" | "submit" | "reset",
        contents?: string | Widget<any>[],
        onClick: (ev: MouseEvent, button: ToggleButtonWidget<T>) => void,
        depressed?: boolean,
        valueWhenDepressed: T,
    }){
        super({...params, onClick: (ev) => {
            this.depressed = !this.depressed
            params.onClick(ev, this)
        }});
        this.valueWhenDepressed = params.valueWhenDepressed
        if(params.depressed){
            this.addCssClass(CssClasses.ItkButtonDepressed)
        }
    }
    public get depressed(): boolean{
        return this.hasCssClass(CssClasses.ItkButtonDepressed)
    }
    public set depressed(value: boolean){
        if(value){
            this.addCssClass(CssClasses.ItkButtonDepressed)
        }else{
            this.removeCssClass(CssClasses.ItkButtonDepressed)
        }
    }
    public get value(): T | undefined{
        return this.depressed ? this.valueWhenDepressed : undefined
    }
    public toggle(){
        this.depressed = !this.depressed
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
                    new Paragraph({parentElement: popup.contents, children: [
                        new ButtonWidget({
                            parentElement: popup.contents,
                            contents: [params.renderer(opt)],
                            inlineCss: {display: "block", width: "100%"},
                            onClick: () => {
                                this.value = opt
                                if(params.onChange){
                                    params.onChange(opt)
                                }
                                popup.destroy()
                            }
                        })
                    ]})

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

export class MultiSelect<T> extends Ul{
    private buttons: Array<ToggleButtonWidget<T>> = []

    constructor(params: {
        parentElement: HTMLElement | ContainerWidget<any> | undefined,
        options: Array<T>,
        renderer: (val: T) => Widget<any>,
        onChange?: (values: T[]) => void,
    }){
        super({parentElement: params.parentElement, inlineCss: {listStyleType: "none", paddingInlineStart: "5px"}})
        if(params.options.length == 0){
            this.addItem(new Li({parentElement: undefined, innerText: "No options available"}))
            return
        }
        for(const opt of params.options){
            let button = new ToggleButtonWidget<T>({
                parentElement: undefined,
                contents: [params.renderer(opt)],
                inlineCss: {display: "block", width: "100%"},
                valueWhenDepressed: opt,
                onClick: (ev: MouseEvent, clickedButton: ToggleButtonWidget<T>) => {
                    let preClickState = !clickedButton.depressed;
                    if(!ev.ctrlKey && !ev.shiftKey){
                        this.buttons.forEach(btn => {btn.depressed = false})
                        clickedButton.depressed = !preClickState
                    }else if(ev.ctrlKey && !ev.shiftKey){
                        clickedButton.depressed = !preClickState
                    }else if(!ev.ctrlKey && ev.shiftKey && !preClickState){
                        let cursor = this.buttons.findIndex(btn => btn == clickedButton)
                        let target = this.buttons.findIndex(sib => sib.depressed && sib != clickedButton)
                        target = target < 0 ? cursor : target
                        const increment = Math.sign(target - cursor) || 1;

                        for(; increment * (target - cursor) >= 0 ; cursor += increment){
                            this.buttons[cursor].depressed = true
                        }
                    }
                    if(params.onChange){
                        params.onChange(this.value)
                    }
                }
            })
            this.addItem(new Li({parentElement: undefined, children: [button]}))
            this.buttons.push(button)
        }
    }

    public get value(): T[]{
        return this.buttons.filter(btn => btn.depressed).map(btn => btn.valueWhenDepressed)
    }

    public get options(): T[]{
        return this.buttons.map(btn => btn.valueWhenDepressed)
    }
}