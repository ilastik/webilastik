import { Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Url } from "../../util/parsed_url";

export class SessionLoaderWidget{
    element: HTMLElement;
    public readonly ilastikUrlInput: HTMLInputElement;
    public readonly sessionUrlField: HTMLInputElement;
    private loadSessionButton: HTMLInputElement
    constructor({
        ilastikUrl, sessionUrl, parentElement, onUsageError, onNewSession
    }: {
        ilastikUrl: Url,
        sessionUrl?: Url,
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

        this.sessionUrlField = createInputParagraph({
            label_text: "Session url: ", inputType: "url", parentElement: form, required: true, value: sessionUrl?.toString() || ""
        })

        this.loadSessionButton = createInputParagraph({inputType: "submit", value: "Rejoin Session", parentElement: form})

        const message_p = createElement({tagName: "p", parentElement: form})

        form.addEventListener("submit", (ev) => {
            this.loadSessionButton.value = "Loading Session..."
            message_p.innerHTML = ""
            this.set_disabled(true)
            Session.load({
                ilastikUrl: Url.parse(this.ilastikUrlInput.value),
                sessionUrl: Url.parse(this.sessionUrlField.value.trim()),
                onUsageError,
            }).then(
                sessionResult => {
                    if(sessionResult instanceof Error){
                        message_p.innerHTML = sessionResult.message
                        this.set_disabled(false)
                    }else{
                        this.set_disabled(true)
                        this.sessionUrlField.value = sessionResult.sessionUrl.raw
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

    public setFields(params: {ilastikUrl: Url, sessionUrl?: Url}){
        this.ilastikUrlInput.value = params.ilastikUrl.raw
        this.sessionUrlField.value = params.sessionUrl?.raw || ""
    }
}
