// import { ListFsDirRequest } from "../../client/dto";
import { Session } from "../../client/ilastik";
import { View, ViewUnion } from "../../viewer/view";
import { Viewer } from "../../viewer/viewer";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { LiveFsTree } from "./live_fs_tree";
import { ErrorPopupWidget, PopupWidget } from "./popup";

export class DataSourceSelectionWidget{
    element: HTMLDetailsElement;
    constructor(params: {parentElement: HTMLElement, session: Session, viewer: Viewer}){
        this.element = new CollapsableWidget({
            display_name: "Data Sources", parentElement: params.parentElement
        }).element

        new DataProxyFilePicker({
            parentElement: this.element,
            session: params.session,
            onOk: async (liveFsTree: LiveFsTree) => {
                const loadingPopup = PopupWidget.LoadingPopup({title: "Loading data sources..."})
                try{
                    let viewPromises = liveFsTree.getSelectedDatasourceUrls().map(urlPromise => urlPromise.then(async (urlResult) => {
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

            },
            okButtonValue: "Open",
        })
    }
}