import { GetDatasourcesFromUrlParamsDto } from "../../client/dto";
import { FsDataSource, Session } from "../../client/ilastik";
import { Path, Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { DataSourceSelectionWidget } from "./datasource_selection_widget";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { Button, ButtonWidget } from "./input_widget";
import { LiveFsTree } from "./live_fs_tree";
import { PopupWidget } from "./popup";
import { ContainerWidget, Div, Paragraph, Span, Table, TableData, TableRow, TagName, Widget } from "./widget";

export class ListWidget<T> extends Table{
    private items = new Array<T>();
    private readonly itemRenderer: (value: T) => Widget<TagName>;
    private readonly onItemRemoved: ((value: T) => void) | undefined;

    constructor(params: {
        parentElement: ContainerWidget<TagName> | undefined,
        itemRenderer: (value: T) => Widget<TagName>,
        onItemRemoved?: (value: T) => void,
        items?: Array<T>,
    }){
        super({...params, cssClasses: [CssClasses.ItkListWidget]})
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
        if(this.onItemRemoved){
            for(const item of items){
                this.onItemRemoved(item)
            }
        }
        this.redraw()
    }

    private redraw(){
        super.clear()
        if(this.items.length == 0){
            new Paragraph({parentElement: this, innerText: "No items selected"})
            return
        }
        for(let i=0; i<this.items.length; i++){
            const item = this.items[i];

            new TableRow({parentElement: this, cssClasses: [CssClasses.ItkListWidgetRow], children: [
                new TableData({parentElement: undefined, children: [this.itemRenderer(item)]}),
                new TableData({parentElement: undefined, children: [
                    new Button({inputType: "button", parentElement: undefined, text: "✖", title: "Remove this item", onClick: () => {
                        this.items.splice(i, 1);
                        this.redraw()
                        if(this.onItemRemoved){
                            this.onItemRemoved(item)
                        }
                    }})
                ]}),
            ]})
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

export class DataSourceListWidget extends Div{
    listWidget: ListWidget<FsDataSource | DataSourceFetchError>;
    session: Session;
    private defaultBucketName: string;
    private defaultBucketPath: Path;

    constructor(params: {
        parentElement: HTMLElement,
        itemRenderer?: (value: FsDataSource | DataSourceFetchError) => Widget<TagName>,
        onItemRemoved?: (value: FsDataSource | DataSourceFetchError) => void,
        items?: Array<FsDataSource | DataSourceFetchError>,
        session: Session,
        defaultBucketName: string,
        defaultBucketPath: Path,
    }){
        super({parentElement: params.parentElement, cssClasses: [CssClasses.ItkDataSourceListWidget]})
        this.defaultBucketName = params.defaultBucketName
        this.defaultBucketPath = params.defaultBucketPath
        new Div({parentElement: this, cssClasses: [CssClasses.ItkDatasourcesListContainer], children: [
            this.listWidget = new ListWidget({...params, parentElement: undefined, itemRenderer: params.itemRenderer || this.renderDataSourceOrError})
        ]})
        new Paragraph({parentElement: this, children: [
            new Button({inputType: "button", text: "Browse Data Proxy", onClick: this.openFilePicker, parentElement: undefined}),
            new Button({inputType: "button", text: "Clear Datasets", parentElement: undefined, onClick: () => {
                this.listWidget.clear()
            }}),
        ]}),
        this.session = params.session
    }

    public get value(): Array<FsDataSource | DataSourceFetchError>{
        return this.listWidget.value
    }

    private openFilePicker = () => {
        const popup = PopupWidget.ClosablePopup({title: "Select datasets from Data Proxy"})
        const filePicker = new DataProxyFilePicker({
            parentElement: popup.element,
            session: this.session,
            defaultBucketName: this.defaultBucketName,
            defaultBucketPath: this.defaultBucketPath,
            onOk: async (liveFsTree: LiveFsTree) => {
                this.defaultBucketName = filePicker.bucketName || this.defaultBucketName;
                this.defaultBucketPath = filePicker.bucketPath || this.defaultBucketPath;

                let datasourcePromises = liveFsTree.getSelectedUrls().map(url => this.session.getDatasourcesFromUrl(
                    new GetDatasourcesFromUrlParamsDto({url: url.toDto()})
                ))

                for(let dsPromise of datasourcePromises){
                    let datasourcesResult = await DataSourceSelectionWidget.uiResolveUrlToDatasource({
                        datasources: dsPromise, session: this.session
                    })
                    if(datasourcesResult instanceof Error){
                        const errorMessage = datasourcesResult.message;
                        await PopupWidget.AsyncDialog<void>({title: "Error", fillInPopup: (params) => {
                            new Paragraph({parentElement: params.popup.element, innerText: errorMessage});
                            new ButtonWidget({parentElement: params.popup.element, contents: "Ok", onClick: () => {params.resolve()}})
                        }})
                        continue
                    }
                    datasourcesResult.forEach(ds => this.listWidget.push(ds))
                }
            },
            okButtonValue: "Add",
        })
    }

    private renderDataSourceOrError = (ds: FsDataSource | DataSourceFetchError): Span => {
        if(ds instanceof DataSourceFetchError){
            return new Span({parentElement: undefined, cssClasses: [CssClasses.ItkErrorText], children: [
                new Span({parentElement: undefined, innerText: ds.url.raw}),
                new Button({inputType: "button", text: "?", parentElement: undefined, onClick: () => {
                    PopupWidget.OkPopup({title: "Error Details", paragraphs: [ds.cause.message]})
                }}),
            ]})
        }else{
            return new Span({parentElement: undefined, innerText: ds.url.raw})
        }
    }
}