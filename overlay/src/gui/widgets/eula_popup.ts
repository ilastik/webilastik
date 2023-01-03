import { Url } from "../../util/parsed_url";
import { Button } from "./input_widget";
import { PopupWidget } from "./popup";
import { Anchor, Paragraph } from "./widget";

export class EulaPopup{
    constructor(){
        let popup = new PopupWidget("Using webilastik: Terms and Conditions")
        new Paragraph({parentElement: popup.element, innerText: (
            "webilastik's computation is backed by the HPCs in CSCS and Juelich; Therefore, in order to use this application, " +
            "you agree to the terms and conditions of using each of those HPC sites:"
        )})
        new Paragraph({parentElement: popup.element, children: [
            new Anchor({
                parentElement: undefined,
                innerText: "CSCS user regulations",
                href: Url.parse("https://www.cscs.ch/services/user-regulations/"),
                target: "_blank",
                rel: "noopener noreferrer",
            }),
        ]})
        new Paragraph({parentElement: popup.element, children: [
            new Anchor({
                parentElement: undefined,
                innerText: "Juelich user regulations",
                href: Url.parse("https://apps.fz-juelich.de/jsc/service-accounts/_downloads/2d3eea9da1b587bad943101f49f4685b/Usage-Agreement-Service-User.pdf"),
                target: "_blank",
                rel: "noopener noreferrer",
            }),
            new Paragraph({parentElement: popup.element, innerText: `
                Further, you agree to not use this application to process any personal data as defined by the GDPR.
            `})
        ]})
        new Button({
            inputType: "button", parentElement: popup.element, text: "I accept the agreement", onClick: () => popup.destroy()
        })
    }
}