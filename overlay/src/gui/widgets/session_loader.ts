import { Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Url } from "../../util/parsed_url";

export class SessionLoaderWidget{
    element: HTMLElement;
    public readonly ilastikUrlInput: HTMLInputElement;
    public readonly sessionIdField: HTMLInputElement;
    private loadSessionButton: HTMLInputElement
    constructor({
        ilastikUrl, sessionId, parentElement, onUsageError, onNewSession
    }: {
        ilastikUrl: Url,
        sessionId?: string,
        parentElement: HTMLElement,
        onUsageError: (message: string) => void,
        onNewSession: (session: Session) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSessionLoaderWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerHTML: "Rejoin Session"})

        const form = createElement({tagName: "form", parentElement: this.element})

        this.ilastikUrlInput = createInputParagraph({
            label_text: "Ilastik api URL: ", inputType: "url", parentElement: form, required: true, value: ilastikUrl.toString()
        })

        const timeoutInput = createInputParagraph({
            label_text: "Timeout (minutes): ", inputType: "number", parentElement: form, required: true, value: "5"
        })
        timeoutInput.min = "1"

        this.sessionIdField = createInputParagraph({
            label_text: "Session ID: ", inputType: "text", parentElement: form, required: true, value: sessionId?.toString() || ""
        })

        this.loadSessionButton = createInputParagraph({inputType: "submit", value: "Rejoin Session", parentElement: form})

        const message_p = createElement({tagName: "p", parentElement: form})

        form.addEventListener("submit", (ev) => {
            this.loadSessionButton.value = "Loading Session..."
            message_p.innerHTML = ""
            this.set_disabled(true)
            Session.load({
                ilastikUrl: Url.parse(this.ilastikUrlInput.value),
                sessionId: this.sessionIdField.value,
                timeout_minutes: parseInt(timeoutInput.value),
                onUsageError,
            }).then(
                sessionResult => {
                    if(sessionResult instanceof Error){
                        message_p.innerHTML = sessionResult.message
                        this.set_disabled(false)
                    }else{
                        this.set_disabled(true)
                        this.sessionIdField.value = sessionResult.sessionUrl.raw
                        this.ilastikUrlInput.value = sessionResult.ilastikUrl.raw
                        onNewSession(sessionResult)
                    }
                },
            )
            ev.preventDefault()
            return false
        })
    }

    public set_disabled(disabled: boolean){
        this.element.querySelectorAll("input").forEach(inp => {
            (inp as HTMLInputElement).disabled = disabled
        })
        if(disabled){
            this.loadSessionButton.value = "Session is running..."
        }else{
            this.loadSessionButton.value = "Rejoin Session"
        }
    }

    public setFields(params: {ilastikUrl: Url, sessionId?: string}){
        this.ilastikUrlInput.value = params.ilastikUrl.raw
        this.sessionIdField.value = params.sessionId || ""
    }
}
