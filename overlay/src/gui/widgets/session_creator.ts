import { Session } from "../../client/ilastik"
import { createElement, createInput } from "../../util/misc"

export class SessionCreatorWidget{
    element: HTMLElement
    constructor({parentElement, ilastik_url, onNewSession}:{
        parentElement: HTMLElement,
        ilastik_url: URL,
        onNewSession: (new_session: Session) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSessionCreatorWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerHTML: "Create New Session"})

        const form = createElement({tagName: "form", parentElement: this.element})

        let p = createElement({tagName: "p", parentElement: form})
        createElement({tagName: "label", innerHTML: "Ilastik api URL: ", parentElement: p})
        const url_input = createInput({inputType: "url", parentElement: p, required: true, value: ilastik_url.toString(), name: "itk_api_url"})

        p = createElement({tagName: "p", parentElement: form})
        createElement({tagName: "label", innerHTML: "Timeout (minutes): ", parentElement: p})
        const timeout_input = createInput({inputType: "number", parentElement: p, required: true, value: "5", name: "itk_session_request_timeout"})
        timeout_input.min = "1"

        p = createElement({tagName: "p", parentElement: form})
        createElement({tagName: "label", innerHTML: "Session Duration (minutes): ", parentElement: p})
        const duration_input = createInput({inputType: "number", parentElement: p, required: true, value: "5", name: "itk_session_request_duration"})
        duration_input.min = "5"

        p = createElement({tagName: "p", parentElement: form})
        const create_session_btn = createInput({inputType: "submit", value: "Create", parentElement: p})

        const creation_log_p = createElement({tagName: "p", parentElement: form, inlineCss: {display: "none"}})
        createElement({tagName: "label", innerHTML: "Creation Log: ", parentElement: creation_log_p})
        const status_messages = createElement({tagName: "div", parentElement: creation_log_p, cssClasses: ["ItkSessionCreatorWidget_status-messages"]})

        form.addEventListener("submit", (ev) => {
            creation_log_p.style.display = "block"
            create_session_btn.value = "Creating Session..."
            this.set_disabled(true)
            status_messages.innerHTML = ""
            Session.create({
                ilastik_url: new URL(url_input.value),
                timeout_s: parseInt(timeout_input.value) * 60,
                session_duration_seconds: parseInt(duration_input.value) * 60,
                onProgress: (message) => {
                    status_messages.innerHTML += `<p><em>${new Date().toLocaleString()}</em> ${message}</p>`
                    status_messages.scrollTop = status_messages.scrollHeight
                }
            }).then(
                session => onNewSession(session),
                failure => {
                    status_messages.innerHTML = failure.message
                    this.set_disabled(false)
                }
            ).then(_ => {
                create_session_btn.value = "Create"
            })
            //don't submit synchronously
            ev.preventDefault()
            return false
        })

    }

    public set_disabled(disabled: boolean){
        this.element.querySelectorAll("input").forEach(inp => {
            (inp as HTMLInputElement).disabled = disabled
        })
    }
}
