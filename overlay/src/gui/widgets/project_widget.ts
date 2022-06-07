import { BucketFs, Session } from "../../client/ilastik";
import { createElement, createInput, getNowString } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { BucketFsInput } from "./bucket_fs_input";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { FileNameInput } from "./file_name_input";
import { ErrorPopupWidget } from "./popup";

export class ProjectWidget{
    public readonly containerWidget: CollapsableWidget;

    constructor(params: {parentElement: HTMLElement, session: Session}){
        this.containerWidget = new CollapsableWidget({display_name: "Project", parentElement: params.parentElement})
        let form = createElement({tagName: "form", parentElement: this.containerWidget.element})
        let bucketInput = new BucketFsInput({
            parentElement: form, required: true, value: new BucketFs({bucket_name: "hbp-image-service", prefix: Path.parse("/")})
        })

        let p = createElement({tagName: "p", parentElement: form, cssClasses: [CssClasses.ItkInputParagraph]})
        createElement({tagName: "label", parentElement: p, innerText: "Project File Name: "})
        let projectFileNameInput = new FileNameInput({
            parentElement: p, required: true, value: `MyProject_${getNowString()}.ilp`
        })

        p = createElement({tagName: "p", parentElement: form})
        let submitButtonText = "Save Project"
        let submitButton = createInput({inputType: "submit", parentElement: p, value: submitButtonText})
        form.addEventListener("submit", (ev): false => {
            ev.preventDefault()
            let fs = bucketInput.tryGetFileSystem()
            let project_file_name = projectFileNameInput.value
            if(!fs || !project_file_name){
                new ErrorPopupWidget({message: "Some inputs missing"})
                return false
            }

            submitButton.disabled = true
            submitButton.value = "Saving project..."
            params.session.saveProject({fs,  project_file_name}).then(result => {
                if(result instanceof Error){
                    new ErrorPopupWidget({message: result.message})
                }
                submitButton.disabled = false
                submitButton.value = submitButtonText
            })

            return false
        })
    }
}