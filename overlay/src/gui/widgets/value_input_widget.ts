import { Color } from "../../client/ilastik";
import { Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { InputType, InputWidget, InputWidgetParams } from "./input_widget";

export type ValueInputWidgetParams<V> = InputWidgetParams & {
    onChange?: (newvalue: V) => void,
}

export abstract class ValueInputWidget<V, IT extends InputType> extends InputWidget<IT>{
    constructor(params: ValueInputWidgetParams<V> & {inputType: IT}){
        super(params)
        const onChange = params.onChange;
        if(onChange){
            this.element.addEventListener("change", () => onChange(this.value))
        }
    }

    protected get raw(): string{
        return this.element.value.trim()
    }
    protected set raw(val: string){
        this.element.value = val.trim()
    }

    public abstract get value(): V;
    public abstract set value(val: V);
}

export class TextInput extends ValueInputWidget<string | undefined, "text">{
    constructor(params: ValueInputWidgetParams<string | undefined> & {value?: string}){
        super({...params, inputType: "text"})
        this.element.classList.add(CssClasses.ItkCharacterInput)
        this.value = params.value
    }
    public get value(): string | undefined{
        return this.element.value.trim() || undefined
    }
    public set value(val: string | undefined){
        this.element.value = val === undefined ? "" : val
    }
}

export class NumberInput extends ValueInputWidget<number, "number">{
    constructor(params: ValueInputWidgetParams<number> & {value: number, min?: number, max?: number}){
        super({...params, inputType: "number"});
        this.element.classList.add(CssClasses.ItkCharacterInput)
        if(params.min !== undefined){
            this.element.min = params.min.toString()
        }
        if(params.max !== undefined){
            this.element.max = params.max.toString()
        }
        this.value = params.value
    }
    public get value(): number{
        return parseFloat(this.raw)
    }
    public set value(val: number){
        this.raw = val.toString()
    }
}

export class ColorPicker extends ValueInputWidget<Color, "color">{
    constructor(params: ValueInputWidgetParams<Color> & {value?: Color}){
        super({...params, inputType: "color"})
        this.element.classList.add(CssClasses.ItkButton)
        if(params.value){
            this.value = params.value
        }
    }
    public get value(): Color{
        return Color.fromHexCode(this.raw)
    }
    public set value(val: Color){
        this.raw = val.hexCode
    }
}

export class UrlInput extends ValueInputWidget<Url | undefined, "url">{
    constructor(params: ValueInputWidgetParams<Url | undefined> & {value?: Url}){
        super({...params, inputType: "url"})
        this.element.addEventListener("change", () => {
            this.element.setCustomValidity(this.raw && this.value === undefined ? "Bad URL" : "")
        })
        this.value = params.value
    }
    public get value(): Url | undefined{
        try{
            return Url.parse(this.element.value)
        }catch(e){
            return undefined
        }
    }
    public set value(value: Url | undefined){
        this.element.value = value === undefined ? "" : value.toString()
    }
}