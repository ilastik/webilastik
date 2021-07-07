import { IViewerDriver } from "../../drivers/viewer_driver";
import { createElement, injectCss } from "../../util/misc";
import { SessionManagerWidget } from "./session_manager";
// import { SessionManagerWidget } from "./session_manager";

export class OverlayControls{
    element: HTMLElement;
    constructor({
        parentElement=document.body, ilastik_url, viewer_driver, draggable=true, css
    }: {
        parentElement: HTMLElement, ilastik_url?: URL, viewer_driver: IViewerDriver, draggable?: boolean, css?: URL
    }){
        if(css){
            injectCss(css)
        }
        this.element = createElement({tagName: "div", parentElement, cssClasses: ["ItkOverlayControls"]})
        const header = createElement({tagName: "h1", parentElement: this.element, cssClasses: ["ItkOverlayControls_header"], innerHTML: "Webilastik"})

        if(draggable){
            this.element.style.position = "fixed"
            this.element.style.top = "0"
            this.element.style.left = "0"
            header.style.userSelect = "none"
            header.style.cursor = "move"
            createElement({
                tagName: "span", parentElement: header, innerHTML: "•••", cssClasses: ["ItkOverlayControls_drag_handle"], inlineCss: {float: "right"}
            })
            header.addEventListener("mousedown", (mouse_down_event) => {
                let current_pos = {x: parseInt(this.element.style.left), y: parseInt(this.element.style.top)}
                let drag_handler = (move_event: MouseEvent) => {
                    let delta = {x: move_event.screenX - mouse_down_event.screenX, y: move_event.screenY - mouse_down_event.screenY}
                    this.element.style.left = (current_pos.x + delta.x).toString() + "px"
                    this.element.style.top = (current_pos.y + delta.y).toString() + "px"
                }
                let cleanup = () => {
                    document.removeEventListener("mousemove", drag_handler)
                    document.removeEventListener("mouseup", cleanup)
                }
                document.addEventListener("mousemove", drag_handler)
                document.addEventListener("mouseup", cleanup)
            })
        }


        new SessionManagerWidget({
            parentElement: this.element, ilastik_url, viewer_driver, workflow_container: this.element
        })
    }
}
