import { ErrorPopupWidget } from "../../gui/widgets/popup";
import { IDeserializer, ensureJsonObject, JsonableValue} from "../../util/serialization";
import { Session } from "../ilastik";

export class Applet<STATE>{
    public readonly name: string
    public readonly session: Session
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
        this.session.addMessageListener((ev: MessageEvent) => {
            let payload = JSON.parse(ev.data)
            let payload_obj = ensureJsonObject(payload)
            if(payload_obj instanceof Error){
                new ErrorPopupWidget({message: payload_obj.message})
                return
            }
            let applet_payload = payload_obj[this.name]
            if(applet_payload === undefined){
                return
            }
            // console.log(`vvvvvvvv ${this.name} got this state from server:\n${JSON.stringify(applet_payload, null, 4)}`)
            if(onNewState){
                let new_state = this.deserializer(applet_payload)
                if(new_state instanceof Error){
                    new ErrorPopupWidget({message: new_state.message})
                    return
                }
                onNewState(new_state)
            }
        })
    }

    protected doRPC(method_name: string, method_arguments: JsonableValue){
        return this.session.doRPC({applet_name: this.name, method_name, method_arguments})
    }
}
