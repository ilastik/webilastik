import { HpcSiteName, Session, SESSION_DONE_STATES } from "../../client/ilastik";
import { CloseComputeSessionParamsDto, ComputeSessionStatusDto, EbrainsAccessTokenDto, ListComputeSessionsParamsDto } from "../../client/dto";
import { secondsToTimeDeltaString } from "../../util/misc";
import { Path, Url } from "../../util/parsed_url";
import { ErrorPopupWidget, PopupWidget } from "./popup";
import { Button, ButtonWidget } from "./input_widget";
import { ImageWidget, Paragraph, Table, Td, Th, THead, Tr } from "./widget";
import { CssClasses } from "../css_classes";

class SessionItemWidget{
    public readonly status: ComputeSessionStatusDto;
    public readonly element: Tr;
    private cancelButton: ButtonWidget
    private rejoinButton: ButtonWidget;

    constructor(params: {
        status: ComputeSessionStatusDto,
        parentElement: Table,
        ilastikUrl: Url,
        token: EbrainsAccessTokenDto,
        onSessionClosed: (status: ComputeSessionStatusDto) => void,
        rejoinSession?: (sessionId: string) => void,
    }){
        this.status = params.status
        const comp_session = params.status.compute_session
        const startTimeString = comp_session.start_time_utc_sec ? new Date(comp_session.start_time_utc_sec * 1000).toLocaleString() : "not started"

        this.element = new Tr({parentElement: params.parentElement, children: [
            new Td({parentElement: undefined, innerText: comp_session.compute_session_id}),
            new Td({parentElement: undefined, innerText: startTimeString}),
            new Td({parentElement: undefined, innerText: secondsToTimeDeltaString(comp_session.time_elapsed_sec)}),
            new Td({parentElement: undefined, innerText: comp_session.state}),
            new Td({parentElement: undefined, children: [
                this.cancelButton = new ButtonWidget({
                    parentElement: undefined,
                    disabled: SESSION_DONE_STATES.includes(comp_session.state) ,
                    contents: "Kill",
                    onClick: async () => {
                        this.cancelButton.disabled = true;
                        this.rejoinButton.disabled = true;
                        let sessionKillResult = await PopupWidget.WaitPopup({
                            title: `Killing session ${comp_session.compute_session_id} at ${params.status.hpc_site}`,
                            operation: Session.cancel({
                                ilastikUrl: params.ilastikUrl,
                                token: params.token,
                                rpcParams: new CloseComputeSessionParamsDto({
                                    compute_session_id: comp_session.compute_session_id,
                                    hpc_site: params.status.hpc_site,
                                })
                            })
                        });
                        if(sessionKillResult instanceof Error){
                            new ErrorPopupWidget({
                                message: `Could not delete session: ${sessionKillResult.message}`,
                                onClose: () => {this.cancelButton.disabled = false}
                            })
                            this.cancelButton.disabled = false;
                            this.rejoinButton.disabled = false;
                            return
                        }else{
                            // removeElement(this.element) //FIXME: is this right?
                            params.onSessionClosed(this.status)
                        }
                    }
                }),
                this.rejoinButton = new ButtonWidget({
                    parentElement: undefined,
                    contents: "Rejoin",
                    disabled: SESSION_DONE_STATES.includes(comp_session.state) || params.rejoinSession === undefined,
                    onClick: () => {
                        if(params.rejoinSession){
                            params.rejoinSession(comp_session.compute_session_id)
                        }
                    }
                }),
            ]})
        ]})
    }
}

export class SessionsPopup{
    constructor(params: {
        ilastikUrl: Url,
        token: EbrainsAccessTokenDto,
        sessionStati: Array<ComputeSessionStatusDto>,
        onSessionClosed: (status: ComputeSessionStatusDto) => void,
        rejoinSession?: (sessionId: string) => void,
    }){
        let popup = new PopupWidget("Sessions:", true)
        let table = new Table({parentElement: popup.contents, cssClasses: [CssClasses.ItkTable], children: [
            new THead({parentElement: undefined, children: [
                new Th({parentElement: undefined, innerText: "Session ID"}),
                new Th({parentElement: undefined, innerText: "Start Time"}),
                new Th({parentElement: undefined, innerText: "Duration"}),
                new Th({parentElement: undefined, innerText: "Status"}),
                new Th({parentElement: undefined, innerText: "Actions"}),
            ]})
        ]})
        params.sessionStati.forEach(status => new SessionItemWidget({
            ...params, status, parentElement: table, rejoinSession: params.rejoinSession === undefined ? undefined : (sessionId) => {
                popup.destroy()
                if(params.rejoinSession){
                    params.rejoinSession(sessionId)
                }
            }
        }))
    }

    public static async create(params: {
        ilastikUrl: Url,
        token: EbrainsAccessTokenDto,
        onSessionClosed: (status: ComputeSessionStatusDto) => void,
        rejoinSession?: (sessionId: string) => void,
        hpc_site: HpcSiteName,
    }): Promise<SessionsPopup | Error | undefined>{
        const loadingPopup = new PopupWidget("Fetching sessions...");
        new Paragraph({parentElement: loadingPopup.contents, children: [
            new ImageWidget({src: Path.parse("/public/images/loading.gif"), parentElement: undefined})
        ]})
        new Paragraph({parentElement: loadingPopup.contents, children: [
            new Button({
                inputType: "button", parentElement: undefined, text: "Cancel", onClick: () => loadingPopup.destroy()
            })
        ]})

        let sessionStatiResult = await Session.listSessions({
            ilastikUrl: params.ilastikUrl,
            token: params.token,
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