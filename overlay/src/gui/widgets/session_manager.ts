import { IViewerDriver } from "../..";
import { Session } from "../../client/ilastik";
import { createInput } from "../../util/misc";
import { ReferencePixelClassificationWorkflowGui } from "../reference_pixel_classification_workflow";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { SessionCreatorWidget } from "./session_creator";
import { SessionLoaderWidget } from "./session_loader";

export class SessionManagerWidget{
    element: HTMLElement
    session?: Session
    workflow?: ReferencePixelClassificationWorkflowGui
    session_creator: SessionCreatorWidget;
    session_loader: SessionLoaderWidget;
    constructor({parentElement, ilastik_url=new URL("https://web.ilastik.org/app"), viewer_driver, workflow_container}: {
        parentElement: HTMLElement, ilastik_url?: URL, viewer_driver: IViewerDriver, workflow_container: HTMLElement
    }){
        this.element = new CollapsableWidget({display_name: "Session Management", parentElement}).element;
        this.element.classList.add("ItkLauncherWidget")

        const onNewSession = (new_session: Session) => {
            this.session = new_session
            this.workflow?.element.parentElement?.removeChild(this.workflow.element)
            this.workflow = new ReferencePixelClassificationWorkflowGui({
                session: new_session, parentElement: workflow_container, viewer_driver
            })
            close_session_btn.disabled = false
            leave_session_btn.disabled = false
            this.session_creator.set_disabled(true)
            this.session_loader.set_disabled(true)
            this.session_loader.setFields({
                ilastik_url: new URL(new_session.ilastik_url),
                session_url: new URL(new_session.session_url),
                token: new_session.token
            })
        }
        this.session_creator = new SessionCreatorWidget({parentElement: this.element, ilastik_url, onNewSession})
        this.session_loader = new SessionLoaderWidget({parentElement: this.element, ilastik_url, onNewSession})

        const onLeaveSession = () => {
            this.workflow?.destroy()
            close_session_btn.disabled = true
            leave_session_btn.disabled = true
            this.session_creator.set_disabled(false)
            this.session_loader.set_disabled(false)
        }

        const close_session_btn = createInput({
            inputType: "button",
            value: "Close Session",
            parentElement: this.element,
            onClick: async () => {
                this.session?.close()
                onLeaveSession()
            },
            inlineCss: {
                marginTop: "10px",
            },
            disabled: true,
        })
        close_session_btn.title = "Terminates session and any running processing"


        const leave_session_btn = createInput({
            inputType: "button",
            value: "Leave Session",
            parentElement: this.element,
            onClick: onLeaveSession,
            inlineCss: {
                marginTop: "10px",
            },
            disabled: true,
        })
        leave_session_btn.title = "Leaves session running on the server"
    }
}
