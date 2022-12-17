import { applyInlineCss, InlineCss } from "../../util/misc";
import { CssClasses } from "../css_classes";

export type WidgetParams = {
    parentElement:HTMLElement | ContainerWidget<any> | undefined,
    innerText?:string,
    title?: string,
    cssClasses?: Array<CssClasses>,
    inlineCss?: InlineCss,
    onClick?: (event: MouseEvent) => void,
    onDblClick?: (event: MouseEvent) => void,
    show?: boolean,
}

export abstract class Widget<T extends keyof HTMLElementTagNameMap>{
    public readonly element: HTMLElementTagNameMap[T];

    constructor(params: {tagName: T} & WidgetParams){
        this.element = document.createElement(params.tagName);
        if(params.parentElement !== undefined){
            const parent = params.parentElement instanceof Widget ? params.parentElement.element : params.parentElement;
            parent.appendChild(this.element)
        }
        if(params.innerText !== undefined){
            this.element.innerText = params.innerText
        }
        if(params.title){
            this.element.title = params.title
        }
        (params.cssClasses || []).forEach(klass => {
            this.element.classList.add(klass)
        })
        const onClick = params.onClick
        if(onClick){
            (this.element as HTMLElement).addEventListener('click', (ev) => onClick(ev))
        }
        const onDblClick = params.onDblClick
        if(onDblClick){
            (this.element as HTMLElement).addEventListener('dblclick', (ev) => onDblClick(ev))

        }
        if(params.show !== undefined){
            this.show(params.show)
        }
        if(params.inlineCss){
            applyInlineCss(this.element, params.inlineCss)
        }
    }

    public get disabled(): boolean{
        return this.element.classList.contains(CssClasses.ItkDisabled)
    }

    public set disabled(val: boolean){
        this.element.classList.remove(CssClasses.ItkDisabled)
        if(val){
            this.element.classList.add(CssClasses.ItkDisabled)
        }
    }

    public addEventListener(eventName: "click", handler: (ev: MouseEvent) => void): this{
        (this.element as HTMLElement).addEventListener(eventName, handler)
        return this
    }

    public destroy(){
        this.element.parentNode?.removeChild(this.element)
    }

    public show(show: boolean){
        this.element.style.display = show ? "" : "none"
    }

    public addCssClass(klass: CssClasses){
        this.element.classList.add(klass)
    }
    public removeCssClass(klass: CssClasses){
        this.element.classList.remove(klass)
    }
    public click(){
        this.element.click()
    }
}

export class Label extends Widget<"label">{
    constructor(params: WidgetParams){
        super({...params, tagName: "label"})
    }
}

export abstract class ContainerWidget<T extends keyof HTMLElementTagNameMap> extends Widget<T>{
    protected constructor(params: WidgetParams & {tagName: T, children?: Array<Widget<any>>}){
        super({...params, tagName: params.tagName});
        (params.children || []).forEach(child => this.element.appendChild(child.element))
    }
    public appendChild(child: Widget<any>){
        this.element.appendChild(child.element)
    }

    public clear(){
        this.element.innerHTML = ""
    }
}

export class Span extends ContainerWidget<"span">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "span"})
    }
}

export class Caption extends ContainerWidget<"caption">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "caption"})
    }
}

export class Div extends ContainerWidget<"div">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "div"})
    }
}

export class Details extends ContainerWidget<"details">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "details"})
    }
}

export class Summary extends ContainerWidget<"summary">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "summary"})
    }
}

export class Paragraph extends ContainerWidget<"p">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "p"})
    }
}

export class Table extends ContainerWidget<"table">{
    constructor(params: WidgetParams & {children?: Array<Widget<"tr" | "caption">>}){
        super({...params, tagName: "table"})
    }
}

export class TableRow extends ContainerWidget<"tr">{
    constructor(params: WidgetParams & {children?: Array<Widget<"td">>}){
        super({...params, tagName: "tr"})
    }
}

export class TableData extends ContainerWidget<"td">{
    constructor(params: WidgetParams & {children?: Array<Widget<any>>}){
        super({...params, tagName: "td"})
    }
}
