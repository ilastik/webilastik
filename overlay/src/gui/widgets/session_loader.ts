import { Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Url } from "../../util/parsed_url";

export class SessionLoaderWidget{
    element: HTMLElement;
    public readonly url_input: HTMLInputElement;
    public readonly sessionUrlField: HTMLInputElement;
    constructor({
        ilastikUrl, sessionUrl, parentElement, onNewSession}: {
        ilastikUrl: Url,
        sessionUrl?: Url,
        parentElement: HTMLElement,
        onNewSession: (session: Session) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSessionLoaderWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerHTML: "Rejoin Session"})

        const form = createElement({tagName: "form", parentElement: this.element})

        this.url_input = createInputParagraph({
            label_text: "Ilastik api URL: ", inputType: "url", parentElement: form, required: true, value: ilastikUrl.toString()
        })

        this.sessionUrlField = createInputParagraph({
            label_text: "Session url: ", inputType: "url", parentElement: form, required: true, value: sessionUrl?.toString() || ""
        })

        const load_session_button = createInputParagraph({inputType: "submit", value: "Rejoin Session", parentElement: form})

        const message_p = createElement({tagName: "p", parentElement: form})

        form.addEventListener("submit", (ev) => {
            load_session_button.value = "Loading Session..."
            message_p.innerHTML = ""
            load_session_button.disabled = true
            Session.load({
                ilastikUrl: Url.parse(this.url_input.value),
                sessionUrl: Url.parse(this.sessionUrlField.value.trim()),
            }).then(
                session => onNewSession(session),
                failure => {message_p.innerHTML = failure.message},
            ).then(_ => {
                load_session_button.value = "Rejoin Session"
                load_session_button.disabled = false
            })
            ev.preventDefault()
            return false
        })
    }

    public set_disabled(disabled: boolean){
        this.element.querySelectorAll("input").forEach(inp => {
            (inp as HTMLInputElement).disabled = disabled
        })
    }

    public setFields(params: {ilastikUrl: Url, sessionUrl: Url}){
        this.url_input.value = params.sessionUrl.raw
        this.sessionUrlField.value = params.sessionUrl.raw
    }
}
