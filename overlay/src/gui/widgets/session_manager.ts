import { IViewerDriver } from "../..";
import { HpcSiteName, Session } from "../../client/ilastik";
import { CreateComputeSessionParamsDto, GetComputeSessionStatusParamsDto } from "../../client/dto";
import { createElement, createInputParagraph, secondsToTimeDeltaString } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { ReferencePixelClassificationWorkflowGui } from "../reference_pixel_classification_workflow";
import { CollapsableWidget } from "./collapsable_applet_gui";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { SessionsPopup } from "./sessions_list_widget";
import { Label, Paragraph, Span } from "./widget";
import { Button, Select } from "./input_widget";
import { TextInput, NumberInput, UrlInput } from "./value_input_widget";

export class SessionManagerWidget{
    element: HTMLElement
    session?: Session
    workflow?: ReferencePixelClassificationWorkflowGui

    private remainingTimeIntervalID: number = 0;
    private reminaningTimeContainer: Paragraph
    private remainingTimeDisplay: TextInput
    ilastikUrlInput: UrlInput;
    timeoutInput: NumberInput;
    createSessionButton: Button<"button">;
    messagesContainerLabel: Label;
    messagesContainer: Paragraph;
    sessionIdField: TextInput;
    rejoinSessionButton: Button<"button">;
    workflowContainer: HTMLElement;
    viewerDriver: IViewerDriver;
    closeSessionButton: Button<"button">;
    leaveSessionButton: Button<"button">;
    listSessionsButton: Button<"button">;
    sessionDurationInput: NumberInput;
    private warnedUserOfImpendingClose = false
    hpcSiteInput: Select<HpcSiteName>;

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

        new Paragraph({parentElement: this.element, children: [
            new Label({parentElement: undefined, innerText: "Ilastik API URL: "}),
            this.ilastikUrlInput = new UrlInput({parentElement: undefined, required: true, value: ilastikUrl}),
        ]})

        new Paragraph({parentElement: this.element, children: [
            new Label({parentElement: undefined, innerText: "HPC site: "}),
            this.hpcSiteInput = new Select<HpcSiteName>({
                parentElement: undefined,
                popupTitle: "Select an HPC Site",
                options: hpcSiteNames,
                renderer: (site) => new Span({parentElement: undefined, innerText: site}),
            }),
            this.listSessionsButton = new Button({
                inputType: "button",
                text: "List Sessions",
                parentElement: undefined,
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
                            if(this.session && this.session.sessionUrl.equals(Url.fromDto(status.session_url))){
                                this.onLeaveSession()
                            }
                        }
                    });
                    this.listSessionsButton.disabled = false
                }
            }),
        ]})

        new Paragraph({
            parentElement: this.element,
            children: [
                new Label({parentElement: undefined, innerText: "Timeout (minutes): "}),
                this.timeoutInput = new NumberInput({parentElement: undefined, value: 15, min: 1}),
            ]
        })


        createElement({tagName: "h3", parentElement: this.element, innerText: "Create Session"})
        new Paragraph({
            parentElement: this.element,
            children: [
                new Label({parentElement: undefined, innerText: "Session Duration (minutes): "}),
                this.sessionDurationInput = new NumberInput({parentElement: undefined, value: 60, min: 5}),
            ]
        })

        new Paragraph({
            parentElement: this.element,
            children: [
                this.createSessionButton = new Button({parentElement: undefined, inputType: "button", text: "Create Session", onClick: async () => {
                    let timeoutMinutes = this.getWaitTimeout()
                    if(timeoutMinutes === undefined){
                        return
                    }
                    this.enableSessionAccquisitionControls({enabled: false})
                    let ilastikUrl = await this.ensureLoggedInAndGetIlastikUrl();
                    if(!ilastikUrl){
                        return this.enableSessionAccquisitionControls({enabled: true})
                    }
                    let sessionDurationMinutes = this.sessionDurationInput.value
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
                        rpcParams: new CreateComputeSessionParamsDto({
                            hpc_site: this.hpcSiteInput.value,
                            session_duration_minutes: sessionDurationMinutes,
                        }),
                        onProgress: (message) => this.logMessage(message),
                        onUsageError: (message) => {new ErrorPopupWidget({message: message})},
                        autoCloseOnTimeout: true,
                    })
                    this.onNewSession(sessionResult)
                }})
            ]
        })

        createElement({tagName: "h3", parentElement: this.element, innerText: "Rejoin Session"})
        new Paragraph({parentElement: this.element, children: [
            new Label({parentElement: undefined, innerText: "Session ID :"}),
            this.sessionIdField = new TextInput({parentElement: undefined, value: undefined}),
        ]})
        new Paragraph({parentElement: this.element, children: [
            this.rejoinSessionButton = new Button({
                inputType: "button",
                text: "Rejoin Session",
                parentElement: this.element,
                onClick: async () => {
                    let timeoutMinutes = this.getWaitTimeout()
                    if(timeoutMinutes === undefined){
                        return
                    }
                    let sessionId = this.sessionIdField.value
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
                        getStatusRpcParams: new GetComputeSessionStatusParamsDto({
                            compute_session_id: sessionId,
                            hpc_site: this.hpcSiteInput.value,
                        }),
                        timeout_minutes: timeoutMinutes,
                        onUsageError: (message) => this.logMessage(message),
                        onProgress: (message) => this.logMessage(message),
                        autoCloseOnTimeout: false,
                    })
                    this.onNewSession(sessionResult)
                }
            })
        ]})

        this.messagesContainerLabel = new Label({parentElement: this.element, innerText: "Log:", show: false});
        this.messagesContainer = new Paragraph({parentElement: this.element, cssClasses: ["ItkSessionCreatorWidget_status-messages"], show: false})

        new Paragraph({parentElement: this.element, children: [
            this.closeSessionButton = new Button({
                inputType: "button",
                text: "Close Session",
                parentElement: undefined,
                onClick: () => this.closeSession(),
                disabled: true,
                title: "Terminates session and any running processing",
            }),
            this.leaveSessionButton = new Button({
                inputType: "button",
                text: "Leave Session",
                parentElement: undefined,
                onClick: this.onLeaveSession,
                disabled: true,
                title: "Leaves session running on the server",
            }),
            this.reminaningTimeContainer = new Paragraph({
                parentElement: undefined,
                show: false,
                children: [
                    new Label({parentElement: undefined, innerText: " Time remaining: "}),
                    this.remainingTimeDisplay = new TextInput({parentElement: undefined, disabled: true, value: ""}),
                ]
            })
        ]});
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
        this.messagesContainerLabel.show(true)
        this.messagesContainer.show(true)


        new Paragraph({
            parentElement: this.messagesContainer,
            innerText: `${new Date().toLocaleString()} ${message}`,
        })
        this.messagesContainer.element.scrollTop = this.messagesContainer.element.scrollHeight
    }

    private getIlastikUrl(): Url | undefined{
        const url = this.ilastikUrlInput.value;
        if(url === undefined){
            new ErrorPopupWidget({message: `Bad ilastik API url`})
            return
        }
        return url
    }

    private getWaitTimeout(): number | undefined{
        const timeoutMinutes = this.timeoutInput.value
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
        let response = await Session.check_login({ilastikUrl})
        if(response instanceof Error){
            new ErrorPopupWidget({message: `Could not login: ${response.message}`})
            return
        }
        if(response.logged_in === true){
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
        this.reminaningTimeContainer.show(true)

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
        this.reminaningTimeContainer.show(false)
        this.workflow?.destroy()
        window.removeEventListener("beforeunload", this.onUnload);
        this.enableSessionDismissalControls({enabled: false})
        this.enableSessionAccquisitionControls({enabled: true})
    }
}