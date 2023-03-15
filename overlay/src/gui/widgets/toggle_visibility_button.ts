import { Button, InputWidgetParams } from "./input_widget";
import { Widget } from "./widget";

export class ToggleVisibilityButton extends Button<"button">{
    private subject: Widget<any>;

    constructor(params: InputWidgetParams & {
        text: string,
        subject: Widget<any>
    }){
        const hideSubject = (ev: MouseEvent) => {
            if(ev.target == this.element || this.subject.element.contains(ev.target)){
                return
            }
            this.subject.show(false)
        }
        super({...params, inputType: "button", onClick: () => {
            if(this.subject.isHidden()){
                this.subject.show(true)
                window.addEventListener("click", hideSubject, true)
            }else{
                this.subject.show(false)
                window.removeEventListener("click", hideSubject, true)
            }
        }})

        this.subject = params.subject
        this.subject.show(false)
    }
}