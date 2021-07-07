import { JsonableValue, IDeserializer, toJsonValue } from "../../util/serialization";
import { Session } from "../ilastik";


export class Applet<STATE extends JsonableValue>{
    public readonly name: string
    public readonly session: Session
    public readonly socket: WebSocket
    public readonly deserializer: IDeserializer<STATE>

    public constructor({name, session, deserializer, onNewState}: {
        name: string,
        session: Session,
        deserializer: IDeserializer<STATE>,
        onNewState?: (new_state: STATE) => void
    }){
        this.name = name
        this.deserializer = deserializer
        this.session = session
        //FIXME: handle failing sockets
        this.socket = session.createAppletSocket(name)
        this.socket.addEventListener("error", (ev) => {
            console.error(`Socket for ${this.name} broke:`)
            console.error(ev)
        })
        this.socket.addEventListener("message", (ev: MessageEvent) => {
            let raw_data = JSON.parse(ev.data)
            console.log(`vvvvvvvv ${this.name} got this state from server:\n${JSON.stringify(raw_data, null, 4)}`)
            let new_state = this.deserializer(raw_data)
            if(onNewState){
                onNewState(new_state)
            }
        })
    }

    protected updateUpstreamState(new_state: STATE){
        const args = toJsonValue(new_state)
        console.debug(`^^^^^^^ ${this.name} is pushing following state:\n${JSON.stringify(args, null, 4)}`)
        this.socket.send(JSON.stringify(toJsonValue(new_state)))
    }
}
