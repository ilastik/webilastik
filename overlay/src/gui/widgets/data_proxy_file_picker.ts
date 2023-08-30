import { BucketFs, Session } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";
import { LiveFsTree } from "./live_fs_tree";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { PathInput, TextInput } from "./value_input_widget";
import { ContainerWidget, Form, Label, Paragraph } from "./widget";

export class DataProxyFilePicker{
    element: Form;
    private bucketNameInput: TextInput;
    private dirPathInput: PathInput;


    constructor(params: {
        parentElement: ContainerWidget<any> | undefined,
        session: Session,
        defaultBucketName: string,
        defaultBucketPath?: Path,
        onOk: (liveFsTree: LiveFsTree) => void,
        okButtonValue?: string,
        onCancel?: () => void,
    }){
        this.element = new Form({parentElement: params.parentElement, children: [
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({parentElement: undefined, innerText: "Bucket name: "}),
                this.bucketNameInput = new TextInput({parentElement: undefined, value: params.defaultBucketName, required: true})
            ]}),
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({parentElement: undefined, innerText: "Path: "}),
                this.dirPathInput = new PathInput({parentElement: undefined, value: params.defaultBucketPath || Path.root, required: true})
            ]}),
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Button({inputType: "submit", text: "Open file tree", parentElement: undefined})
            ]})
        ]})

        this.element.preventSubmitWith(() => {
            const bucketName = this.bucketNameInput.value
            const dirPath = this.dirPathInput.value
            if(!bucketName || !dirPath){
                new ErrorPopupWidget({message: "Please enter a bucket name and a path into the bucket"})
                return
            }

            const popup = new PopupWidget(`Browsing bucket ${bucketName}`)
            const fs = new BucketFs({bucket_name: bucketName});
            const fsTreeWidget = new LiveFsTree({
                fs,
                dirPath: dirPath,
                parentElement: popup.contents,
                session: params.session,
            })
            new Paragraph({parentElement: popup.contents, cssClasses: [CssClasses.ItkInputParagraph], children: [
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
        })


    }

    public get bucketName(): string | undefined{
        return this.bucketNameInput.value
    }
    public get bucketPath(): Path | undefined{
        return this.dirPathInput.value
    }
}