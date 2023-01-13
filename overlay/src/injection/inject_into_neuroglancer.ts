import { NeuroglancerDriver, OverlayControls } from "..";
import { EulaPopup } from "../gui/widgets/eula_popup";
import { injectCss } from "../util/misc";
import { Url } from "../util/parsed_url";

//You can bundle the entire project using this as the main script. Then, inject it
//onto a page with neuroglancer (via a bookmarklet, for example) to have a working
//overlay

(window as any).inject_ilastik = (ilastikUrl?: URL, cssUrl?: URL) => {
    let viewer : any = (<any>window)["viewer"];

    const overlay_controls = new OverlayControls({
        viewer_driver: new NeuroglancerDriver(viewer),
        ilastikUrl: ilastikUrl ? Url.parse(ilastikUrl.toString()) : undefined,
    })
    overlay_controls.element.style.zIndex = "999"
    if(cssUrl){
        injectCss(Url.parse(cssUrl.toString()))
    }

    new EulaPopup()
}
