import { createElement, removeElement } from "../../util/misc";

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
        this.element = createElement({tagName: "div", parentElement: document.body, cssClasses: ["ItkPopupWidget"], inlineCss: {
            position: "fixed",
            zIndex: zIndex + 1 + "",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
        }})
        createElement({tagName: "h2", parentElement: this.element, innerHTML: title})
    }

    public destroy(){
        removeElement(this.background)
        removeElement(this.element)
    }
}
