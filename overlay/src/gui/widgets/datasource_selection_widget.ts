// import { ListFsDirRequest } from "../../client/dto";
import { GetDatasourcesFromUrlParamsDto } from "../../client/dto";
import { FsDataSource, Session } from "../../client/ilastik";
import { IViewerDriver } from "../../drivers/viewer_driver";
import { Path, Url } from "../../util/parsed_url";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { Button, ButtonWidget, MultiSelect } from "./input_widget";
import { LiveFsTree } from "./live_fs_tree";
import { PopupWidget } from "./popup";
import { Anchor, Div, Paragraph, Span } from "./widget";

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
            display_name: "Data Sources", parentElement: params.parentElement, help: params.help
        }).element
        this.session = params.session
        this.defaultBucketName = params.defaultBucketName
        this.defaultBucketPath = params.defaultBucketPath

        new Paragraph({parentElement: this.element, children: [
            new Button({inputType: "button", text: "Open...", parentElement: undefined, onClick: () => {
                const popup = PopupWidget.ClosablePopup({title: "Select datasets from Data Proxy"})
                const filePicker = new DataProxyFilePicker({
                    parentElement: popup.element,
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
            }})
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

    public static async uiResolveUrlToDatasource(params: {
        datasources: Url | Promise<FsDataSource[] | undefined | Error>,
        session: Session
    }): Promise<FsDataSource[] | Error>{
        let datasourcesResult: FsDataSource[] | undefined | Error;
        if(params.datasources instanceof Url){
            datasourcesResult = await PopupWidget.WaitPopup({
                title: `Opening ${params.datasources.raw}`,
                operation: params.session.getDatasourcesFromUrl(
                    new GetDatasourcesFromUrlParamsDto({
                        url: params.datasources.toDto(),
                    })
                )
            })
        }else{
            const datasourcesPromise = params.datasources
            datasourcesResult = await PopupWidget.WaitPopup({
                title: `Opening datasources...`,
                operation: datasourcesPromise
            })
        }
        if(datasourcesResult instanceof Error){
            return datasourcesResult
        }
        if(datasourcesResult === undefined){
            return new Error(`Unsupported datasource format`)
        }
        if(datasourcesResult.length == 1){
            return datasourcesResult
        }
        const datasources = datasourcesResult
        return PopupWidget.AsyncDialog({
            title: "Select resolutions to open",
            fillInPopup: (params: {popup: PopupWidget, resolve: (result: FsDataSource[]) => void}) => {
                let datasourcesSelect = new MultiSelect<FsDataSource>({
                    parentElement: params.popup.element,
                    options: datasources,
                    renderer: (ds) => new Span({parentElement: undefined, innerText: ds.getDisplayString()}),
                })
                new ButtonWidget({parentElement: params.popup.element, contents: "Open Selected", onClick: () => params.resolve(datasourcesSelect.value)})
                new ButtonWidget({parentElement: params.popup.element, contents: "Skip", onClick: () => params.resolve([])})
            }
        })
    }

    public static async tryOpenViews({urls, session, viewer}: {urls: Array<Url>, session: Session, viewer: Viewer}){
        let viewPromises = urls.map(url => session.getDatasourcesFromUrl(
            new GetDatasourcesFromUrlParamsDto({
                url: url.toDto(),
            }))
        )

        let errorMessages: string[] = []
        let unsupportedUrls: Url[] = []

        for(let i = 0; i < urls.length; i++){
            let viewPromise = viewPromises[i]

            let datasourcesResult = await this.uiResolveUrlToDatasource({datasources: viewPromise, session})
            if(datasourcesResult instanceof Error){
                errorMessages.push(`Could not resolve datasource: ${datasourcesResult.message}`)
                continue
            }
            for(let ds of datasourcesResult){
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

        if(unsupportedUrls.length > 0 || errorMessages.length > 0){
            let popup = new PopupWidget("Errors when opening data sources", true)
            for(const errorMsg of errorMessages){
                new Paragraph({parentElement: popup.element, innerText: errorMsg, cssClasses: [CssClasses.ItkErrorText]})
            }
            if(unsupportedUrls.length > 0){
                const p = new Paragraph({parentElement: popup.element})
                new Span({parentElement: p, innerText:
                    `Only datasources in Neuroglancer's Precomputed Chunks or Deep Zoom format are supported in the viewer at this time ` +
                    `(though you might still be able to use it in batch export).` +
                    `You can try converting your images to the Precomputed Chunks format by using the `,
                }),
                new Anchor({
                    parentElement: p,
                    href: Url.parse('https://wiki.ebrains.eu/bin/view/Collabs/hbp-image-service-user-guide/'),
                    rel: "noopener noreferrer",
                    target: "_blank",
                    children: [new Span({parentElement: undefined, innerText: 'EBRAINS image service'})],
                })
            }
        }
    }
}