// import { ListFsDirRequest } from "../../client/dto";
import { GetDatasourcesFromUrlParamsDto } from "../../client/dto";
import { DziLevelDataSource, FsDataSource, PrecomputedChunksDataSource, Session } from "../../client/ilastik";
import { IViewerDriver } from "../../drivers/viewer_driver";
import { Url } from "../../util/parsed_url";
import { Viewer } from "../../viewer/viewer";
import { CssClasses } from "../css_classes";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { Button } from "./input_widget";
import { LiveFsTree } from "./live_fs_tree";
import { PopupWidget } from "./popup";
import { Anchor, Div, Label, Paragraph, Span } from "./widget";

export class DataSourceSelectionWidget{
    private element: HTMLDetailsElement;
    private session: Session;
    public readonly viewer: Viewer;
    public readonly lanesContainer: Div;

    constructor(params: {
        parentElement: HTMLElement, session: Session, defaultBucketName: string, viewer_driver: IViewerDriver
    }){
        this.element = new CollapsableWidget({
            display_name: "Data Sources", parentElement: params.parentElement
        }).element
        this.session = params.session

        new DataProxyFilePicker({
            parentElement: this.element,
            session: params.session,
            defaultBucketName: params.defaultBucketName,
            onOk: (liveFsTree: LiveFsTree) => PopupWidget.WaitPopup({
                title: "Loading data sources...", operation: this.tryOpenViews(liveFsTree)
            }),
            okButtonValue: "Open",
        })

        this.lanesContainer = new Div({parentElement: this.element})
        new Label({parentElement: this.element, innerText: "Data Sources:"})
        this.viewer = new Viewer({
            driver: params.viewer_driver, session: params.session, parentElement: this.element
        })
    }

    public destroy(){
        this.viewer.destroy()
        // this.element.destroy()
    }

    private tryOpenViews = async (liveFsTree: LiveFsTree) => {
        let selectedUrls = liveFsTree.getSelectedUrls()
        let viewPromises = selectedUrls.map(url => this.session.getDatasourcesFromUrl(
            new GetDatasourcesFromUrlParamsDto({
                url: url.toDto(),
            }))
        )

        let errorMessages: string[] = []
        let unsupportedUrls: Url[] = []

        for(let i = 0; i < selectedUrls.length; i++){
            let url = selectedUrls[i]
            let viewPromise = viewPromises[i]

            let viewResult = await viewPromise;
            if(viewResult instanceof Error){
                errorMessages.push(`Could not open view: ${viewResult.message}`)
            }else if(viewResult === undefined){
                console.log("FIXME: handle undefined datasource? Maybe just don't have undefined at all?")
            }else{
                const datasources: FsDataSource[] = viewResult
                //FIXME: viewer driver should be the one responsible for checking which datasources it supports
                if(datasources.find(ds => !(ds instanceof PrecomputedChunksDataSource || ds instanceof DziLevelDataSource))){
                    errorMessages.push(`Unsupported datasources from ${url.raw}`)
                    unsupportedUrls.push(url)
                    continue
                }

                const selectedResolution: FsDataSource = datasources.length == 1 ? datasources[0] : await PopupWidget.AsyncDialog({
                    title: "Select a resolution",
                    fillInPopup: (params: {popup: PopupWidget, resolve: (result: FsDataSource) => void}) => {
                        for(const ds of datasources){
                            const p = new Paragraph({parentElement: params.popup.element})
                            new Button({inputType: "button", parentElement: p, text: ds.resolutionString, onClick: () => params.resolve(ds)})
                        }
                    }
                })

                this.viewer.openLane({
                    name: `${selectedResolution.url.name}`,
                    isVisible: true,
                    rawData: selectedResolution,
                })
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
                    `Only datasources in Neuroglancer's Precomputed Chunks format are supported in the viewer at this time ` +
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