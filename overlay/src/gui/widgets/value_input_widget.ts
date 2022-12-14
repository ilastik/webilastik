import { Color } from "../../client/ilastik";
import { CssClasses } from "../css_classes";
import { InputType, InputWidget, InputWidgetParams } from "./input_widget";

export type ValueInputWidgetParams<V> = InputWidgetParams & {
    onChange?: (newvalue: V) => void,
    value: V,
}

export abstract class ValueInputWidget<V, IT extends InputType> extends InputWidget<IT>{
    private readonly onChange: ((newvalue: V) => void) | undefined;

    constructor(params: ValueInputWidgetParams<V> & {inputType: IT}){
        super(params)
        this.onChange = params.onChange
        this.element.value = this.valueToRaw(params.value)
    }

    protected abstract rawToValue(raw: string): V;
    protected abstract valueToRaw(val: V): string;
    public get value(): V{
        return this.rawToValue(this.element.value)
    }

    public set value(val: V){
        this.element.value = this.valueToRaw(val)
        if(this.onChange){
            this.onChange(this.value)
        }
    }
}

export class TextInput extends ValueInputWidget<string | undefined, "text">{
    constructor(params: ValueInputWidgetParams<string | undefined>){
        super({...params, inputType: "text"})
        this.element.classList.add(CssClasses.ItkCharacterInput)
    }
    protected rawToValue(raw: string): string | undefined{
        return raw.trim() || undefined
    }
    protected valueToRaw(val: string | undefined): string{
        return val === undefined ? "" : val
    }
}

export class NumberInput extends ValueInputWidget<number, "number">{
    constructor(params: ValueInputWidgetParams<number> & {min?: number, max?: number}){
        super({...params, inputType: "number"});
        this.element.classList.add(CssClasses.ItkCharacterInput)
        if(params.min !== undefined){
            this.element.min = params.min.toString()
        }
        if(params.max !== undefined){
            this.element.max = params.max.toString()
        }
    }
    protected rawToValue(raw: string): number{
        return parseFloat(raw)
    }
    protected valueToRaw(val: number): string{
        return val.toString()
    }
}

export class ColorPicker extends ValueInputWidget<Color, "color">{
    constructor(params: ValueInputWidgetParams<Color>){
        super({...params, inputType: "color"})
        this.element.classList.add(CssClasses.ItkButton)
    }
    protected rawToValue(raw: string): Color{
        return Color.fromHexCode(raw)
    }
    protected valueToRaw(val: Color): string{
        return val.hexCode
    }
}
