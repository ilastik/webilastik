import { HpcSiteName, Session, SESSION_DONE_STATES } from "../../client/ilastik";
import { CloseComputeSessionParamsDto, ComputeSessionStatusDto, ListComputeSessionsParamsDto } from "../../client/dto";
import { createElement, createImage, removeElement, secondsToTimeDeltaString } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { Button } from "./input_widget";

class SessionItemWidget{
    public readonly status: ComputeSessionStatusDto;
    public readonly element: HTMLTableRowElement;
    private cancelButton: Button<"button">

    constructor(params: {
        status: ComputeSessionStatusDto,
        parentElement: HTMLTableElement,
        ilastikUrl: Url,
        onSessionClosed: (status: ComputeSessionStatusDto) => void,
    }){
        this.status = params.status
        this.element = createElement({tagName: "tr", parentElement: params.parentElement})
        const comp_session = params.status.compute_session
        const startTimeString = comp_session.start_time_utc_sec ? new Date(comp_session.start_time_utc_sec * 1000).toLocaleString() : "not started"

        createElement({tagName: "td", parentElement: this.element, innerText: comp_session.compute_session_id})
        createElement({tagName: "td", parentElement: this.element, innerText: startTimeString})
        createElement({tagName: "td", parentElement: this.element, innerText: secondsToTimeDeltaString(comp_session.time_elapsed_sec)})
        createElement({tagName: "td", parentElement: this.element, innerText: comp_session.state})
        let cancelButtonTd = createElement({tagName: "td", parentElement: this.element})
        this.cancelButton = new Button({
            inputType: "button",
            parentElement: cancelButtonTd,
            disabled: SESSION_DONE_STATES.includes(comp_session.state) ,
            text: "Kill",
            onClick: async () => {
                this.cancelButton.disabled = true;
                let cancellationResult = await Session.cancel({
                    ilastikUrl: params.ilastikUrl,
                    rpcParams: new CloseComputeSessionParamsDto({
                        compute_session_id: comp_session.compute_session_id,
                        hpc_site: params.status.hpc_site,
                    })
                })
                if(cancellationResult instanceof Error){
                    new ErrorPopupWidget({
                        message: `Could not delete session: ${cancellationResult.message}`,
                        onClose: () => {this.cancelButton.disabled = false}
                    })
                    this.cancelButton.disabled = false;
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
        sessionStati: Array<ComputeSessionStatusDto>,
        onSessionClosed: (status: ComputeSessionStatusDto) => void,
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

        new Button({inputType: "button", parentElement: popup.element, text: "OK", onClick: () => popup.destroy()})
    }

    public static async create(params: {
        ilastikUrl: Url,
        onSessionClosed: (status: ComputeSessionStatusDto) => void,
        hpc_site: HpcSiteName,
    }): Promise<SessionsPopup | Error | undefined>{
        const loadingPopup = new PopupWidget("Fetching sessions...");
        createImage({
            src: "/public/images/loading.gif",
            parentElement: createElement({tagName: "p", parentElement: loadingPopup.element}),
        })
        new Button({
            inputType: "button", parentElement: loadingPopup.element, text: "Cancel", onClick: () => loadingPopup.destroy()
        })
        let sessionStatiResult = await Session.listSessions({
            ilastikUrl: params.ilastikUrl,
            rpcParams: new ListComputeSessionsParamsDto({hpc_site: params.hpc_site})
        })
        if(!loadingPopup.element.parentElement){
            return undefined
        }
        loadingPopup.destroy()
        if(sessionStatiResult instanceof Error){
            new ErrorPopupWidget({message: `Failed retrieving sessions`})
            return sessionStatiResult
        }
        return new SessionsPopup({...params, sessionStati: sessionStatiResult.compute_sessions_stati})
    }
}