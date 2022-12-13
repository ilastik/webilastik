import { Session } from "../../client/ilastik";
import { IViewerDriver } from "../../drivers/viewer_driver";
import { createElement, injectCss } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { ErrorPopupWidget } from "./popup";
import { SessionManagerWidget } from "./session_manager";
// import { SessionManagerWidget } from "./session_manager";

export class OverlayControls{
    element: HTMLElement;
    constructor({
        parentElement=document.body, ilastikUrl=Url.parse("https://app.ilastik.org/"), viewer_driver, draggable=true, css
    }: {
        parentElement: HTMLElement, ilastikUrl?: Url, viewer_driver: IViewerDriver, draggable?: boolean, css?: Url
    }){
        if(css){
            injectCss(css)
        }
        this.element = createElement({tagName: "div", parentElement, cssClasses: [CssClasses.ItkOverlayControls]})
        const header = createElement({
            tagName: "h1",
            parentElement: this.element,
            cssClasses: [CssClasses.ItkOverlayControlsHeader, CssClasses.ItkTitleBar],
        })
        createElement({tagName: "span", parentElement: header, innerText: "Webilastik"})

        if(draggable){
            this.element.style.position = "fixed"
            this.element.style.top = "0"
            this.element.style.left = "0"
            header.style.userSelect = "none"
            header.style.cursor = "move"
            createElement({
                tagName: "span",
                parentElement: header,
                innerText: "⠿",
                cssClasses: [CssClasses.ItkDragHandle],
            })
            header.addEventListener("mousedown", (mouse_down_event) => {
                let current_pos = {x: parseInt(this.element.style.left), y: parseInt(this.element.style.top)}
                let drag_handler = (move_event: MouseEvent) => {
                    let delta = {x: move_event.screenX - mouse_down_event.screenX, y: move_event.screenY - mouse_down_event.screenY}
                    this.element.style.left = (Math.max(0, current_pos.x + delta.x)).toString() + "px"
                    this.element.style.top = (Math.max(0, current_pos.y + delta.y)).toString() + "px"
                }
                let cleanup = () => {
                    document.removeEventListener("mousemove", drag_handler)
                    document.removeEventListener("mouseup", cleanup)
                }
                document.addEventListener("mousemove", drag_handler)
                document.addEventListener("mouseup", cleanup)
            })
        }

        let showSessionWidget = async () => {
            let siteNamesResponse = await Session.getAvailableHpcSites({ilastikUrl})
            if(siteNamesResponse instanceof Error){
                new ErrorPopupWidget({message: `Could not retrieve HPC site names: ${siteNamesResponse.message}`})
                return
            }
            new SessionManagerWidget({
                parentElement: this.element, ilastikUrl, viewer_driver, workflow_container: this.element, hpcSiteNames: siteNamesResponse.available_sites
            })
        };
        showSessionWidget();
    }
}
