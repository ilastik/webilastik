import { Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Url } from "../../util/parsed_url";

export class SessionLoaderWidget{
    element: HTMLElement;
    public readonly ilastikUrlInput: HTMLInputElement;
    public readonly sessionIdField: HTMLInputElement;
    private loadSessionButton: HTMLInputElement
    private messagesContainer: HTMLParagraphElement;
    messagesContainerLabel: HTMLLabelElement;

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

        this.messagesContainerLabel = createElement({tagName: "label", parentElement: form, innerText: "Session joining log:", inlineCss: {display: "none"}})
        this.messagesContainer = createElement({tagName: "p", parentElement: form, cssClasses: ["ItkSessionCreatorWidget_status-messages"], inlineCss: {display: "none"}})

        form.addEventListener("submit", (ev): false => {
            this.messagesContainer.innerHTML = "";
            this.set_disabled({disabled: true, buttonText: "Loading Session..."});

            (async () => {
                const ilastikUrl = Url.parse(this.ilastikUrlInput.value)
                let is_logged_in = await Session.check_login({ilastikUrl})
                if(!is_logged_in){
                    this.logMessage("Not looged in.")
                    const login_url = ilastikUrl.joinPath("api/login_then_close").raw
                    this.messagesContainer.innerHTML += `<p><a target="_blank" rel="noopener noreferrer" href="${login_url}">Login on ebrains</a> and try again.</p>`
                    window.open(login_url)
                    this.set_disabled({disabled: false, buttonText: "Rejoin Session"});
                    return
                }

                let sessionResult = await Session.load({
                    ilastikUrl,
                    sessionId: this.sessionIdField.value,
                    timeout_minutes: parseInt(timeoutInput.value),
                    onUsageError,
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
                    onNewSession(sessionResult)
                }
            })()

            ev.preventDefault()
            return false
        })
    }

    private logMessage(message: string){
        this.messagesContainerLabel.style.display = "inline"
        this.messagesContainer.style.display = "block"

        let p = createElement({tagName: "p", parentElement: this.messagesContainer})
        createElement({tagName: "em", parentElement: p, innerText: `${new Date().toLocaleString()} ${message}`})
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight
    }

    public set_disabled(params: {disabled: boolean, buttonText: string}){
        this.element.querySelectorAll("input").forEach(inp => {
            (inp as HTMLInputElement).disabled = params.disabled
        })
        this.loadSessionButton.value = params.buttonText
    }

    public setFields(params: {ilastikUrl: Url, sessionId?: string}){
        this.ilastikUrlInput.value = params.ilastikUrl.raw
        this.sessionIdField.value = params.sessionId || ""
    }
}
