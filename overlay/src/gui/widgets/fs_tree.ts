import { createElement } from "../../util/misc";
import { CssClasses } from "../css_classes";

export class FsFileWidget{
    public readonly element: HTMLParagraphElement;
    public readonly parent: FsFolderWidget;

    constructor(params: {
        parent: FsFolderWidget, name: string, onDblClick?: () => void
    }){
        this.element = createElement({
            tagName: "p",
            parentElement: params.parent.element,
            innerText: "🗎 " + params.name,
            cssClasses: ["ItkFileWidget"],
            onClick: () => {
                this.selected = !this.selected
            },
            onDblClick: params.onDblClick,
        })
        this.parent = params.parent
    }

    public get selected(): boolean{
        return this.element.classList.contains(CssClasses.ItkSelected)
    }

    public set selected(value: boolean){
        this.element.classList.remove(CssClasses.ItkSelected)
        if(value){
            this.element.classList.add(CssClasses.ItkSelected)
        }
    }
}

export class FsFolderWidget{
    public readonly element: HTMLDetailsElement;
    public readonly summary: HTMLElement;
    private children = new Map<string, FsFileWidget | FsFolderWidget>()
    private expandWidget: HTMLSpanElement;
    public readonly parent: FsFolderWidget | undefined

    constructor(params: {parent: HTMLElement | FsFolderWidget, name: string, onOpen?: () => void}){
        this.parent = params.parent instanceof FsFolderWidget ? params.parent : undefined
        this.element = createElement({
            tagName: "details",
            parentElement: params.parent instanceof FsFolderWidget ? params.parent.element : params.parent,
            cssClasses: ["ItkFolderWidget"]
        })
        this.summary = createElement({
            tagName: "summary",
            parentElement: this.element,
        });
        this.expandWidget = createElement({
            tagName: "span",
            parentElement: this.summary,
            innerText: "▶",
            cssClasses: [CssClasses.ItkExpandFolderWidget],
            onClick: (ev): false => {
                ev.stopPropagation()
                ev.preventDefault()
                this.element.open = !this.element.open
                if(this.element.open){
                    this.expandWidget.innerText = "▼"
                    if(params.onOpen){
                        params.onOpen()
                    }
                }else{
                    this.expandWidget.innerText = "▶"
                }
                return false
            }
        })
        createElement({tagName: "span", parentElement: this.summary, innerText: "📁 " + params.name, onClick: (ev): false => {
            ev.stopPropagation()
            ev.preventDefault()
            this.selected = !this.selected
            return false
        }})
    }

    public get selected(): boolean{
        return this.summary.classList.contains(CssClasses.ItkSelected)
    }

    public set selected(value: boolean){
        this.summary.classList.remove(CssClasses.ItkSelected)
        if(value){
            this.summary.classList.add(CssClasses.ItkSelected)
        }
    }

    public addChildFile(name: string): FsFileWidget{
        const child = new FsFileWidget({parent: this, name})
        this.children.set(name, child)
        return child
    }

    public addChildFolder(name: string): FsFolderWidget{
        const child = new FsFolderWidget({parent: this, name})
        this.children.set(name, child)
        return child
    }
}
