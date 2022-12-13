import { GetDatasourcesFromUrlParamsDto } from "../../client/dto";
import { FsDataSource, Session } from "../../client/ilastik";
import { HashMap } from "../../util/hashmap";
import { createElement, createInput } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { LiveFsTree } from "./live_fs_tree";
import { PopupWidget } from "./popup";

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
        this.element = createElement({tagName: "table", parentElement: params.parentElement, cssClasses: [CssClasses.ItkListWidget]})
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
            const tr = createElement({tagName: "tr", parentElement: this.element, cssClasses: [CssClasses.ItkListWidgetRow]})
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

    public get value(): Array<T>{
        return this.items.slice()
    }
}

export class DataSourceFetchError extends Error{
    public readonly url: Url;
    public readonly cause: Error;
    constructor(params: {url: Url, cause: Error}){
        super(params.cause.message)
        this.url = params.url
        this.cause = params.cause
    }
}

export class DataSourceListWidget{
    element: HTMLDivElement;
    listWidget: ListWidget<FsDataSource | DataSourceFetchError>;
    session: Session;

    constructor(params: {
        parentElement: HTMLElement,
        itemRenderer?: (value: FsDataSource | DataSourceFetchError) => HTMLElement,
        onItemRemoved?: (value: FsDataSource | DataSourceFetchError) => void,
        items?: Array<FsDataSource | DataSourceFetchError>,
        session: Session,
    }){
        this.session = params.session
        this.element = createElement({tagName: "div", parentElement: params.parentElement, cssClasses: [CssClasses.ItkDataSourceListWidget]})
        this.listWidget = new ListWidget({...params, parentElement: this.element, itemRenderer: params.itemRenderer || this.renderDataSourceOrError})
        const buttonsContainer = createElement({tagName: "p", parentElement: this.element})
        createInput({inputType: "button", value: "Browse Data Proxy", parentElement: buttonsContainer, onClick: () => this.openFilePicker()})
    }

    public get value(): Array<FsDataSource | DataSourceFetchError>{
        return this.listWidget.value
    }

    private openFilePicker = () => {
        const popup = PopupWidget.ClosablePopup({title: "Select datasets from Data Proxy"})
        new DataProxyFilePicker({
            parentElement: popup.element,
            session: this.session,
            onOk: (liveFsTree: LiveFsTree) => this.addDataSourcesFromUrls(liveFsTree.getSelectedUrls()),
            okButtonValue: "Add",
        })
    }

    private addDataSourcesFromUrls = async (urls: Url[]) => {
        PopupWidget.WaitPopup({
            title: "Loading data sources...",
            operation: (async () => {
                const datasourcePromises = new HashMap<Url, Promise<FsDataSource[] | FsDataSource | undefined | Error>, string>();
                urls.forEach(url => datasourcePromises.set(
                    url,
                    this.session.getDatasourcesFromUrl(new GetDatasourcesFromUrlParamsDto({url: url.toDto()}))
                ));
                for(const [url, dsPromise] of datasourcePromises.entries()){
                    const datasources_result = await dsPromise;
                    if(datasources_result instanceof Error){
                        this.listWidget.push(new DataSourceFetchError({url, cause: datasources_result}))
                    }else if(datasources_result === undefined){
                        this.listWidget.push(new DataSourceFetchError({url, cause: new Error(`Could not open datasource at ${url.raw}`)}))
                    }else if(datasources_result instanceof Array){
                        datasources_result.forEach(ds => this.listWidget.push(ds))
                    }else{
                        this.listWidget.push(datasources_result)
                    }
                }
            })(),
        })
    }

    private renderDataSourceOrError = (ds: FsDataSource | DataSourceFetchError): HTMLElement => {
        if(ds instanceof DataSourceFetchError){
            return createElement({
                tagName: "span", parentElement: undefined, cssClasses: [CssClasses.ErrorText], innerText: ds.url.raw, onClick: () => {
                    PopupWidget.OkPopup({title: "Error Details", paragraphs: [ds.cause.message]})
                }
            })
        }else{
            return createElement({tagName: "span", parentElement: undefined, innerText: ds.url.raw})
        }
    }
}