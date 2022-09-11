import { createElement, createInput } from "../../util/misc";
import { PopupWidget } from "./popup";

export class EulaPopup{
    constructor(){
        let popup = new PopupWidget("Using webilastik: Terms and Conditions")
        createElement({tagName: "div", parentElement: popup.element, innerHTML: `
            <p>
                webilastik's computation is backed by the HPCs in CSCS and Juelich; Therefore, in order to use this application,
                you agree to the terms and conditions of using each of those HPC sites:
            </p>

            <p>
                <a href="https://www.cscs.ch/services/user-regulations/" target="_blank" rel = "noopener noreferrer">
                    CSCS user regulations
                </a>
            </p>

            <p>
                <a href="https://apps.fz-juelich.de/jsc/service-accounts/_downloads/2d3eea9da1b587bad943101f49f4685b/Usage-Agreement-Service-User.pdf" target="_blank" rel = "noopener noreferrer">
                    Juelich user regulations
                </a>
            </p>

            <p>
                Further, you agree to not use this application to process any personal data as defined by the GDPR.
            </p>

        `})
        createInput({inputType: "button", parentElement: popup.element, value: "I accept the agreement", onClick: () => {
            popup.destroy()
        }})
    }
}