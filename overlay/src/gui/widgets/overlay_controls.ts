import { Session, StartupConfigs } from "../../client/ilastik";
import { IViewerDriver } from "../../drivers/viewer_driver";
import { createElement, injectCss } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { ErrorPopupWidget } from "./popup";
import { SessionManagerWidget } from "./session_manager";
// import { SessionManagerWidget } from "./session_manager";



function uiGetUrlConfigs(): StartupConfigs{
    let startupConfigs = StartupConfigs.tryFromWindowLocation()
    if(startupConfigs instanceof Error){
        new ErrorPopupWidget({message: `Could not get startup configs from current URL: ${startupConfigs.message}. Using defaults...`})
        return StartupConfigs.getDefault()
    }
    return startupConfigs
}

export class OverlayControls{
    element: HTMLElement;
    constructor({
        ilastikUrl=Url.parse("https://app.ilastik.org/"), viewer_driver, css
    }: {
        ilastikUrl?: Url, viewer_driver: IViewerDriver, css?: Url
    }){
        if(css){
            injectCss(css)
        }
        this.element = createElement({tagName: "div", parentElement: viewer_driver.getContainerForWebilastikControls(), cssClasses: [CssClasses.ItkOverlayControls]})

        let showSessionWidget = async () => {
            let siteNamesResponse = await Session.getAvailableHpcSites({ilastikUrl})
            if(siteNamesResponse instanceof Error){
                new ErrorPopupWidget({message: `Could not retrieve HPC site names: ${siteNamesResponse.message}`})
                return
            }
            const configs = uiGetUrlConfigs();
            const sessionManagementWidget = new SessionManagerWidget({
                parentElement: this.element,
                ilastikUrl, viewer_driver,
                workflow_container: this.element,
                hpcSiteNames: siteNamesResponse.available_sites,
                configs,
            })
            if(configs.autorejoin_session_id){
                sessionManagementWidget.rejoinSession(configs.autorejoin_session_id)
            }

        };
        showSessionWidget();
    }
}
