import { IViewerDriver } from "../..";
import { HpcSiteName, Session } from "../../client/ilastik";
import { createElement, createInput, createInputParagraph, secondsToTimeDeltaString } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { ReferencePixelClassificationWorkflowGui } from "../reference_pixel_classification_workflow";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { PopupSelect } from "./selector_widget";
import { SessionsPopup } from "./sessions_list_widget";

export class SessionManagerWidget{
    element: HTMLElement
    session?: Session
    workflow?: ReferencePixelClassificationWorkflowGui

    private remainingTimeIntervalID: number = 0;
    private reminaningTimeContainer: HTMLParagraphElement
    private remainingTimeDisplay: HTMLInputElement
    ilastikUrlInput: HTMLInputElement;
    timeoutInput: HTMLInputElement;
    createSessionButton: HTMLInputElement;
    messagesContainerLabel: HTMLLabelElement;
    messagesContainer: HTMLParagraphElement;
    sessionIdField: HTMLInputElement;
    rejoinSessionButton: HTMLInputElement;
    workflowContainer: HTMLElement;
    viewerDriver: IViewerDriver;
    closeSessionButton: HTMLInputElement;
    leaveSessionButton: HTMLInputElement;
    listSessionsButton: HTMLInputElement;
    sessionDurationInput: HTMLInputElement;
    private warnedUserOfImpendingClose = false
    hpcSiteInput: PopupSelect<HpcSiteName>;

    constructor({parentElement, ilastikUrl, viewer_driver, workflow_container, hpcSiteNames}: {
        parentElement: HTMLElement, ilastikUrl: Url, viewer_driver: IViewerDriver, workflow_container: HTMLElement, hpcSiteNames: Array<HpcSiteName>
    }){
        this.workflowContainer = workflow_container
        this.viewerDriver = viewer_driver
        this.element = new CollapsableWidget({
            display_name: "Session Management",
            parentElement,
            open: true,
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


        this.ilastikUrlInput = createInputParagraph({
            label_text: "Ilastik api URL: ", inputType: "url", parentElement: this.element, required: true, value: ilastikUrl.toString()
        })

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: p, innerText: "HPC site: "})
        this.hpcSiteInput = new PopupSelect<HpcSiteName>({
            popupTitle: "Select an HPC Site",
            parentElement: p,
            options: hpcSiteNames,
            optionRenderer: (args) => createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option}),
        })
        this.listSessionsButton = createInput({
            inputType: "button",
            value: "List Sessions",
            parentElement: p,
            inlineCss: {marginTop: "10px"},
            onClick: async () => {
                this.listSessionsButton.disabled = true
                let ilastikUrl = await this.ensureLoggedInAndGetIlastikUrl();
                if(!ilastikUrl){
                    this.listSessionsButton.disabled = false
                    return
                }
                await SessionsPopup.create({
                    ilastikUrl,
                    hpc_site: this.hpcSiteInput.value,
                    onSessionClosed: (status) => {
                        if(this.session && this.session.sessionUrl.equals(status.session_url)){
                            this.onLeaveSession()
                        }
                    }
                });
                this.listSessionsButton.disabled = false
            }
        })

        this.timeoutInput = createInputParagraph({
            label_text: "Timeout (minutes): ", inputType: "number", parentElement: this.element, required: true, value: "15"
        })
        this.timeoutInput.min = "1"


        createElement({tagName: "h3", parentElement: this.element, innerText: "Create Session"})
        this.sessionDurationInput = createInputParagraph({inputType: "number", parentElement: this.element, label_text: "Session Duration (minutes): ", value: "60"})
        this.sessionDurationInput.min = "5"
        this.createSessionButton = createInputParagraph({
            inputType: "button",
            value: "Create Session",
            parentElement: this.element,
            onClick: async () => {
                let timeoutMinutes = this.getWaitTimeout()
                if(timeoutMinutes === undefined){
                    return
                }
                this.enableSessionAccquisitionControls({enabled: false})
                let ilastikUrl = await this.ensureLoggedInAndGetIlastikUrl();
                if(!ilastikUrl){
                    return this.enableSessionAccquisitionControls({enabled: true})
                }
                let sessionDurationMinutes = parseInt(this.sessionDurationInput.value)
                if(Number.isNaN(sessionDurationMinutes)){
                    new ErrorPopupWidget({message: `Bad session duration: ${this.sessionDurationInput.value}`})
                    return
                }
                this.logMessage("Creating session....")
                this.enableSessionAccquisitionControls({enabled: false})
                this.sessionIdField.value = ""
                let sessionResult = await Session.create({
                    ilastikUrl,
                    timeout_minutes: timeoutMinutes,
                    session_duration_minutes: sessionDurationMinutes,
                    onProgress: (message) => this.logMessage(message),
                    onUsageError: (message) => this.logMessage(message),
                    autoCloseOnTimeout: true,
                    hpc_site: this.hpcSiteInput.value,
                })
                this.onNewSession(sessionResult)
            }
        })


        createElement({tagName: "h3", parentElement: this.element, innerText: "Rejoin Session"})
        this.sessionIdField = createInputParagraph({inputType: "text", parentElement: this.element, label_text: "Session ID: "})
        this.rejoinSessionButton = createInputParagraph({
            inputType: "button",
            value: "Rejoin Session",
            parentElement: this.element,
            onClick: async () => {
                let timeoutMinutes = this.getWaitTimeout()
                if(timeoutMinutes === undefined){
                    return
                }
                let sessionId = this.sessionIdField.value.trim()
                if(!sessionId){
                    new ErrorPopupWidget({message: "Bad session ID"})
                    return
                }
                this.enableSessionAccquisitionControls({enabled: false})
                let ilastikUrl = await this.ensureLoggedInAndGetIlastikUrl();
                if(!ilastikUrl){
                    return this.enableSessionAccquisitionControls({enabled: true})
                }
                this.logMessage("Joining session....")
                let sessionResult = await Session.load({
                    ilastikUrl,
                    sessionId,
                    timeout_minutes: timeoutMinutes,
                    onUsageError: (message) => this.logMessage(message),
                    onProgress: (message) => this.logMessage(message),
                    autoCloseOnTimeout: false,
                    hpc_site: this.hpcSiteInput.value,
                })
                this.onNewSession(sessionResult)
            }
        })


        this.messagesContainerLabel = createElement({tagName: "label", parentElement: this.element, innerText: "Log:", inlineCss: {display: "none"}})
        this.messagesContainer = createElement({tagName: "p", parentElement: this.element, cssClasses: ["ItkSessionCreatorWidget_status-messages"], inlineCss: {display: "none"}})


        this.closeSessionButton = createInput({
            inputType: "button",
            value: "Close Session",
            parentElement: this.element,
            onClick: () => this.closeSession(),
            inlineCss: {marginTop: "10px"},
            disabled: true,
        })
        this.closeSessionButton.title = "Terminates session and any running processing"


        this.leaveSessionButton = createInput({
            inputType: "button",
            value: "Leave Session",
            parentElement: this.element,
            onClick: this.onLeaveSession,
            inlineCss: {marginTop: "10px"},
            disabled: true,
        })
        this.leaveSessionButton.title = "Leaves session running on the server"

        this.reminaningTimeContainer = createElement({tagName: "p", parentElement: this.element, inlineCss: {display: "none"}})
        createElement({tagName: "label", parentElement: this.reminaningTimeContainer, innerText: " Time remaining: "})
        this.remainingTimeDisplay = createInput({inputType: "text", parentElement: this.reminaningTimeContainer, disabled: true, value: ""})
    }

    private closeSession = () => {
        this.logMessage(`Closing session ${this.session?.sessionId}`)
        this.session?.terminate()
        this.session = undefined
        this.onLeaveSession()
        this.sessionIdField.value = ""
    }

    private enableSessionAccquisitionControls(params: {enabled: boolean}){
        this.ilastikUrlInput.disabled = !params.enabled
        this.timeoutInput.disabled = !params.enabled

        this.sessionDurationInput.disabled = !params.enabled
        this.createSessionButton.disabled = !params.enabled

        this.sessionIdField.disabled = !params.enabled
        this.rejoinSessionButton.disabled = !params.enabled
    }

    private enableSessionDismissalControls(params: {enabled: boolean}){
        this.closeSessionButton.disabled = !params.enabled
        this.leaveSessionButton.disabled = !params.enabled
    }

    private logMessage = (message: string) => {
        this.messagesContainerLabel.style.display = "inline"
        this.messagesContainer.style.display = "block"

        let p = createElement({tagName: "p", parentElement: this.messagesContainer})
        createElement({tagName: "em", parentElement: p, innerText: `${new Date().toLocaleString()} ${message}`})
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight
    }

    private getIlastikUrl(): Url | undefined{
        try{
            return Url.parse(this.ilastikUrlInput.value)
        }catch{
            new ErrorPopupWidget({message: `Could not parse ilastik url: ${this.ilastikUrlInput.value}`})
            return
        }
    }

    private getWaitTimeout(): number | undefined{
        const timeoutMinutes = parseInt(this.timeoutInput.value)
        if(Number.isNaN(timeoutMinutes)){
            new ErrorPopupWidget({message: `Bad timeout value: ${this.timeoutInput.value}`})
            return
        }
        return timeoutMinutes
    }

    private async ensureLoggedInAndGetIlastikUrl(): Promise<Url | undefined>{
        let ilastikUrl = this.getIlastikUrl()
        if(ilastikUrl === undefined){
            return undefined
        }
        let logInResult = await Session.check_login({ilastikUrl})
        if(logInResult instanceof Error){
            new ErrorPopupWidget({message: `Could not login: ${logInResult.message}`})
            return
        }
        if(logInResult === true){
            return ilastikUrl
        }

        let popup = new PopupWidget("Not logged in")
        const loginUrl = ilastikUrl.joinPath("api/login_then_close")
        let loginLink = createElement({
            tagName: "a",
            parentElement: createElement({tagName: "p", parentElement: popup.element}),
            innerHTML: "Login on ebrains and try again.",
            onClick: () => popup.destroy()
        })
        loginLink.target = "_blank"
        loginLink.rel = "noopener noreferrer"
        loginLink.href = loginUrl.raw

        createInputParagraph({inputType: "button", parentElement: popup.element, value: "close", onClick: () => {
            popup.destroy()
        }})

        window.open(loginUrl.raw)
        return undefined
    }

    private onNewSession(sessionResult: Session | Error){
        if(sessionResult instanceof Error){
            this.logMessage(sessionResult.message)
            this.enableSessionAccquisitionControls({enabled: true})
            return
        }
        this.sessionIdField.value = sessionResult.sessionUrl.raw

        this.enableSessionAccquisitionControls({enabled: false})
        this.session = sessionResult
        this.workflow?.element.parentElement?.removeChild(this.workflow.element)
        this.workflow = new ReferencePixelClassificationWorkflowGui({
            session: sessionResult, parentElement: this.workflowContainer, viewer_driver: this.viewerDriver
        })
        this.sessionIdField.value = sessionResult.sessionId
        this.reminaningTimeContainer.style.display = "block"

        this.warnedUserOfImpendingClose = false
        this.remainingTimeIntervalID = window.setInterval(() => {
            if(this.session === undefined){
                window.clearInterval(this.remainingTimeIntervalID)
                return
            }
            const startTime = this.session.startTime
            if(startTime === undefined){
                this.remainingTimeDisplay.value = "Not started yet"
                return
            }
            const ellapsedTimeMs = new Date().getTime() - startTime.getTime()
            const remainingTimeSec = (this.session.timeLimitMinutes * 60 - ellapsedTimeMs / 1000)
            this.remainingTimeDisplay.value = secondsToTimeDeltaString(Math.floor(remainingTimeSec))
            if(!this.warnedUserOfImpendingClose && remainingTimeSec < 3 * 60){
                this.warnedUserOfImpendingClose = true
                PopupWidget.OkPopup({title: "Session is about to close", paragraphs: ["You should save your project"]})
            }
            if(remainingTimeSec <= 0){
                this.closeSession()
            }
        }, 1000);
        window.addEventListener("beforeunload", this.onUnload);
        this.enableSessionDismissalControls({enabled: true})
    }

    private onUnload = (event: BeforeUnloadEvent) => {
        event.preventDefault();
        return event.returnValue = "Are you sure you want to exit? Your compute session is still running.";
    };

    private onLeaveSession = () => {
        this.session?.closeWebsocket()
        this.session = undefined
        window.clearInterval(this.remainingTimeIntervalID)
        this.reminaningTimeContainer.style.display = "none"
        this.workflow?.destroy()
        window.removeEventListener("beforeunload", this.onUnload);
        this.enableSessionDismissalControls({enabled: false})
        this.enableSessionAccquisitionControls({enabled: true})
    }
}