// import { ListFsDirRequest } from "../../client/dto";
import { GetDatasourcesFromUrlParamsDto } from "../../client/dto";
import { DziLevelDataSource, FsDataSource, PrecomputedChunksDataSource, Session } from "../../client/ilastik";
import { IViewerDriver } from "../../drivers/viewer_driver";
import { HashMap } from "../../util/hashmap";
import { Path, Url } from "../../util/parsed_url";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { ButtonWidget, MultiSelect } from "./input_widget";
import { LiveFsTree } from "./live_fs_tree";
import { PopupWidget } from "./popup";
import { UrlInput } from "./value_input_widget";
import { Anchor, Div, Form, Li, Paragraph, Span, Ul } from "./widget";

type ChoiceTransition = {
    nextState: AutoChooseScaleState,
    chosenScales: FsDataSource[]
}

class NoDefaultScale{
    public async chooseScales(scales: FsDataSource[]): Promise<ChoiceTransition>{
        const chosenScales = await DataSourceSelectionWidget.uiChooseScales(scales)
        if(chosenScales.length == 1 && scales.length > 1){
            return {nextState: new InferredDefaultScale(chosenScales[0]), chosenScales}
        }else{
            return {nextState: new NoDefaultScale(), chosenScales}
        }
    }
}
class InferredDefaultScale{
    constructor(public readonly ds: FsDataSource){}
    public async chooseScales(scales: FsDataSource[]): Promise<ChoiceTransition>{
        const candidate = scales.find(ds => ds.hasSameScaleAs(this.ds))
        if(!candidate){
            return new NoDefaultScale().chooseScales(scales)
        }
        return new Promise(resolve => {
            let popup = new PopupWidget("Using previously selected scale");
            new Paragraph({
                parentElement: popup.contents,
                innerText: `Do you want to use the previously selected scale (${this.ds.resolutionString}) for all URLs of this kind of dataset?`
            })
            new Paragraph({parentElement: popup.contents, children: [
                new ButtonWidget({parentElement: undefined, contents: "Yes", onClick: () => {
                    popup.destroy()
                    resolve({nextState: new ConfirmedDefaultScale(this.ds), chosenScales: [candidate]})
                }}),
                new ButtonWidget({parentElement: undefined, contents: "No, but ask again", onClick: () => {
                    popup.destroy()
                    resolve(new NoDefaultScale().chooseScales(scales))
                }}),
                new ButtonWidget({parentElement: undefined, contents: "Choose all scales manually", onClick: async () => {
                    popup.destroy()
                    resolve(new NeverUseDefaultScale().chooseScales(scales))
                }}),
            ]})
        })
    }
}
class ConfirmedDefaultScale{
    constructor(public readonly ds: FsDataSource){}
    public async chooseScales(scales: FsDataSource[]): Promise<ChoiceTransition>{
        const candidate = scales.find(ds => ds.hasSameScaleAs(this.ds))
        if(candidate){
            return {nextState: this, chosenScales: [candidate]}
        }else{
            return new NoDefaultScale().chooseScales(scales)
        }
    }
}
class NeverUseDefaultScale{
    public async chooseScales(scales: FsDataSource[]): Promise<ChoiceTransition>{
        return {nextState: new NeverUseDefaultScale(), chosenScales: await DataSourceSelectionWidget.uiChooseScales(scales)}
    }
}

type AutoChooseScaleState = {chooseScales(scales: FsDataSource[]): Promise<ChoiceTransition>} & (
    NoDefaultScale |
    InferredDefaultScale |
    ConfirmedDefaultScale |
    NeverUseDefaultScale
)

export class DataSourceSelectionWidget{
    private element: HTMLDivElement;
    private session: Session;
    public readonly viewer: Viewer;
    public readonly lanesContainer: Div;
    private defaultBucketPath: Path;
    private defaultBucketName: string;

    constructor(params: {
        parentElement: HTMLElement,
        session: Session,
        defaultBucketName: string,
        defaultBucketPath: Path,
        viewer_driver: IViewerDriver,
        help: string[],
    }){
        this.element = new CollapsableWidget({
            display_name: "Training Images", parentElement: params.parentElement, help: params.help
        }).element
        this.session = params.session
        this.defaultBucketName = params.defaultBucketName
        this.defaultBucketPath = params.defaultBucketPath

        new Paragraph({parentElement: this.element, children: [
            new ButtonWidget({contents: "🔗 Enter URL", parentElement: undefined, onClick: () => {
                const popup = PopupWidget.ClosablePopup({title: "Enter dataset URL"})
                let urlInput: UrlInput;
                new Form({parentElement: popup.contents, children: [
                    urlInput = new UrlInput({
                        parentElement: popup.contents, required: true, inlineCss: {width: "30em"}
                    }),
                    new Paragraph({parentElement: popup.contents, children: [
                        new ButtonWidget({buttonType: "submit", parentElement: undefined, contents: "Open", onClick: () => {}})
                    ]})
                ]}).preventSubmitWith(() => {
                    const url = urlInput.value
                    if(!url){
                        return
                    }
                    popup.destroy()
                    PopupWidget.WaitPopup({
                        title: "Loading data sources...",
                        operation: DataSourceSelectionWidget.tryOpenViews({
                            urls: [url],
                            session: this.session,
                            viewer: this.viewer,
                        }),
                    })
                })
            }}),
            new ButtonWidget({contents: "🪣 Open from Data Proxy", parentElement: undefined, onClick: () => {
                const popup = PopupWidget.ClosablePopup({title: "Select datasets from Data Proxy"})
                const filePicker = new DataProxyFilePicker({
                    parentElement: popup.contents,
                    session: this.session,
                    defaultBucketName: this.defaultBucketName,
                    defaultBucketPath: this.defaultBucketPath,
                    onOk: (liveFsTree: LiveFsTree) => {
                        popup.destroy()
                        this.defaultBucketName = filePicker.bucketName || this.defaultBucketName;
                        this.defaultBucketPath = filePicker.bucketPath || this.defaultBucketPath;
                        PopupWidget.WaitPopup({
                            title: "Loading data sources...",
                            operation: DataSourceSelectionWidget.tryOpenViews({
                                urls: liveFsTree.getSelectedUrls(),
                                session: this.session,
                                viewer: this.viewer,
                            }),
                        })
                    },
                    okButtonValue: "Open",
                })
            }}),
        ]})

        this.lanesContainer = new Div({parentElement: this.element})
        this.viewer = new Viewer({
            driver: params.viewer_driver, session: params.session, parentElement: this.element
        })
    }

    public destroy(){
        this.viewer.destroy()
        // this.element.destroy()
    }

    public static async uiResolveUrlToDatasources(params: {
        datasources: Url,
        session: Session,
    }): Promise<FsDataSource[] | Error>{
        let datasourcesResult: FsDataSource[] | undefined | Error;
        datasourcesResult = await PopupWidget.WaitPopup({
            title: `Opening ${params.datasources.raw}`,
            operation: params.session.getDatasourcesFromUrl(
                new GetDatasourcesFromUrlParamsDto({
                    url: params.datasources.toDto(),
                })
            )
        })
        return datasourcesResult
    }

    public static async uiChooseScales(scales: FsDataSource[]): Promise<FsDataSource[]>{
        if(scales.length == 1){
            return scales
        }
        return PopupWidget.WaitPopup({
            title: "Select resolutions to open",
            withSpinner: false,
            operation: (popup: PopupWidget) => new Promise<FsDataSource[]>(resolve => {

                let datasourcesSelect = new MultiSelect<FsDataSource>({
                    parentElement: popup.contents,
                    options: scales,
                    renderer: (ds) => new Span({parentElement: undefined, innerText: ds.getDisplayString()}),
                })
                new ButtonWidget({parentElement: popup.contents, contents: "Open Selected", onClick: () => resolve(datasourcesSelect.value)})
                new ButtonWidget({parentElement: popup.contents, contents: "Skip", onClick: () => resolve([])})
            })
        })
    }

    public static async tryResolveDataSources(
        params: {urls: Url[], session: Session}
    ): Promise<HashMap<Url, FsDataSource[] | Error, string>>{
        let out = new HashMap<Url, FsDataSource[] | Error, string>()
        let datasourcePromises = new Map(params.urls.map(url => [
            url,
            params.session.getDatasourcesFromUrl(new GetDatasourcesFromUrlParamsDto({url: url.toDto()}))
        ]))

        let prevPrecompDataSource: AutoChooseScaleState = new NoDefaultScale()
        let prevDziDataSource: AutoChooseScaleState = new NoDefaultScale()
        let prevSingleScaleDataSource = new NeverUseDefaultScale()

        for(const [url, dsPromise] of datasourcePromises.entries()){
            const datasourcesResult = await PopupWidget.WaitPopup({title: `Getting datasources...`, operation: dsPromise});
            if(datasourcesResult instanceof Error){
                out.set(url, datasourcesResult)
                continue
            }
            if(datasourcesResult.length == 0){ //FIXME: is this even possible?
                continue
            }
            let chosenScales: FsDataSource[]
            if(datasourcesResult[0] instanceof PrecomputedChunksDataSource){
                ({nextState: prevPrecompDataSource, chosenScales} = await prevPrecompDataSource.chooseScales(datasourcesResult))
            }else if(datasourcesResult[0] instanceof DziLevelDataSource){
                ({nextState: prevDziDataSource, chosenScales} = await prevDziDataSource.chooseScales(datasourcesResult))
            }else{
                ({nextState: prevSingleScaleDataSource, chosenScales} = await prevSingleScaleDataSource.chooseScales(datasourcesResult))
            }
            out.set(url, chosenScales)
        }
        return out
    }

    public static async tryOpenViews(
        {urls, session, viewer}:
        {urls: Array<Url>, session: Session, viewer: Viewer}
    ): Promise<void>{
        let datasourcesMap = await this.tryResolveDataSources({urls, session})

        let errorMessages: string[] = []
        let unsupportedUrls: Url[] = []

        for(const [url, results] of datasourcesMap.entries()){
            if(results instanceof Error){
                errorMessages.push(`Could not resolve datasource at ${url.raw}: ${results.message}`)
                continue
            }
            for(let ds of results){
                if(!(ds instanceof PrecomputedChunksDataSource) && !(ds instanceof DziLevelDataSource)){
                    unsupportedUrls.push(ds.url)
                    continue
                }
                const openingResult = await viewer.openLane({
                    name: ds.getDisplayString(),
                    isVisible: true,
                    rawData: ds,
                })
                if(openingResult instanceof Error){
                    errorMessages.push(`Could not open view: ${openingResult.message}`)
                }
            }
        }

        if(unsupportedUrls.length == 0 && errorMessages.length == 0){
            return
        }
        return PopupWidget.WaitPopup({
            title: "Errors when opening some data sources",
            withSpinner: false,
            operation: (popup) => new Promise(resolve => {
                for(const errorMsg of errorMessages){
                    new Paragraph({parentElement: popup.contents, innerText: errorMsg, cssClasses: [CssClasses.ItkErrorText]})
                }
                if(unsupportedUrls.length > 0){
                    new Paragraph({parentElement: popup.contents, children: [
                        new Span({parentElement: undefined, innerText:
                            `Only datasources in Neuroglancer's Precomputed Chunks or Deep Zoom format are supported in the viewer at this time ` +
                            `(though you might still be able to use it in batch export).` +
                            `You can try converting your images to the Precomputed Chunks format by using the `,
                        }),
                        new Anchor({
                            parentElement: undefined,
                            href: Url.parse('https://wiki.ebrains.eu/bin/view/Collabs/hbp-image-service-user-guide/'),
                            rel: "noopener noreferrer",
                            target: "_blank",
                            children: [new Span({parentElement: undefined, innerText: 'EBRAINS image service'})],
                        })
                    ]})
                    new Paragraph({parentElement: popup.contents, innerText: "Unsupported URLs:"});
                    new Ul({parentElement: popup.contents, children: unsupportedUrls.map(url => {
                        return new Li({parentElement: undefined, innerText: url.raw})
                    })})
                }
                new Paragraph({parentElement: popup.contents, children: [
                    new ButtonWidget({parentElement: undefined, contents: "Ok", onClick: () => resolve()})
                ]})
            })
        })
    }
}