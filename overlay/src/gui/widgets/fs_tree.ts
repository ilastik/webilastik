import { removeElement } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { Details, Paragraph, Span, Summary } from "./widget";

export class FsFileWidget extends Paragraph{
    public readonly parent: FsFolderWidget;
    public readonly path: Path;

    constructor(params: {
        parent: FsFolderWidget, name: string, onDblClick?: () => void
    }){
        super({
            parentElement: params.parent.element,
            innerText: "🗎 " + params.name,
            cssClasses: [CssClasses.ItkFileWidget],
            onClick: (ev) => {
                this.parent.handleNodeClicked(this, ev)
            },
            onDblClick: params.onDblClick,

        })
        this.path = params.parent.path.joinPath(params.name)
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

    public getRoot(): FsFolderWidget{
        return this.parent.getRoot()
    }

    public getSiblings(): Array<FsFileWidget | FsFolderWidget>{
        return this.parent.getChildren()
    }

    public getSelectedSibling(): FsFileWidget | FsFolderWidget | undefined{
        for(const sibling of this.getSiblings()){
            if(sibling != this && sibling.selected){
                return sibling
            }
        }
        return undefined
    }

    public selectExclusively(select: boolean){
        this.getRoot().deselectDownstream()
        this.selected = select
    }
}

export class FsFolderWidget extends Details{
    public readonly summary: Summary;
    private children = new Map<string, FsFileWidget | FsFolderWidget>()
    public readonly parent: FsFolderWidget | undefined
    public readonly path: Path

    constructor(params: {
        parent: HTMLElement | FsFolderWidget,
        name: string,
        onOpen?: (widget: FsFolderWidget) => void,
    }){
        let summary: Summary;
        let expandWidget: Span;
        super({
            parentElement: params.parent instanceof FsFolderWidget ? params.parent.element : params.parent,
            cssClasses: [CssClasses.ItkFolderWidget],
            children: [
                summary = new Summary({parentElement: undefined, children: [
                    expandWidget = new Span({
                        parentElement: undefined,
                        innerText: "▸ 📁",
                        cssClasses: [CssClasses.ItkExpandFolderWidget],
                        onClick: (ev): false => {
                            ev.stopPropagation()
                            ev.preventDefault()
                            this.element.open = !this.element.open
                            if(this.element.open){
                                expandWidget.element.innerText = "▾ 📂"
                                if(params.onOpen){
                                    params.onOpen(this)
                                }
                            }else{
                                expandWidget.element.innerText = "▸ 📁"
                            }
                            return false
                        }
                    }),
                    new Span({
                        parentElement: undefined,
                        innerText: params.name,
                        cssClasses: [CssClasses.ItkFsNodeName],
                        onClick: (ev): false => {
                            ev.stopPropagation()
                            ev.preventDefault()
                            this.handleNodeClicked(this, ev)
                            return false
                        }
                    })
                ]}),
            ]
        })
        this.path = params.parent instanceof FsFolderWidget ? params.parent.path.joinPath(params.name) : Path.parse("/")
        this.parent = params.parent instanceof FsFolderWidget ? params.parent : undefined
        this.summary = summary;
    }

    public clear(){
        this.children = new Map();
        for(const childElement of Array.from(this.element.children)){
            if(childElement != this.summary.element){
                removeElement(childElement as HTMLElement)
            }
        }
    }

    public handleNodeClicked(node: FsFileWidget | FsFolderWidget, ev: MouseEvent){
        let nodeOriginalSelectionState = node.selected
        if(!ev.ctrlKey && !ev.shiftKey){
            this.getRoot().selected = false
            this.getRoot().deselectDownstream()
            node.selected = !nodeOriginalSelectionState
        }else if(ev.ctrlKey && !ev.shiftKey){
            node.selected = !nodeOriginalSelectionState
        }else if(!ev.ctrlKey && ev.shiftKey && !this.selected){
            const siblings = Array.from(node.parent?.children.values() || [])
            let selectedSibling = siblings.find(sib => sib.selected && sib != node)
            if(selectedSibling === undefined){
                node.selected = !nodeOriginalSelectionState
            }else{
                let sib_index=0
                for(; sib_index < siblings.length; sib_index++){
                    let sib = siblings[sib_index]
                    if(sib == selectedSibling || sib == node){
                        sib.selected = true;
                        sib_index++;
                        break
                    }
                }
                for(;sib_index < siblings.length; sib_index++){
                    let sib = siblings[sib_index]
                    sib.selected = true
                    if(sib == selectedSibling || sib == node){
                        break
                    }
                }
            }
            // let nodesToFlipSelection = new Array<FsFileWidget | FsFolderWidget>()
            // for(const sibling of this.children.values()){

            // }
        }
    }

    public getChildren(): Array<FsFileWidget | FsFolderWidget>{
        return Array.from(this.children.values())
    }

    public get selected(): boolean{
        return this.summary.element.classList.contains(CssClasses.ItkSelected)
    }

    public set selected(value: boolean){
        this.summary.element.classList.remove(CssClasses.ItkSelected)
        if(value){
            this.summary.element.classList.add(CssClasses.ItkSelected)
        }
    }

    public getRoot(): FsFolderWidget{
        let out: FsFolderWidget = this
        while(out.parent){
            out = out.parent
        }
        return out
    }

    public addChildFile(name: string): FsFileWidget{
        const child = new FsFileWidget({parent: this, name})
        this.children.set(name, child)
        return child
    }

    public addChildFolder(params: {name: string, onOpen?: (widget: FsFolderWidget) => void}): FsFolderWidget{
        const child = new FsFolderWidget({parent: this, ...params})
        this.children.set(params.name, child)
        return child
    }

    public getDownstreamSelections(): Array<FsFileWidget | FsFolderWidget>{
        let out = new Array<FsFileWidget | FsFolderWidget>()
        for(const node of this.children.values()){
            if(node.selected){
                out.push(node)
            }
            if(node instanceof FsFolderWidget){
                out = out.concat(node.getDownstreamSelections())
            }
        }
        return out
    }

    public deselectDownstream(){
        for(const child of this.getDownstreamSelections()){
            child.selected = false
        }
    }
}
