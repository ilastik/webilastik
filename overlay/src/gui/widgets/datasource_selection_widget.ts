// import { ListFsDirRequest } from "../../client/dto";
import { PrecomputedChunksDataSource, Session } from "../../client/ilastik";
import { Url } from "../../util/parsed_url";
import { FailedView, RawDataView, View } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { LiveFsTree } from "./live_fs_tree";
import { PopupWidget } from "./popup";
import { Anchor, Div, Paragraph, Span } from "./widget";

export class DataSourceSelectionWidget{
    private element: HTMLDetailsElement;
    private session: Session;
    private viewer: Viewer;

    constructor(params: {
        parentElement: HTMLElement, session: Session, viewer: Viewer, defaultBucketName: string,
    }){
        this.element = new CollapsableWidget({
            display_name: "Data Sources", parentElement: params.parentElement
        }).element
        this.session = params.session
        this.viewer = params.viewer

        new DataProxyFilePicker({
            parentElement: this.element,
            session: params.session,
            defaultBucketName: params.defaultBucketName,
            onOk: (liveFsTree: LiveFsTree) => PopupWidget.WaitPopup({
                title: "Loading data sources...", operation: this.tryOpenViews(liveFsTree)
            }),
            okButtonValue: "Open",
        })
    }

    private tryOpenViews = async (liveFsTree: LiveFsTree) => {
        let viewPromises = liveFsTree.getSelectedUrls().map(url => View.tryOpen({
            name: url.path.name, url, session: this.session, opacity: 1.0, visible: true,
        }))

        let imageServiceHintWidget: Div | undefined = undefined
        let errorMessageWidgets = new Array<Paragraph>();


        for(const viewPromise of viewPromises){
            const viewResult = await viewPromise;
            if(viewResult instanceof FailedView){
                errorMessageWidgets.push(new Paragraph({
                    parentElement: undefined, innerText: `Could not open view: ${viewResult.url}`
                }))
            }else if(viewResult instanceof RawDataView && viewResult.getDatasources()?.find(ds => !(ds instanceof PrecomputedChunksDataSource))){
                errorMessageWidgets.push(new Paragraph({
                    parentElement: undefined, innerText: `Unsupported format: ${viewResult.url}`
                }))
                imageServiceHintWidget = imageServiceHintWidget || new Div({parentElement: undefined, children: [
                    new Paragraph({
                        parentElement: undefined,
                        children: [
                            new Span({parentElement: undefined, innerText:
                                `Only datasources in Neuroglancer's Precomputed Chunks format are supported in the viewer at this time ` +
                                `(though you might still be able to use it in batch export).` +
                                `You can try converting your images to the Precomputed Chunks format by using the `,
                            }),
                            new Anchor({
                                parentElement: undefined,
                                href: Url.parse('https://wiki.ebrains.eu/bin/view/Collabs/hbp-image-service-user-guide/'),
                                rel: "noopener noreferrer",
                                target: "_blank",
                                children: [
                                    new Span({parentElement: undefined, innerText: 'EBRAINS image service'})
                                ]
                            })
                        ]
                    })

                ]})
            }else{
                this.viewer.reconfigure({toOpen: [viewResult]})
            }
        }

        if(errorMessageWidgets.length > 0 || imageServiceHintWidget){
            let popup = new PopupWidget("Errors when opening data sources", true)
            if(imageServiceHintWidget){
                popup.appendChild(imageServiceHintWidget)
            }
            for(const errorMsgWidget of errorMessageWidgets){
                popup.appendChild(errorMsgWidget)
            }
        }
    }
}