// import { ListFsDirRequest } from "../../client/dto";
import { ListFsDirRequest } from "../../client/dto";
import { BucketFs, Session } from "../../client/ilastik";
import { createInput, createInputParagraph } from "../../util/misc";
import { View, ViewUnion } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { FsFolderWidget } from "./fs_tree";
import { LiveFsTree } from "./live_fs_tree";
import { ErrorPopupWidget, PopupWidget } from "./popup";

export class DataSourceSelectionWidget{
    element: HTMLDetailsElement;
    constructor(params: {parentElement: HTMLElement, session: Session, viewer: Viewer}){
        this.element = new CollapsableWidget({
            display_name: "Data Sources", parentElement: params.parentElement
        }).element


        const bucketNameInput = createInputParagraph({
            inputType: "text", parentElement: this.element, value: "hbp-image-service", label_text: "Bucket name: "
        })
        createInputParagraph({inputType: "button", parentElement: this.element, value: "Open file tree", onClick: () => {
            const bucketName = bucketNameInput.value
            if(bucketName.length == 0){
                new ErrorPopupWidget({message: "Please enter a bucket name"})
                return
            }

            const popup = new PopupWidget(`Browsing bucket ${bucketName}`)
            const fs = new BucketFs({bucket_name: bucketName});
            const fsTreeWidget = new LiveFsTree({
                fs,
                parentElement: popup.element,
                session: params.session,
            })
            createInput({inputType: "button", parentElement: popup.element, value: "Open", onClick: async () => {
                popup.destroy()
                const viewPromises = new Array<Promise<ViewUnion>>();
                const loadingPopup = PopupWidget.LoadingPopup({title: "Loading data sources..."})
                try{
                    for(const node of fsTreeWidget.getSelectedNodes()){
                        let url = fs.getUrl(node.path)
                        if(node instanceof FsFolderWidget){
                            const result = await params.session.listFsDir(new ListFsDirRequest({fs: fs.toDto(), path: node.path.toDto()}))
                            if(result instanceof Error){
                                new ErrorPopupWidget({message: result.message})
                                return
                            }
                            if(result.files.find(path => path.endsWith("/info"))){
                                url = url.updatedWith({datascheme: "precomputed"})
                            }
                        }
                        const viewPromise =  View.tryOpen({name: url.path.name, url, session: params.session})
                        viewPromises.push(viewPromise)
                    }
                    for(const viewPromise of viewPromises){
                        params.viewer.openDataView(await viewPromise)
                    }
                }finally{
                    loadingPopup.destroy()
                }
            }})
            createInput({inputType: "button", parentElement: popup.element, value: "Cancel", onClick: () => {
                popup.destroy()
            }})
        }})
    }
}