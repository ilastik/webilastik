import { BucketFs, Session } from "../../client/ilastik";
import { createElement, createInput, createInputParagraph } from "../../util/misc";
import { LiveFsTree } from "./live_fs_tree";
import { ErrorPopupWidget, PopupWidget } from "./popup";

export class DataProxyFilePicker{
    element: HTMLDivElement;

    constructor(params: {
        parentElement: HTMLElement,
        session: Session,
        onOk: (liveFsTree: LiveFsTree) => void,
        okButtonValue?: string,
        onCancel?: () => void,
    }){
        this.element = createElement({tagName: "div", parentElement: params.parentElement})
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
            const buttonsP = createElement({tagName: "p", parentElement: popup.element})
            createInput({inputType: "button", parentElement: buttonsP, value: params.okButtonValue || "Ok", onClick: () => {
                popup.destroy()
                params.onOk(fsTreeWidget)
            }})
            createInput({inputType: "button", parentElement: buttonsP, value: "Cancel", onClick: () => {
                popup.destroy()
                if(params.onCancel){
                    params.onCancel()
                }
            }})

        }})
    }
}