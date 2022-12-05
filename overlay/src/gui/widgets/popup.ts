import { createElement, createImage, createInput, createInputParagraph, removeElement } from "../../util/misc";

export class PopupWidget{
    public readonly background: HTMLElement
    public readonly element: HTMLElement

    constructor(title: string){
        const zIndex = 99999
        this.background = createElement({tagName: "div", parentElement: document.body, inlineCss: {
            position: "fixed",
            height: "100vh",
            width: "100vw",
            top: "0",
            left: "0",
            zIndex: zIndex + "",
            backgroundColor: "rgba(0,0,0, 0.5)",
        }})
        this.element = createElement({tagName: "div", parentElement: document.body, cssClasses: ["ItkPopupWidget"]})
        createElement({tagName: "h2", parentElement: this.element, innerHTML: title})
    }

    public destroy(){
        removeElement(this.background)
        removeElement(this.element)
    }

    public static OkPopup(params: {title: string, paragraphs: string[]}): PopupWidget{
        let popup = new PopupWidget(params.title);
        for(let paragraph of params.paragraphs){
            createElement({tagName: "p", parentElement: popup.element, innerHTML: `<p>${paragraph}</p>`})
        }
        createInputParagraph({inputType: "button", parentElement:  popup.element, value: "Ok", onClick: () => {
            popup.destroy()
        }})
        return popup
    }

    public static LoadingPopup(params: {title: string}): PopupWidget{
        let popup = new PopupWidget(params.title);
        createImage({src: "/public/images/loading.gif", parentElement: popup.element})
        return popup
    }
}

export class ErrorPopupWidget extends PopupWidget{
    constructor(params: {message: string, onClose?: () => void}){
        super("Error")
        createElement({tagName: "span", parentElement: this.element, innerHTML: params.message})
        createInputParagraph({inputType: "button", parentElement:  this.element, value: "Ok", onClick: () => {
            this.destroy()
            if(params.onClose){
                params.onClose()
            }
        }})
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