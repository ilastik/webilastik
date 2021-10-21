import { JsonableValue, IDeserializer, toJsonValue, ensureJsonObject } from "../../util/serialization";


export class Applet<STATE extends JsonableValue>{
    public readonly name: string
    public readonly socket: WebSocket
    public readonly deserializer: IDeserializer<STATE>

    public constructor({name, socket, deserializer, onNewState}: {
        name: string,
        socket: WebSocket,
        deserializer: IDeserializer<STATE>,
        onNewState?: (new_state: STATE) => void
    }){
        this.name = name
        this.deserializer = deserializer
        this.socket = socket
        this.socket.addEventListener("error", (ev) => {
            console.error(`Socket for ${this.name} broke:`)
            console.error(ev)
        })
        this.socket.addEventListener("message", (ev: MessageEvent) => {
            let payload = JSON.parse(ev.data)
            let payload_obj = ensureJsonObject(payload)
            let applet_payload = payload_obj[this.name]
            if(applet_payload === undefined){
                return
            }
            console.log(`vvvvvvvv ${this.name} got this state from server:\n${JSON.stringify(applet_payload, null, 4)}`)
            let new_state = this.deserializer(applet_payload)
            if(onNewState){
                onNewState(new_state)
            }
        })
    }

    protected updateUpstreamState(new_state: STATE){
        const args = toJsonValue(new_state)
        console.debug(`^^^^^^^ ${this.name} is pushing following state:\n${JSON.stringify(args, null, 4)}`)
        this.socket.send(JSON.stringify({
            [this.name]: toJsonValue(new_state)
        }))
    }
}
