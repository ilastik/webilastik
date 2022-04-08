import { DataSource, Session } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { ErrorPopupWidget } from "./popup";
import { OneShotSelectorWidget } from "./selector_widget";
import { UrlInput } from "./url_input";


export class DataSourceInput{
    public readonly element: HTMLDivElement;
    private readonly session: Session;
    private readonly urlInput: UrlInput;
    private readonly suggestionsContainer: HTMLDivElement
    public readonly checkButton: HTMLInputElement;
    private readonly onChanged: ((newValue: DataSource | undefined) => void) | undefined;
    private statusMessageContainer: HTMLParagraphElement;
    private _value: DataSource | undefined;

    constructor(params: {
        parentElement: HTMLElement, session: Session, value?: DataSource, onChanged?: (newValue: DataSource | undefined) => void
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
        this.suggestionsContainer = createElement({tagName: "div", parentElement: this.element})
    }

    private async checkUrl(){
        let previousValue = this.value

        this.suggestionsContainer.innerHTML = ""

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
        new OneShotSelectorWidget({
            parentElement: this.suggestionsContainer,
            options: datasources_result,
            optionRenderer: (ds: DataSource) => ds.getDisplayString(),
            onOk: (ds: DataSource) => {this.value = ds},
        })
    }

    public get value(): DataSource | undefined{
        return this._value
    }

    public set value(value: DataSource | undefined){
        this._value = value

        this.urlInput.value = undefined
        this.statusMessageContainer.innerHTML = ""
        this.suggestionsContainer.innerHTML = ""

        if(value !== undefined){
            this.statusMessageContainer.innerText = `Current selection: ${value.getDisplayString()}`
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