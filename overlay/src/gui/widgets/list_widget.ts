import { FsDataSource } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";

export class ListWidget<T>{
    public readonly element: HTMLTableElement;
    private items = new Array<T>();
    private readonly itemRenderer: (value: T) => HTMLElement;
    private readonly onItemRemoved: ((value: T) => void) | undefined;

    constructor(params: {
        parentElement: HTMLElement,
        itemRenderer: (value: T) => HTMLElement,
        onItemRemoved?: (value: T) => void,
        items?: Array<T>,
    }){
        this.element = createElement({tagName: "table", parentElement: params.parentElement})
        this.itemRenderer = params.itemRenderer;
        this.onItemRemoved = params.onItemRemoved;
        this.redraw()
    }

    public push(value: T){
        this.items.push(value)
        this.redraw()
    }

    public clear(){
        let items = this.items
        this.items = []
        this.redraw()
        if(this.onItemRemoved){
            for(const item of items){
                this.onItemRemoved(item)
            }
        }
    }

    private redraw(){
        this.element.innerHTML = ""
        for(let i=0; i<this.items.length; i++){
            const item = this.items[i];
            const tr = createElement({tagName: "tr", parentElement: this.element})
            const contentTd = createElement({tagName: "td", parentElement: tr})
            contentTd.appendChild(this.itemRenderer(item))

            const removeItemTd = createElement({tagName: "td", parentElement: tr})
            const removeButton = createInput({inputType: "button", value: "x", parentElement: removeItemTd, onClick: () => {
                this.items.splice(i, 1);
                this.redraw()
                if(this.onItemRemoved){
                    this.onItemRemoved(item)
                }
            }})
            removeButton.title = "Remove"
        }
    }
}

export class DataSourceListWidget{
    element: HTMLDivElement;
    listWidget: ListWidget<FsDataSource>;

    constructor(params: {
        parentElement: HTMLElement,
        itemRenderer: (value: FsDataSource) => HTMLElement,
        onItemRemoved?: (value: FsDataSource) => void,
        items?: Array<FsDataSource>,
    }){
        this.element = createElement({tagName: "div", parentElement: params.parentElement})
        this.listWidget = new ListWidget({...params, parentElement: this.element})
        const buttonsContainer = createElement({tagName: "p", parentElement: this.element})
        createInput({inputType: "button", value: "Browse Data Proxy", parentElement: buttonsContainer})
    }
}