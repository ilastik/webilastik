import { NeuroglancerDriver, OverlayControls } from "..";
import { injectCss } from "../util/misc";

//You can bundle the entire project using this as the main script. Then, inject it
//onto a page with neuroglancer (via a bookmarklet, for example) to have a working
//overlay

(window as any).inject_ilastik = (ilastik_url?: URL, css_url?: URL) => {
    let viewer : any = (<any>window)["viewer"];

    const overlay_controls = new OverlayControls({
        parentElement: document.body,
        viewer_driver: new NeuroglancerDriver(viewer),
        ilastik_url,
    })
    overlay_controls.element.style.zIndex = "999"
    if(css_url){
        injectCss(css_url)
    }
}
