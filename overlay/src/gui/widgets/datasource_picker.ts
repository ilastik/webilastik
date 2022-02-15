import { Applet } from "../../client/applets/applet";
import { DataSource, Session } from "../../client/ilastik";
import { createElement, createInput, createInputParagraph } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { ensureJsonArray, ensureJsonObject, ensureJsonString, ensureOptional, JsonValue } from "../../util/serialization";
import { CssClasses } from "../css_classes";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { OneShotSelectorWidget, SelectorWidget } from "./selector_widget";

type State = {
    datasource_url?: string,
    datasource_choices?: Array<DataSource>,
    datasource?: DataSource,
    error_message?: string,
    suggested_urls: Array<Url>,
}

export class DataSourcePicker extends Applet<State>{
    public readonly element: HTMLDivElement;
    private readonly datasourceUrlInput: HTMLInputElement;
    private state: State = {suggested_urls: []}
    private readonly feedbackContainer: HTMLParagraphElement;
    private readonly suggestionsContainer: HTMLDivElement
    public readonly checkButton: HTMLInputElement;
    useDatasetFromTrainingButton: HTMLInputElement;

    constructor(params: {name: string, parentElement: HTMLElement, session: Session}){
        super({
            name: params.name,
            session: params.session,
            deserializer: (value: JsonValue) => {
                const valueObject = ensureJsonObject(value)
                return {
                    datasource_url: ensureOptional(ensureJsonString, valueObject.datasource_url),
                    datasource_choices: ensureOptional(
                        raw => ensureJsonArray(raw).map(ds => DataSource.fromJsonValue(ds)),
                        valueObject.datasource_choices,
                    ),
                    datasource: ensureOptional(DataSource.fromJsonValue, valueObject.datasource),
                    error_message: ensureOptional(ensureJsonString, valueObject.error_message),
                    suggested_urls: ensureJsonArray(valueObject["suggested_urls"]).map(raw_url => Url.parse(ensureJsonString(raw_url)))
                }
            },
            onNewState: (state: State) => this.onNewState(state),
        })
        this.element = createElement({tagName: "div", parentElement: params.parentElement})
        let p = createElement({tagName: "p", parentElement: this.element, cssClasses: [CssClasses.ItkInputParagraph]})
        createElement({tagName: "label", parentElement: p, innerHTML: "Input Dataset Url: "})
        this.datasourceUrlInput = createInput({inputType: "url", parentElement: p})
        const checkUrl = (ev: Event): false => {
            this.doRPC("set_url", {url: this.datasourceUrlInput.value})
            ev.preventDefault()
            return false
        }
        this.datasourceUrlInput.addEventListener("keyup", (ev) => {
            if(ev.key === 'Enter'){
                checkUrl(ev)
            }
        })
        this.datasourceUrlInput.addEventListener("focusout", checkUrl)
        this.checkButton = createInput({inputType: "button", value: "check", parentElement: p, onClick: checkUrl})

        this.feedbackContainer = createElement({tagName: "p", parentElement: this.element})

        this.suggestionsContainer = createElement({tagName: "div", parentElement: this.element})
        this.useDatasetFromTrainingButton = createInputParagraph({inputType: "button", parentElement: this.suggestionsContainer, value: "Use dataset from training...", onClick: () => {
            if(this.state.suggested_urls.length == 0){
                new ErrorPopupWidget({message: "No suggestions."})
                return
            }
            this.useDatasetFromTrainingButton.disabled = true
            let popup = new PopupWidget("Input suggestions")
            new OneShotSelectorWidget({
                parentElement: popup.element,
                options: this.state.suggested_urls,
                optionRenderer: (url) => url.raw,
                onOk: (url) => {
                    this.doRPC("set_url", {url: url.raw})
                    this.useDatasetFromTrainingButton.disabled = false
                    popup.destroy()
                },
                onCancel: () => {
                    this.useDatasetFromTrainingButton.disabled = false
                    popup.destroy()
                },
            })
        }})


    }

    private onNewState(state: State): void{
        this.state = state
        this.datasourceUrlInput.value = state.datasource_url || ""
        this.feedbackContainer.innerHTML = ""
        if(state.datasource !== undefined){
            createElement({
                tagName: "span",
                parentElement: this.feedbackContainer,
                innerHTML: `Selected: ${state.datasource.getDisplayString()}`,
                cssClasses: [CssClasses.SuccessText]
            })
        }else{
            createElement({
                tagName: "span",
                parentElement: this.feedbackContainer,
                innerHTML: state.error_message || "No selection",
                cssClasses: [CssClasses.ErrorText]
            })
        }
        if(state.datasource_choices !== undefined){
            createElement({tagName: "p", parentElement: this.feedbackContainer, innerHTML: "Select a resolution:"})
            new SelectorWidget<DataSource>({
                parentElement: this.feedbackContainer,
                options: state.datasource_choices,
                optionRenderer: (datasource) => datasource.getDisplayString(),
                initial_selection: state.datasource,
                comparator: (ds1, ds2) => ds1.equals(ds2),
                onSelection: (_, datasource_index: number) => {
                    this.doRPC("pick_datasource", {datasource_index})
                },
            })
        }
    }

    public getDatasource(): DataSource | undefined{
        return this.state.datasource
    }
}