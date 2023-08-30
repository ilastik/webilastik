import { createElement, createInput } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { Div, ImageWidget, Paragraph, Span, Widget } from "./widget";
import { TitleBar } from "./title_bar";
import { Button, ButtonWidget } from "./input_widget";
import { Path } from "../../util/parsed_url";

export class PopupWidget extends Div{
    public readonly background: Div
    public readonly header: TitleBar<"h1">
    public readonly contents: Div;

    protected static popupStack: Array<PopupWidget> = []

    constructor(title: string, closable: boolean = false){
        super({parentElement: document.body, cssClasses: [CssClasses.ItkPopupWidget]})
        const zIndex = 99999
        this.background = new Div({parentElement: document.body, inlineCss: {
            position: "fixed",
            height: "100vh",
            width: "100vw",
            top: "0",
            left: "0",
            zIndex: zIndex + "",
            backgroundColor: "rgba(0,0,0, 0.5)",
        }})
        this.header = new TitleBar({
            tagName: "h1",
            parentElement: this.element,
            text: title,
            widgetsRight: closable ?
                [
                    new Button({inputType: "button", text: "✖", parentElement: undefined, onClick: () => this.destroy()})
                ] : []
        })
        this.contents = new Div({parentElement: this.element, cssClasses: [CssClasses.ItkPopupContents]})
        if(PopupWidget.popupStack.length > 0){
            PopupWidget.popupStack[PopupWidget.popupStack.length - 1].show(false)
        }
        PopupWidget.popupStack.push(this)
    }

    public show(show: boolean): void {
        super.show(show)
        this.background.show(show)
    }

    public destroy(){
        this.background.destroy()
        super.destroy()
        let popupIndex = PopupWidget.popupStack.indexOf(this)
        if(popupIndex >= 0){
            PopupWidget.popupStack.splice(popupIndex, 1)
        }
        if(PopupWidget.popupStack.length > 0){
            PopupWidget.popupStack[PopupWidget.popupStack.length - 1].show(true)
        }
    }

    public static ClosablePopup(params: {title: string}): PopupWidget{
        return new PopupWidget(params.title, true);
    }

    public static OkPopup(params: {title: string, paragraphs: string[]}): PopupWidget{
        let popup = new PopupWidget(params.title);
        for(let paragraph of params.paragraphs){
            new Paragraph({parentElement: popup.element, innerText: paragraph})
        }
        new Paragraph({parentElement:  popup.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Button({parentElement: undefined, inputType: "button", text: "Ok", onClick: () => popup.destroy()})
        ]})
        return popup
    }

    public static LoadingPopup(params: {title: string}): PopupWidget{
        let popup = new PopupWidget(params.title);
        new Paragraph({parentElement: popup.contents, inlineCss: {textAlign: "center"}, children: [
            new ImageWidget({
                src: Path.parse("/public/images/loading.gif"), parentElement: popup.contents
            })
        ]})

        return popup
    }

    public static async WaitPopup<T>(params: {
        title: string,
        withSpinner?: boolean,
        operation: Promise<T> | ((popup: PopupWidget) => Promise<T>),
    }): Promise<T>{
        const withSpinner = params.withSpinner === undefined ? true : params.withSpinner
        let popup = withSpinner ? PopupWidget.LoadingPopup({title: params.title}) : new PopupWidget(params.title);
        let result = await (params.operation instanceof Promise ? params.operation : params.operation(popup));
        popup.destroy()
        return result
    }

    public static async WaitOkPopup(params: {
        title: string,
        contents: Widget<any>[],
    }): Promise<void>{
        return this.WaitPopup<void>({
            title: params.title,
            withSpinner: false,
            operation: async (popup) => new Promise<void>(resolve => {
                params.contents.forEach(widg => popup.contents.appendChild(widg))
                new Paragraph({parentElement: popup.contents, children: [
                    new ButtonWidget({
                        parentElement: undefined, contents: "Ok", onClick: () => resolve()
                    })
                ]})
            })
        })
    }

    public static async ButtonOptions<T>(params: {
        title: string, explanation: Widget<any>, options: Array<[string, T]>
    }): Promise<T>{
        return PopupWidget.WaitPopup({
            title: params.title,
            withSpinner: false,
            operation: async (popup) => new Promise(resolve => {
                popup.contents.appendChild(params.explanation)
                new Paragraph({parentElement: popup.contents, children: params.options.map(opt => {
                    return new ButtonWidget({
                        parentElement: undefined, contents: opt[0], onClick: () => resolve(opt[1])
                    })
                })});
            })
        })
    }
}

export class ErrorPopupWidget extends PopupWidget{
    constructor(params: {message: string | Widget<any>[], onClose?: () => void}){
        super("Error")
        let contentWidgets: Array<Widget<any>>;
        if(typeof params.message == "string"){
            contentWidgets = [new Span({parentElement: undefined, innerText: params.message})]
        }else{
            contentWidgets = params.message
        }
        for(const widget of contentWidgets){
            this.contents.appendChild(widget)
        }
        new Paragraph({parentElement:  this.element, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Button({parentElement: undefined, inputType: "button", text: "Ok", onClick: () => {
                this.destroy()
                if(params.onClose){
                    params.onClose()
                }
            }})
        ]})
    }
}

export class InputPopupWidget<V> extends PopupWidget{
    constructor(params: {
        title: string,
        inputWidgetFactory: (parentElement: HTMLElement) => {value: V},
        onConfirm: (value: V) => void,
        onCancel?: () => void
    }){
        super(params.title)
        let inputWidget = params.inputWidgetFactory(this.element)
        let p = createElement({tagName: "p", parentElement: this.element})
        createInput({inputType: "button", parentElement: p, value: "Ok", onClick: () => {
            this.destroy()
            params.onConfirm(inputWidget.value)
        }})
        createInput({inputType: "button", parentElement: p, value: "Cancel", onClick: () => {
            this.destroy()
            if(params.onCancel){
                params.onCancel()
            }
        }})
    }
}
