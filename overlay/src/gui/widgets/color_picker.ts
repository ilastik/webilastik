import { Color } from "../../client/ilastik";
import { createInput} from "../../util/misc";
import { CssClasses } from "../css_classes";

export class ColorPicker{
    public readonly element: HTMLInputElement

    constructor(params:{
        parentElement: HTMLElement,
        onChange?: (colors: {newColor: Color}) => void,
        color?: Color,
    }){
        this.element = createInput({inputType: "color", parentElement: params.parentElement, cssClasses: [CssClasses.ItkButton]})
        this.value = params.color || new Color({r:0, g:255, b: 0})

        const onChange = params.onChange
        if(onChange){
            this.element.addEventListener("change", () => onChange({newColor: this.value}))
        }
    }

    public get value(): Color{
        return Color.fromHexCode(this.element.value)
    }

    public set value(color: Color){
        this.element.value = color.hexCode
    }
}
