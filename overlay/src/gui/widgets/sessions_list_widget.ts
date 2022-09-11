import { HpcSiteName, Session, SessionStatus } from "../../client/ilastik";
import { createElement, createImage, createInput, removeElement, secondsToTimeDeltaString } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { ErrorPopupWidget, PopupWidget } from "./popup";

class SessionItemWidget{
    public readonly status: SessionStatus;
    public readonly element: HTMLTableRowElement;
    private cancelButton: HTMLInputElement

    constructor(params: {
        status: SessionStatus,
        parentElement: HTMLTableElement,
        ilastikUrl: Url,
        onSessionClosed: (status: SessionStatus) => void,
    }){
        this.status = params.status
        this.element = createElement({tagName: "tr", parentElement: params.parentElement})
        const job = params.status.slurm_job
        const startTimeString = job.start_time_utc_sec ? new Date(job.start_time_utc_sec * 1000).toLocaleString() : "not started"

        createElement({tagName: "td", parentElement: this.element, innerText: job.session_id})
        createElement({tagName: "td", parentElement: this.element, innerText: startTimeString})
        createElement({tagName: "td", parentElement: this.element, innerText: secondsToTimeDeltaString(job.time_elapsed_sec)})
        createElement({tagName: "td", parentElement: this.element, innerText: job.state})
        let cancelButtonTd = createElement({tagName: "td", parentElement: this.element})
        this.cancelButton = createInput({
            inputType: "button",
            parentElement: cancelButtonTd,
            disabled: job.is_done(),
            value: "Kill",
            onClick: async () => {
                this.cancelButton.disabled = true;
                this.cancelButton.classList.add("ItkLoadingBackground");
                let cancellationResult = await Session.cancel({
                    ilastikUrl: params.ilastikUrl, sessionId: job.session_id, hpc_site: params.status.hpc_site,
                })
                if(cancellationResult instanceof Error){
                    new ErrorPopupWidget({
                        message: `Could not delete session: ${cancellationResult.message}`,
                        onClose: () => {this.cancelButton.disabled = false}
                    })
                    this.cancelButton.disabled = false;
                    this.cancelButton.classList.remove("ItkLoadingBackground");
                    return
                }else{
                    removeElement(this.element)
                    params.onSessionClosed(this.status)
                }
            }
        })
    }
}

export class SessionsPopup{
    constructor(params: {
        ilastikUrl: Url,
        sessionStati: Array<SessionStatus>,
        onSessionClosed: (status: SessionStatus) => void,
    }){
        let popup = new PopupWidget("Sessions:")
        let table = createElement({tagName: "table", parentElement: popup.element, cssClasses: ["ItkTable"]})
        createElement({tagName: "th", parentElement: table, innerText: "Session ID"})
        createElement({tagName: "th", parentElement: table, innerText: "Start Time"})
        createElement({tagName: "th", parentElement: table, innerText: "Duration"})
        createElement({tagName: "th", parentElement: table, innerText: "Status"})
        createElement({tagName: "th", parentElement: table, innerText: ""})
        params.sessionStati.forEach(status => new SessionItemWidget({
            ...params, status, parentElement: table,
        }))

        createInput({inputType: "button", parentElement: popup.element, value: "OK", onClick: () => popup.destroy()})
    }

    public static async create(params: {
        ilastikUrl: Url,
        onSessionClosed: (status: SessionStatus) => void,
        hpc_site: HpcSiteName,
    }): Promise<SessionsPopup | Error | undefined>{
        const loadingPopup = new PopupWidget("Fetching sessions...");
        createImage({
            src: "/public/images/loading.gif",
            parentElement: createElement({tagName: "p", parentElement: loadingPopup.element}),
        })
        createInput({
            inputType: "button", parentElement: loadingPopup.element, value: "Cancel", onClick: () => loadingPopup.destroy()
        })
        let sessionStatiResult = await Session.listSessions({ilastikUrl: params.ilastikUrl, hpc_site: params.hpc_site})
        if(!loadingPopup.element.parentElement){
            return undefined
        }
        loadingPopup.destroy()
        if(sessionStatiResult instanceof Error){
            new ErrorPopupWidget({message: `Failed retrieving sessions`})
            return sessionStatiResult
        }
        return new SessionsPopup({...params, sessionStati: sessionStatiResult})
    }
}