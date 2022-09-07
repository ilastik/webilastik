import { Session } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { SessionWidget } from "./session_widget";

export class SessionLoaderWidget extends SessionWidget{
    public readonly sessionIdField: HTMLInputElement;
    private readonly onUsageError: (message: string) => void;
    private readonly onNewSession: (session: Session) => void;

    constructor(params: {
        ilastikUrl: Url,
        sessionId?: string,
        parentElement: HTMLElement,
        onUsageError: (message: string) => void,
        onNewSession: (session: Session) => void,
    }){
        super({...params, title: "Rejoin Session", submitButtonValue: "Rejoin Session"})
        this.onUsageError = params.onUsageError
        this.onNewSession = params.onNewSession

        createElement({tagName: "label", parentElement: this.extraFieldsContainer, innerText: "Session ID: "})
        this.sessionIdField = createInput({
            inputType: "text",
            parentElement: this.extraFieldsContainer,
            required: true,
            value: params.sessionId?.toString() || "",
        })
    }

    protected async onSubmit(params: {ilastikUrl: Url, timeout_minutes: number}){
        this.logMessage("Joining session....")
        let sessionResult = await Session.load({
            ilastikUrl: params.ilastikUrl,
            sessionId: this.sessionIdField.value,
            timeout_minutes: params.timeout_minutes,
            onUsageError: this.onUsageError,
            onProgress: (message) => this.logMessage(message),
            autoCloseOnTimeout: false,
        })

        if(sessionResult instanceof Error){
            this.logMessage(sessionResult.message)
            this.set_disabled({disabled: false, buttonText: "Rejoin Session"})
        }else{
            this.set_disabled({disabled: true, buttonText: "Session is running..."})
            this.sessionIdField.value = sessionResult.sessionUrl.raw
            this.ilastikUrlInput.value = sessionResult.ilastikUrl.raw
            this.onNewSession(sessionResult)
        }
    }

    public setFields(params: {ilastikUrl: Url, sessionId?: string}){
        this.ilastikUrlInput.value = params.ilastikUrl.raw
        this.sessionIdField.value = params.sessionId || ""
    }
}
