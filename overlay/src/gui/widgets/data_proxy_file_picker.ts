import { BucketFs, Session } from "../../client/ilastik";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";
import { LiveFsTree } from "./live_fs_tree";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { TextInput } from "./value_input_widget";
import { Div, Label, Paragraph } from "./widget";

export class DataProxyFilePicker{
    element: Div;
    private bucketNameInput: TextInput;


    constructor(params: {
        parentElement: HTMLElement | undefined,
        session: Session,
        defaultBucketName: string,
        onOk: (liveFsTree: LiveFsTree) => void,
        okButtonValue?: string,
        onCancel?: () => void,
    }){
        this.element = new Div({parentElement: params.parentElement, children: [
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({parentElement: undefined, innerText: "Bucket name: "}),
                this.bucketNameInput = new TextInput({parentElement: undefined, value: params.defaultBucketName})
            ]})
        ]})

        new Paragraph({parentElement: this.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Button({inputType: "button", text: "Open file tree", parentElement: undefined, onClick: () => {
                const bucketName = this.bucketNameInput.value
                if(!bucketName){
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
                new Paragraph({parentElement: popup.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
                    new Button({inputType: "button", parentElement: undefined, text: params.okButtonValue || "Ok", onClick: () => {
                        popup.destroy()
                        params.onOk(fsTreeWidget)
                    }}),
                    new Button({inputType: "button", parentElement: undefined, text: "Cancel", onClick: () => {
                        popup.destroy()
                        if(params.onCancel){
                            params.onCancel()
                        }
                    }}),
                ]})
            }})
        ]})
    }

    public get bucketName(): string | undefined{
        return this.bucketNameInput.value
    }
}