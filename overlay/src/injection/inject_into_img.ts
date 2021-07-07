export {}
import { HtmlImgDriver, OverlayControls } from "..";
import { injectCss } from "../util/misc";

(window as any).inject_ilastik_into_images = (ilastik_url?: URL, css_url?: URL) => {
    document.addEventListener("dblclick", (ev: MouseEvent) => {
        const clicked_element = ev.target as HTMLElement
        if(clicked_element.tagName != "IMG"){
            return
        }
        let controls = new OverlayControls({
            parentElement: document.body,
            viewer_driver: new HtmlImgDriver({img: clicked_element as HTMLImageElement}),
            ilastik_url,
        })
        controls.element.style.zIndex = "999"
        if(css_url){
            injectCss(css_url)
        }
    })
}
