import { IViewerDriver } from "../..";
import { Session } from "../../client/ilastik";
import { createInput } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { ReferencePixelClassificationWorkflowGui } from "../reference_pixel_classification_workflow";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { ErrorPopupWidget } from "./popup";
import { SessionCreatorWidget } from "./session_creator";
import { SessionLoaderWidget } from "./session_loader";

export class SessionManagerWidget{
    element: HTMLElement
    session?: Session
    workflow?: ReferencePixelClassificationWorkflowGui
    session_creator: SessionCreatorWidget;
    session_loader: SessionLoaderWidget;
    constructor({parentElement, ilastikUrl=Url.parse("https://app.ilastik.org/"), viewer_driver, workflow_container}: {
        parentElement: HTMLElement, ilastikUrl?: Url, viewer_driver: IViewerDriver, workflow_container: HTMLElement
    }){
        this.element = new CollapsableWidget({
            display_name: "Session Management",
            parentElement,
            help: [
                `Normal ilastik operation can be computationally intensive, requiring dedicated compute resources
                to be allocated to every user working with it.`,

                `This widget allows you to request a compute session where ilastik will run; Select a session duration
                and click 'Create' to create a new compute session. Eventually the compute session will be allocated,
                opening up the other workflow widgets.`,

                `You can also leave a session and rejoin it later if it is still running. To so so, just copy the session
                URL from 'Rejoin Session' below and paste it in any other browser tab that is running webilastik.`,

                `To close a session, click the 'Close Session' button. This will terminate the entire session and prevent
                your account from being charged more node-hours than you need for your work.`
            ]
        }).element;
        this.element.classList.add("ItkLauncherWidget")

        const onUnload = (event: BeforeUnloadEvent) => {
            event.preventDefault();
            return event.returnValue = "Are you sure you want to exit? Your compute session is still running.";
        };

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
                ilastikUrl,
                sessionUrl: new_session.sessionUrl,
            })
            window.addEventListener("beforeunload", onUnload);
        }
        const onUsageError = (message: string) => {
            new ErrorPopupWidget({message})
        };
        this.session_creator = new SessionCreatorWidget({parentElement: this.element, ilastikUrl, onNewSession, onUsageError})
        this.session_loader = new SessionLoaderWidget({parentElement: this.element, ilastikUrl, onNewSession, onUsageError})

        const onLeaveSession = () => {
            this.workflow?.destroy()
            close_session_btn.disabled = true
            leave_session_btn.disabled = true
            this.session_creator.set_disabled(false)
            this.session_loader.set_disabled(false)
            window.removeEventListener("beforeunload", onUnload);
        }

        const close_session_btn = createInput({
            inputType: "button",
            value: "Close Session",
            parentElement: this.element,
            onClick: async () => {
                this.session?.close()
                onLeaveSession()
                this.session_loader.setFields({
                    ilastikUrl,
                    sessionUrl: undefined,
                })
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
