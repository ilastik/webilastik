import { Session } from "../../client/ilastik";
import { LoadProjectParamsDto, SaveProjectParamsDto } from "../../client/dto";
import { createElement, createInput, getNowString } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { ErrorPopupWidget } from "./popup";
import { FileLocationInputWidget } from "./file_location_input";

export class ProjectWidget{
    public readonly containerWidget: CollapsableWidget;

    constructor(params: {parentElement: HTMLElement, session: Session}){
        this.containerWidget = new CollapsableWidget({display_name: "Project", parentElement: params.parentElement})
        let form = createElement({tagName: "form", parentElement: this.containerWidget.element})
        const fileLocationInputWidget = new FileLocationInputWidget({
            parentElement: form,
            defaultBucketName: "hbp-image-service",
            defaultPath: Path.parse(`/MyProject_${getNowString()}.ilp`),
            required: true,
        })

        let p = createElement({tagName: "p", parentElement: form})
        let saveButtonText = "Save Project"
        let loadButtonText = "Load Project"
        let saveButton = createInput({inputType: "submit", parentElement: p, value: saveButtonText})
        let loadButton = createInput({inputType: "submit", parentElement: p, value: loadButtonText})
        form.addEventListener("submit", (ev: SubmitEvent): false => {
            ev.preventDefault()
            const location = fileLocationInputWidget.value
            if(location === undefined){
                new ErrorPopupWidget({message: "Some inputs missing"})
                return false
            }

            saveButton.disabled = loadButton.disabled = true

            if(ev.submitter == loadButton){
                loadButton.value = "Loading project..."
                params.session.loadProject(new LoadProjectParamsDto({
                    fs: location.filesystem.toDto(),  project_file_path: location.path.toDto(),
                })).then(result => {
                    if(result instanceof Error){
                        new ErrorPopupWidget({message: result.message})
                    }
                    loadButton.value = loadButtonText
                    saveButton.disabled = loadButton.disabled = false
                })
            }else if(ev.submitter == saveButton){
                saveButton.value = "Saving project..."
                params.session.saveProject(new SaveProjectParamsDto({
                    fs: location.filesystem.toDto(),  project_file_path: location.path.toDto()
                })).then(result => {
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