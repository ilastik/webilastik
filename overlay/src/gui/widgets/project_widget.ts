import { Session } from "../../client/ilastik";
import { BucketFSMessage, LoadProjectParamsMessage, SaveProjectParamsMessage } from "../../client/message_schema";
import { createElement, createInput, getNowString } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { BucketFsInput } from "./bucket_fs_input";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { PathInput } from "./path_input";
import { ErrorPopupWidget } from "./popup";

export class ProjectWidget{
    public readonly containerWidget: CollapsableWidget;

    constructor(params: {parentElement: HTMLElement, session: Session}){
        this.containerWidget = new CollapsableWidget({display_name: "Project", parentElement: params.parentElement})
        let form = createElement({tagName: "form", parentElement: this.containerWidget.element})
        let bucketInput = new BucketFsInput({
            parentElement: form,
            hidePrefix: true,
            required: true,
            value: new BucketFSMessage({
                bucket_name: "hbp-image-service", prefix: "/"
            })
        })

        let p = createElement({tagName: "p", parentElement: form, cssClasses: [CssClasses.ItkInputParagraph]})
        createElement({tagName: "label", parentElement: p, innerText: "Project File Path: "})
        let projectFilePathInput = new PathInput({
            parentElement: p, required: true, value: Path.parse(`/MyProject_${getNowString()}.ilp`)
        })

        p = createElement({tagName: "p", parentElement: form})
        let saveButtonText = "Save Project"
        let loadButtonText = "Load Project"
        let saveButton = createInput({inputType: "submit", parentElement: p, value: saveButtonText})
        let loadButton = createInput({inputType: "submit", parentElement: p, value: loadButtonText})
        form.addEventListener("submit", (ev: SubmitEvent): false => {
            ev.preventDefault()

            let fs = bucketInput.value
            let project_file_path = projectFilePathInput.value
            if(!fs || !project_file_path){
                new ErrorPopupWidget({message: "Some inputs missing"})
                return false
            }

            saveButton.disabled = loadButton.disabled = true

            if(ev.submitter == loadButton){
                loadButton.value = "Loading project..."
                params.session.loadProject(new LoadProjectParamsMessage({fs,  project_file_path: project_file_path.raw})).then(result => {
                    if(result instanceof Error){
                        new ErrorPopupWidget({message: result.message})
                    }
                    loadButton.value = loadButtonText
                    saveButton.disabled = loadButton.disabled = false
                })
            }else if(ev.submitter == saveButton){
                saveButton.value = "Saving project..."
                params.session.saveProject(new SaveProjectParamsMessage({fs,  project_file_path: project_file_path.raw})).then(result => {
                    if(result instanceof Error){
                        new ErrorPopupWidget({message: result.message})
                    }
                    saveButton.value = saveButtonText
                    saveButton.disabled = loadButton.disabled = false
                })
            }
            return false
        })
    }
}