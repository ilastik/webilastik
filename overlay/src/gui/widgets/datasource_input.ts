import { FsDataSource, Session } from "../../client/ilastik";
import { GetDatasourcesFromUrlParamsDto } from "../../client/dto";
import { createElement } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { ErrorPopupWidget, InputPopupWidget } from "./popup";
import { SelectorWidget } from "./selector_widget";
import { UrlInput } from "./value_input_widget";
import { Label, Paragraph } from "./widget";
import { Button } from "./input_widget";


export class DataSourceInput{
    public readonly element: HTMLDivElement;
    private readonly session: Session;
    private readonly urlInput: UrlInput;
    public readonly checkButton: Button<"button">;
    private readonly onChanged: ((newValue: FsDataSource | undefined) => void) | undefined;
    private statusMessageContainer: HTMLParagraphElement;
    private _value: FsDataSource | undefined;

    constructor(params: {
        parentElement: HTMLElement,
        session: Session,
        value?: FsDataSource,
        onChanged?: (newValue: FsDataSource | undefined) => void,
    }){
        this.session = params.session
        this._value = params.value
        this.onChanged = params.onChanged
        this.element = createElement({tagName: "div", parentElement: params.parentElement})

        new Paragraph({parentElement: this.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Label({parentElement: undefined, innerText: "Url: "}),
            this.urlInput = new UrlInput({parentElement: undefined}),
            this.checkButton = new Button({inputType: "button", text: "check", parentElement: undefined, onClick: () => this.checkUrl()}),
        ]})
        this.urlInput.element.addEventListener("keyup", (ev) => {
            this.checkButton.disabled = this.urlInput.value === undefined;
            if(ev.key === 'Enter'){
                this.checkUrl()
            }
        })
        this.urlInput.element.addEventListener("focusout", () => this.checkUrl())

        this.statusMessageContainer = createElement({tagName: "p", parentElement: this.element, cssClasses: [CssClasses.InfoText]})
    }

    private async checkUrl(){
        let previousValue = this.value

        let url = this.urlInput.value
        if(url === undefined){
            if(previousValue !== undefined && this.onChanged){
                this.onChanged(undefined)
            }
            return
        }
        let datasources_result = await this.session.getDatasourcesFromUrl(new GetDatasourcesFromUrlParamsDto({url: url.toDto()}))
        if(datasources_result instanceof Error){
            new ErrorPopupWidget({message: `Error retrieving datasources: ${datasources_result}`})
            return
        }
        if(datasources_result === undefined){
            new ErrorPopupWidget({message: `No datasources fond with given URL: ${url}`})
            return
        }
        this.popupSuggestions(datasources_result instanceof Array ? datasources_result : [datasources_result])
    }

    protected popupSuggestions(suggestions: FsDataSource[]){
        new InputPopupWidget<FsDataSource>({
            title: "Select a Data Source",
            inputWidgetFactory: (parentElement) => {
                return new SelectorWidget({
                    parentElement: parentElement,
                    options: suggestions,
                    optionRenderer: (args) => createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option.getDisplayString()}),
                })
            },
            onConfirm: (ds) => {
                this.value = ds
            },
        })
    }

    public get value(): FsDataSource | undefined{
        return this._value
    }

    public set value(value: FsDataSource | undefined){
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