// import { ListFsDirRequest } from "../../client/dto";
import { BucketFs, Session } from "../../client/ilastik";
import { createInput, createInputParagraph } from "../../util/misc";
import { View, ViewUnion } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";
import { CollapsableWidget } from "./collapsable_applet_gui";
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
                const loadingPopup = PopupWidget.LoadingPopup({title: "Loading data sources..."})
                try{
                    let viewPromises = fsTreeWidget.getSelectedDatasourceUrls().map(urlPromise => urlPromise.then(async (urlResult) => {
                        return urlResult instanceof Error ?
                            urlResult:
                            await View.tryOpen({name: urlResult.path.name, url: urlResult, session: params.session})
                    }))
                    const viewsToOpen = new Array<ViewUnion>();
                    for(const viewPromise of viewPromises){
                        const viewResult = await viewPromise;
                        if(viewResult instanceof Error){
                            new ErrorPopupWidget({message: `Could not open view: ${viewResult.message}`})
                            return
                        }
                        viewsToOpen.push(viewResult)
                    }
                    viewsToOpen.forEach(v => params.viewer.openDataView(v))
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