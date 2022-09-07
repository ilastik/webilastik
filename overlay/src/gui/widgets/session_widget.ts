import { Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Url } from "../../util/parsed_url";

export abstract class SessionWidget{
    element: HTMLElement;
    public readonly form: HTMLFormElement
    public readonly ilastikUrlInput: HTMLInputElement;
    public readonly timeoutInput: HTMLInputElement;
    private submitButton: HTMLInputElement
    private messagesContainer: HTMLParagraphElement;
    messagesContainerLabel: HTMLLabelElement;
    protected readonly submitButtonValue: string;
    protected readonly extraFieldsContainer: HTMLParagraphElement;

    constructor(params: {
        ilastikUrl: Url,
        sessionId?: string,
        parentElement: HTMLElement,
        title: string,
        submitButtonValue: string,
    }){
        this.submitButtonValue = params.submitButtonValue
        this.element = createElement({tagName: "div", parentElement: params.parentElement, cssClasses: ["ItkSessionLoaderWidget"]})
        createElement({tagName: "h3", parentElement: this.element, innerText: params.title})

        this.form = createElement({tagName: "form", parentElement: this.element})

        this.ilastikUrlInput = createInputParagraph({
            label_text: "Ilastik api URL: ", inputType: "url", parentElement: this.form, required: true, value: params.ilastikUrl.toString()
        })

        this.timeoutInput = createInputParagraph({
            label_text: "Timeout (minutes): ", inputType: "number", parentElement: this.form, required: true, value: "15"
        })
        this.timeoutInput.min = "1"

        this.extraFieldsContainer = createElement({tagName: "p", parentElement: this.form})

        this.submitButton = createInputParagraph({inputType: "submit", value: this.submitButtonValue, parentElement: this.form})

        this.messagesContainerLabel = createElement({tagName: "label", parentElement: this.form, innerText: "Log:", inlineCss: {display: "none"}})
        this.messagesContainer = createElement({tagName: "p", parentElement: this.form, cssClasses: ["ItkSessionCreatorWidget_status-messages"], inlineCss: {display: "none"}})

        this.form.addEventListener("submit", (ev): false => {
            this.messagesContainer.innerHTML = "";
            this.set_disabled({disabled: true});

            const ilastikUrl = Url.parse(this.ilastikUrlInput.value)
            Session.check_login({ilastikUrl}).then(is_logged_in => {
                if(!is_logged_in){
                    this.directUserToLogin()
                }else{
                    this.onSubmit({ilastikUrl, timeout_minutes: parseInt(this.timeoutInput.value)});
                }
            })

            ev.preventDefault()
            return false
        })
    }

    protected abstract onSubmit(prams: {ilastikUrl: Url, timeout_minutes: number}): void;

    protected logMessage(message: string){
        this.messagesContainerLabel.style.display = "inline"
        this.messagesContainer.style.display = "block"

        let p = createElement({tagName: "p", parentElement: this.messagesContainer})
        createElement({tagName: "em", parentElement: p, innerText: `${new Date().toLocaleString()} ${message}`})
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight
    }

    public set_disabled(params: {disabled: boolean, buttonText?: string}){
        this.element.querySelectorAll("input").forEach(inp => {
            (inp as HTMLInputElement).disabled = params.disabled
        })
        this.submitButton.value = params.buttonText || this.submitButtonValue
    }

    public directUserToLogin(){
        let ilastikUrl = Url.parse(this.ilastikUrlInput.value)
        this.logMessage("Not looged in.")
        const login_url = ilastikUrl.joinPath("api/login_then_close").raw
        this.messagesContainer.innerHTML += `<p><a target="_blank" rel="noopener noreferrer" href="${login_url}">Login on ebrains</a> and try again.</p>`
        window.open(login_url)
        this.set_disabled({disabled: false});
    }
}
