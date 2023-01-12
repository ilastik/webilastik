import { Filesystem, Session } from "../../client/ilastik";
import { GetFileSystemAndPathFromUrlParamsDto, LoadProjectParamsDto, SaveProjectParamsDto } from "../../client/dto";
import { dateToSafeString } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { FileLocationInputWidget } from "./file_location_input";
import { Div, Form, Label, Paragraph } from "./widget";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";
import { TabsWidget } from "./tabs_widget";
import { DataProxyFilePicker } from "./data_proxy_file_picker";
import { LiveFsTree } from "./live_fs_tree";
import { UrlInput } from "./value_input_widget";


export class ProjectLoaderWidget{
    private readonly session: Session;
    onSuccess: () => void;

    constructor(params: {
        parentElement: HTMLElement | undefined,
        session: Session,
        onSuccess: () => void,
    }){
        this.session = params.session
        this.onSuccess = params.onSuccess

        let dataProxyFilePickerContainer = new Div({parentElement: params.parentElement})
        new DataProxyFilePicker({
            parentElement: dataProxyFilePickerContainer.element, //FIXME
            session: params.session,
            onOk: (liveFsTree: LiveFsTree) => {
                let paths = liveFsTree.getSelectedPaths()
                if(paths.length != 1){
                    new ErrorPopupWidget({message: "Please select one project file"})
                    return
                }
                this.tryLoadProject(liveFsTree.fs, paths[0])
            },
            okButtonValue: "Open",
        })

        let projectUrlInput: UrlInput;
        let loadFromUrlForm = new Form({parentElement: undefined, children: [
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({parentElement: undefined, innerText: "Project file (.ilp) URL:"}),
                projectUrlInput = new UrlInput({parentElement: undefined, required: true})
            ]}),
            new Paragraph({parentElement: undefined, children: [
                new Button({parentElement: undefined, inputType: "submit", text: "Open"})
            ]})
        ]})
        loadFromUrlForm.preventSubmitWith(async () => {
            let url =projectUrlInput.value
            if(url === undefined){
                new ErrorPopupWidget({message: "Invalid URL"})
                return
            }
            let result = await PopupWidget.WaitPopup({
                title: "Interpreting Url...",
                operation: params.session.tryGetFsAndPathFromUrl(new GetFileSystemAndPathFromUrlParamsDto({url: url.toDto()}))
            })
            if(result instanceof Error){
                new ErrorPopupWidget({message: "Could not interpret URL"})
                return
            }
            this.tryLoadProject(result.fs, result.path)
        })

        new TabsWidget({
            parentElement: params.parentElement,
            tabBodyWidgets: new Map([
                ["Data Proxy", dataProxyFilePickerContainer],
                ["Url", new Div({parentElement: undefined, children: [
                    loadFromUrlForm
                ]})],
            ])
        })
    }

    private async tryLoadProject(fs: Filesystem, path: Path){
        let result = await PopupWidget.WaitPopup({
            title: "Loading project file...",
            operation: this.session.loadProject(new LoadProjectParamsDto({
                fs: fs.toDto(),  project_file_path: path.toDto()
            }))
        })
        if(result instanceof Error){
            new ErrorPopupWidget({message: `Could not open project: ${result.message}`})
        }else{
            this.onSuccess()
        }
    }
}

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
            new Button({inputType: "button", parentElement: undefined, text: "Load Project", onClick: () => {
                let popup = new PopupWidget("Select a project file to load", true)
                new ProjectLoaderWidget({
                    parentElement: popup.element, session: params.session, onSuccess: () => popup.destroy()
                })
            }}),
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
}