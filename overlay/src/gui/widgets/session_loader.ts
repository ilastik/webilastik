import { Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";

export class SessionLoaderWidget{
    element: HTMLElement;
    public readonly url_input: HTMLInputElement;
    public readonly session_url_field: HTMLInputElement;
    constructor({
        ilastik_url, session_url, parentElement, onNewSession}: {
        ilastik_url: URL,
        session_url?: URL,
        parentElement: HTMLElement,
        onNewSession: (session: Session) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSessionLoaderWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerHTML: "Rejoin Session"})

        const form = createElement({tagName: "form", parentElement: this.element})

        this.url_input = createInputParagraph({
            label_text: "Ilastik api URL: ", inputType: "url", parentElement: form, required: true, value: ilastik_url.toString()
        })

        this.session_url_field = createInputParagraph({
            label_text: "Session url: ", inputType: "url", parentElement: form, required: true, value: session_url?.toString() || ""
        })

        const load_session_button = createInputParagraph({inputType: "submit", value: "Rejoin Session", parentElement: form})

        const message_p = createElement({tagName: "p", parentElement: form})

        form.addEventListener("submit", (ev) => {
            load_session_button.value = "Loading Session..."
            message_p.innerHTML = ""
            load_session_button.disabled = true
            Session.load({
                ilastik_url: new URL(this.url_input.value),
                session_url: new URL(this.session_url_field.value.trim()),
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

    public setFields(params: {ilastik_url: URL, session_url: URL}){
        this.url_input.value = params.session_url.toString()
        this.session_url_field.value = params.session_url.toString()
    }
}
