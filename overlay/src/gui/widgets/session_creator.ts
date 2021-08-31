import { Session } from "../../client/ilastik"
import { createElement, createInput } from "../../util/misc"
import { Url } from "../../util/parsed_url"

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
            (async () => {
                try{
                    creation_log_p.style.display = "block"
                    const ilastik_api_url = Url.parse(url_input.value)
                    let is_logged_in = await Session.check_login({ilastik_api_url})
                    if(!is_logged_in){
                        const login_url = ilastik_api_url.joinPath("login_then_close").raw
                        status_messages.innerHTML = `<p><a target="_blank" rel="noopener noreferrer" href="${login_url}">Login on ebrains</a> required.</p>`
                        window.open(login_url)
                        return
                    }
                    create_session_btn.value = "Creating Session..."
                    this.set_disabled(true)
                    status_messages.innerHTML = "";

                    let session = await Session.create({
                        ilastik_url: new URL(url_input.value),
                        timeout_s: parseInt(timeout_input.value) * 60,
                        session_duration_seconds: parseInt(duration_input.value) * 60,
                        onProgress: (message) => {
                            status_messages.innerHTML += `<p><em>${new Date().toLocaleString()}</em> ${message}</p>`
                            status_messages.scrollTop = status_messages.scrollHeight
                        }
                    })
                    onNewSession(session)
                    create_session_btn.value = "Create"
                }catch(e){
                    status_messages.innerHTML = e.message
                    this.set_disabled(false)
                }
            })()

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
