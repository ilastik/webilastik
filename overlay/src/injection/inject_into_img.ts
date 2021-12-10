export {}
import { HtmlImgDriver, OverlayControls } from "..";
import { injectCss } from "../util/misc";
import "../util/fetch_wrapper";
import { Url } from "../util/parsed_url";

(window as any).inject_ilastik_into_images = (ilastikUrl?: URL, cssUrl?: URL) => {
    document.addEventListener("dblclick", (ev: MouseEvent) => {
        const clicked_element = ev.target as HTMLElement
        if(clicked_element.tagName != "IMG"){
            return
        }
        let controls = new OverlayControls({
            parentElement: document.body,
            viewer_driver: new HtmlImgDriver({img: clicked_element as HTMLImageElement}),
            ilastikUrl: ilastikUrl? Url.parse(ilastikUrl.toString()) : undefined,
        })
        controls.element.style.zIndex = "999"
        if(cssUrl){
            injectCss(Url.parse(cssUrl.toString()))
        }
    })
}
