import { Session } from "../../client/ilastik"
import { createElement, createInputParagraph } from "../../util/misc"
import { Url } from "../../util/parsed_url"

export class SessionCreatorWidget{
    element: HTMLElement
    constructor({parentElement, ilastikUrl, onNewSession}:{
        parentElement: HTMLElement,
        ilastikUrl: Url,
        onNewSession: (new_session: Session) => void,
    }){
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkSessionCreatorWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerHTML: "Create New Session"})

        const form = createElement({tagName: "form", parentElement: this.element})

        const ilastikUrlInput = createInputParagraph({
            label_text: "Ilastik URL: ",inputType: "url", parentElement: form, required: true, value: ilastikUrl.toString(), name: "itk_api_url"
        })

        const timeout_input = createInputParagraph({
            label_text: "Timeout (minutes): ", inputType: "number", parentElement: form, required: true, value: "5", name: "itk_session_request_timeout"
        })
        timeout_input.min = "1"

        const duration_input = createInputParagraph({
            label_text: "Session Duration (minutes): ", inputType: "number", parentElement: form, required: true, value: "5", name: "itk_session_request_duration"
        })
        duration_input.min = "5"

        const create_session_btn = createInputParagraph({inputType: "submit", value: "Create", parentElement: form})

        const creation_log_p = createElement({tagName: "p", parentElement: form, inlineCss: {display: "none"}})
        createElement({tagName: "label", innerHTML: "Creation Log: ", parentElement: creation_log_p})
        const status_messages = createElement({tagName: "div", parentElement: creation_log_p, cssClasses: ["ItkSessionCreatorWidget_status-messages"]})

        form.addEventListener("submit", (ev) => {
            (async () => {
                try{
                    creation_log_p.style.display = "block"
                    const ilastikUrl = Url.parse(ilastikUrlInput.value)
                    let is_logged_in = await Session.check_login({ilastikUrl})
                    if(!is_logged_in){
                        const login_url = ilastikUrl.joinPath("login_then_close").raw
                        status_messages.innerHTML = `<p><a target="_blank" rel="noopener noreferrer" href="${login_url}">Login on ebrains</a> required.</p>`
                        window.open(login_url)
                        return
                    }
                    create_session_btn.value = "Creating Session..."
                    this.set_disabled(true)
                    status_messages.innerHTML = "";

                    let session = await Session.create({
                        ilastikUrl: Url.parse(ilastikUrlInput.value),
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
