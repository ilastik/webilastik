import { Session } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";

export class SessionLoaderWidget{
    element: HTMLElement;
    public readonly url_input: HTMLInputElement;
    public readonly session_url_field: HTMLInputElement;
    public readonly session_token_field: HTMLInputElement;
    constructor({
        ilastik_url, session_url, token="", parentElement, onNewSession}: {
        ilastik_url: URL,
        session_url?: URL,
        token?: string,
        parentElement: HTMLElement,
        onNewSession: (session: Session) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSessionLoaderWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerHTML: "Rejoin Session"})

        const form = createElement({tagName: "form", parentElement: this.element})
        let p: HTMLElement;

        p = createElement({tagName: "p", parentElement: form})
        createElement({tagName: "label", innerHTML: "Ilastik api URL: ", parentElement: p})
        this.url_input = createInput({inputType: "url", parentElement: p, required: true, value: ilastik_url.toString()})

        p = createElement({tagName: "p", parentElement: form})
        createElement({tagName: "label", parentElement: p, innerHTML: "Session url: "})
        this.session_url_field = createInput({
            inputType: "url", parentElement: p, required: true, value: session_url?.toString() || ""
        })

        p = createElement({tagName: "p", parentElement: form})
        createElement({tagName: "label", parentElement: p, innerHTML: "Session token: "})
        this.session_token_field = createInput({inputType: "text", parentElement: p, required: true, value: token})

        p = createElement({tagName: "p", parentElement: form})
        const load_session_button = createInput({inputType: "submit", value: "Rejoin Session", parentElement: p})

        const message_p = createElement({tagName: "p", parentElement: form})

        form.addEventListener("submit", (ev) => {
            load_session_button.value = "Loading Session..."
            message_p.innerHTML = ""
            load_session_button.disabled = true
            Session.load({
                ilastik_url: new URL(this.url_input.value),
                session_url: new URL(this.session_url_field.value.trim()),
                token: this.session_token_field.value.trim(),
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

    public setFields(params: {ilastik_url: URL, session_url: URL, token: string}){
        this.url_input.value = params.session_url.toString()
        this.session_url_field.value = params.session_url.toString()
        this.session_token_field.value = params.token
    }
}
