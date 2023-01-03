import { Session } from "../../client/ilastik";
import { LoadProjectParamsDto, SaveProjectParamsDto } from "../../client/dto";
import { dateToSafeString } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { FileLocationInputWidget } from "./file_location_input";
import { Paragraph } from "./widget";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";

export class ProjectWidget{
    public readonly containerWidget: CollapsableWidget;
    private readonly session: Session;
    private savedPath: Path | undefined
    private readonly defaultPath: Path;

    constructor(params: {parentElement: HTMLElement, session: Session}){
        this.session = params.session
        this.defaultPath = Path.parse(`/MyProject_${dateToSafeString(params.session.startTime || new Date())}.ilp`)
        this.containerWidget = new CollapsableWidget({display_name: "Project", parentElement: params.parentElement})
        new Paragraph({parentElement: this.containerWidget.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Button({inputType: "button", parentElement: undefined, text: "Save Project", onClick: this.popupSaveProject}),
            new Button({inputType: "button", parentElement: undefined, text: "Load Project", onClick: this.popupLoadProject}),
            new Button({inputType: "button", parentElement: undefined, text: "Download Project", onClick: () => {
                    const ilp_form = document.body.appendChild(document.createElement("form"))
                    ilp_form.action = params.session.sessionUrl.joinPath("download_project_as_ilp").raw
                    ilp_form.method = "post"
                    ilp_form.target = "_blank"
                    ilp_form.style.display = "none"
                    ilp_form.submit()
            }}),
        ]})
    }
    private popupSaveProject = () => {
        const popup = new PopupWidget("Save Project", true);
        const fileLocationInput = new FileLocationInputWidget({
            parentElement: popup.element,
            filesystemChoices: ["data-proxy"],
            defaultBucketName: "hbp-image-service",
            defaultPath: this.savedPath || this.defaultPath,
        })
        new Paragraph({parentElement: popup.element, children: [
            new Button({inputType: "button", text: "Save Project", parentElement: undefined, onClick: async () => {
                const fileLocation = fileLocationInput.value
                if(fileLocation === undefined){
                    new ErrorPopupWidget({message: "Missing parameters"})
                    return
                }
                let result = await PopupWidget.WaitPopup({
                    title: "Saving project...",
                    operation: this.session.saveProject(new SaveProjectParamsDto({
                        fs: fileLocation.filesystem.toDto(),  project_file_path: fileLocation.path.toDto()
                    })),
                })
                if(result instanceof Error){
                    new ErrorPopupWidget({message: result.message})
                }
                this.savedPath = fileLocation.path
                popup.destroy()
            }})
        ]})
    }
    private popupLoadProject = () => {
        const popup = new PopupWidget("Load Project", true);
        const fileLocationInput = new FileLocationInputWidget({
            parentElement: popup.element,
            filesystemChoices: ["data-proxy", "http"],
            defaultBucketName: "hbp-image-service",
            defaultPath: this.savedPath || this.defaultPath,
        })
        new Paragraph({parentElement: popup.element, children: [
            new Button({inputType: "button", text: "Load Project", parentElement: undefined, onClick: async () => {
                const fileLocation = fileLocationInput.value
                if(fileLocation === undefined){
                    new ErrorPopupWidget({message: "Missing parameters"})
                    return
                }
                let result = await PopupWidget.WaitPopup({
                    title: "Loading project...",
                    operation: this.session.loadProject(new LoadProjectParamsDto({
                        fs: fileLocation.filesystem.toDto(),  project_file_path: fileLocation.path.toDto()
                    })),
                })
                if(result instanceof Error){
                    new ErrorPopupWidget({message: result.message})
                }
                popup.destroy()
            }})
        ]})
    }
}