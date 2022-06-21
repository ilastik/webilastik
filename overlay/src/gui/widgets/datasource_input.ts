import { DataSource, Session } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { OneShotSelectorWidget } from "./selector_widget";
import { UrlInput } from "./url_input";


export class DataSourceInput{
    public readonly element: HTMLDivElement;
    private readonly session: Session;
    private readonly urlInput: UrlInput;
    private readonly suggestionsButtonContainer: HTMLDivElement
    public readonly checkButton: HTMLInputElement;
    private readonly onChanged: ((newValue: DataSource | undefined) => void) | undefined;
    private statusMessageContainer: HTMLParagraphElement;
    private _value: DataSource | undefined;

    constructor(params: {
        parentElement: HTMLElement,
        session: Session,
        value?: DataSource,
        onChanged?: (newValue: DataSource | undefined) => void,
    }){
        this.session = params.session
        this._value = params.value
        this.onChanged = params.onChanged
        this.element = createElement({tagName: "div", parentElement: params.parentElement})

        let p = createElement({tagName: "p", parentElement: this.element, cssClasses: [CssClasses.ItkInputParagraph]})
        this.urlInput = UrlInput.createLabeled({label: "Url: ", parentElement: p})
        this.urlInput.input.addEventListener("keyup", (ev) => {
            if(ev.key === 'Enter'){
                this.checkUrl()
            }
        })
        this.urlInput.input.addEventListener("focusout", () => this.checkUrl())
        this.checkButton = createInput({inputType: "button", value: "check", parentElement: p, onClick: () => this.checkUrl})

        this.statusMessageContainer = createElement({tagName: "p", parentElement: this.element, cssClasses: [CssClasses.InfoText]})
        this.suggestionsButtonContainer = createElement({tagName: "div", parentElement: this.element})
    }

    public setSuggestions(suggestions: DataSource[] | undefined){
        this.suggestionsButtonContainer.innerHTML = ""
        if(!suggestions || suggestions.length == 0){
            return
        }
        createInput({
            inputType: "button", parentElement: this.suggestionsButtonContainer, value: "Suggestions...", onClick: () => {
                this.popupSuggestions(suggestions)
            }
        })
    }

    private async checkUrl(){
        let previousValue = this.value

        let url = this.urlInput.value
        if(url == undefined){
            if(previousValue !== undefined && this.onChanged){
                this.onChanged(undefined)
            }
            return
        }
        let datasources_result = await DataSource.getDatasourcesFromUrl({datasource_url: url, session: this.session})
        if(datasources_result instanceof Error){
            new ErrorPopupWidget({message: `Error retrieving datasources: ${datasources_result}`})
            return
        }
        if(datasources_result.length == 0){
            new ErrorPopupWidget({message: `No datasources fond with given URL: ${url}`})
            return
        }
        this.popupSuggestions(datasources_result)
    }

    protected popupSuggestions(suggestions: DataSource[]){
        let popup = new PopupWidget("Select a Data Source")
        new OneShotSelectorWidget({
            parentElement: popup.element,
            options: suggestions,
            optionRenderer: (ds) => ds.getDisplayString(),
            onOk: (ds) => {
                this.value = ds
                popup.destroy()
            },
            onCancel: () => popup.destroy(),
        })
    }

    public get value(): DataSource | undefined{
        return this._value
    }

    public set value(value: DataSource | undefined){
        this._value = value

        this.urlInput.value = undefined
        this.statusMessageContainer.innerHTML = ""

        if(value !== undefined){
            this.statusMessageContainer.innerText = `✔️ Current selection: ${value.getDisplayString()}`
        }
        if(this.onChanged){
            this.onChanged(value)
        }
    }

    public static createLabeled(params: {legend: string} & ConstructorParameters<typeof DataSourceInput>[0]): DataSourceInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new DataSourceInput({...params, parentElement: fieldset})
    }
}