import { Session } from "../../client/ilastik"
import { createElement, createInput } from "../../util/misc"
import { Url } from "../../util/parsed_url"
import { SessionWidget } from "./session_widget"

export class SessionCreatorWidget extends SessionWidget{
    private readonly durationInput: HTMLInputElement
    onUsageError: (message: string) => void
    onNewSession: (session: Session) => void

    constructor(params:{
        ilastikUrl: Url,
        sessionId?: string,
        parentElement: HTMLElement,
        onUsageError: (message: string) => void,
        onNewSession: (session: Session) => void,
    }){
        super({...params, title: "Create New Compute Session", submitButtonValue: "Create Session"})
        this.onUsageError = params.onUsageError
        this.onNewSession = params.onNewSession


        createElement({tagName: "label", parentElement: this.extraFieldsContainer, innerText: "Session Duration (minutes): "})
        this.durationInput = createInput({
            inputType: "number", parentElement: this.extraFieldsContainer, required: true, value: "15", name: "itk_session_request_duration"
        })
        this.durationInput.min = "5"
        this.durationInput.max = "60"
    }

    protected async onSubmit(params: {ilastikUrl: Url, timeout_minutes: number}){
        this.logMessage("Creating session...")

        let session_result = await Session.create({
            ilastikUrl: params.ilastikUrl,
            timeout_minutes: params.timeout_minutes,
            session_duration_minutes: parseInt(this.durationInput.value),
            onProgress: (message) => this.logMessage(message),
            onUsageError: this.onUsageError,
            autoCloseOnTimeout: true,
        })
        if(session_result instanceof Error){
            this.logMessage(session_result.message)
            this.set_disabled({disabled: false})
        }else{
            this.onNewSession(session_result)
            this.set_disabled({disabled: true, buttonText: "Session is running"})
        }
    }
}
