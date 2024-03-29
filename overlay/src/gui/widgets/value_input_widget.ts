import { AxesKeys, AxisKey, BucketFs, Color, HttpFs } from "../../client/ilastik";
import { Path, Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { Button, InputType, InputWidget, InputWidgetParams, Select } from "./input_widget";
import { ContainerWidget, Span, TagName } from "./widget";

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
        if(["text", "number", "search", "url"].includes(params.inputType)){
            this.element.classList.add(CssClasses.ItkCharacterInput)
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
        this.value = params.value
    }
    public get value(): string | undefined{
        return this.element.value.trim() || undefined
    }
    public set value(val: string | undefined){
        this.element.value = val === undefined ? "" : val
    }
}

export class NumberInput extends ValueInputWidget<number | undefined, "number">{
    constructor(params: ValueInputWidgetParams<number | undefined> & {value?: number, min?: number, max?: number, step?: number}){
        super({...params, inputType: "number"});
        if(params.min !== undefined){
            this.element.min = params.min.toString()
        }
        if(params.max !== undefined){
            this.element.max = params.max.toString()
        }
        if(params.step !== undefined){
            this.element.step = params.step.toString()
        }
        this.value = params.value
    }
    public get value(): number | undefined{
        if(!this.raw){
            return undefined
        }
        return parseFloat(this.raw)
    }
    public set value(val: number | undefined){
        this.raw = val === undefined ? "" : val.toString()
    }
}

export class ColorPicker extends ValueInputWidget<Color, "color">{
    constructor(params: ValueInputWidgetParams<Color> & {value?: Color}){
        super({...params, inputType: "color"})
        this.element.classList.add(CssClasses.ItkButton)
        this.element.classList.add(CssClasses.ItkColorPicker)
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
        super({
            ...params,
            inputType: "url"
        })
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

export class PathInput extends ValueInputWidget<Path | undefined, "text">{
    constructor(params: ValueInputWidgetParams<Path | undefined> & {value?: Path}){
        super({
            ...params,
            inputType: "text"
        })
        this.value = params.value
    }

    public get value(): Path | undefined{
        if(!this.raw){
            return undefined
        }
        return Path.parse(this.raw) //FIXME: bad path?
    }

    public set value(path: Path | undefined){
        if(path){
            this.element.value = path.toString()
        }else{
            this.element.value = ""
        }
    }
}

export class BucketFsInput extends ValueInputWidget<BucketFs | undefined, "text">{
    constructor(params: ValueInputWidgetParams<BucketFs | undefined> & {value?: BucketFs}){
        super({...params, inputType: "text"})
        this.value  = params.value
    }

    public get value(): BucketFs | undefined{
        if(!this.raw){
            return undefined
        }
        return new BucketFs({bucket_name: this.raw})
    }

    public set value(fs: BucketFs | undefined){
        if(fs){
            this.raw = fs.bucket_name
        }else{
            this.raw = ""
        }
    }
}

export class HttpFsInput extends ValueInputWidget<HttpFs | undefined, "url">{
    constructor(params: ValueInputWidgetParams<HttpFs | undefined> & {value?: HttpFs}){
        super({...params, inputType: "url"})
        this.value  = params.value
    }

    public get value(): HttpFs | undefined{
        try{//FIXME: make URl.parse return an error
            let url = Url.parse(this.raw)
            if(url.protocol != "http" && url.protocol != "https"){
                return undefined
            }
            return new HttpFs({
                protocol: url.protocol,
                hostname: url.hostname,
                port: url.port,
                path: url.path,
                search: url.search,
            })
        }catch{
            return undefined
        }
    }

    public set value(fs: HttpFs | undefined){
        if(fs){
            this.raw = fs.url.toString()
        }else{
            this.raw = ""
        }
    }
}

export class BooleanInput extends ValueInputWidget<boolean, "checkbox">{
    private readonly valueExplanationSpan: Span;
    private readonly valueExplanations: { on: string; off: string; }

    constructor(params: ValueInputWidgetParams<boolean> & {
        value?: boolean,
        valueExplanations?: {on: string, off: string},
    }){

        let onClick = (ev: MouseEvent) => {
            this.value = this.element.checked //FIXME? this is just to update description text
            if(params.onClick){
                params.onClick(ev)
            }
        }
        super({...params, inputType: "checkbox", onClick})
        this.valueExplanations = params.valueExplanations || {on: "", off: ""}
        this.valueExplanationSpan = new Span({parentElement: params.parentElement, cssClasses: [CssClasses.InfoText]})
        this.value  = params.value === undefined ? false : params.value
    }

    public get value(): boolean{
        return this.element.checked
    }

    public set value(val: boolean){
        this.element.checked = val
        this.valueExplanationSpan.setInnerText(this.valueExplanations[val ? "on" : "off"])
    }
}

export class ToggleButton extends Button<"button">{
    private pressed: boolean
    constructor(params: InputWidgetParams & {text: string, value: boolean}){
        let onClick = (ev: MouseEvent) => {
            this.value = !this.pressed
            if(params.onClick){
                params.onClick(ev)
            }
        }
        super({...params, onClick, inputType: "button"})
        this.pressed  = params.value
        this.value = params.value
    }

    public get value(): boolean{
        return this.pressed
    }

    public set value(val: boolean){
        this.pressed = val
        if(val){
            this.addCssClass(CssClasses.ItkButtonDepressed)
        }else{
            this.removeCssClass(CssClasses.ItkButtonDepressed)
        }
    }
}

export class AxisKeyInput extends Select<AxisKey>{
    constructor(params: {parentElement: HTMLElement | ContainerWidget<TagName> | undefined, value?: AxisKey}){
        super({
            parentElement: params.parentElement,
            options: ["x", "y", "z", "t", "c"],
            renderer: (val) => new Span({parentElement: undefined, innerText: val}),
            popupTitle: "Select an axis",
            value: params.value
        })
    }
}

export class AxesKeysInput extends Span{
    public readonly axisLabel0: Select<AxisKey>;
    public readonly axisLabel1: Select<AxisKey>;
    public readonly axisLabel2: Select<AxisKey>;
    public readonly axisLabel3: Select<AxisKey>;
    public readonly axisLabel4: Select<AxisKey>;

    constructor(params: {
        parentElement: HTMLElement | ContainerWidget<TagName> | undefined,
        value?: AxesKeys,
    }){
        let axisLabel0: Select<AxisKey>;
        let axisLabel1: Select<AxisKey>;
        let axisLabel2: Select<AxisKey>;
        let axisLabel3: Select<AxisKey>;
        let axisLabel4: Select<AxisKey>;
        super({...params, children: [
            axisLabel0 = new AxisKeyInput({parentElement: undefined, value: "t"}),
            axisLabel1 = new AxisKeyInput({parentElement: undefined, value: "z"}),
            axisLabel2 = new AxisKeyInput({parentElement: undefined, value: "y"}),
            axisLabel3 = new AxisKeyInput({parentElement: undefined, value: "x"}),
            axisLabel4 = new AxisKeyInput({parentElement: undefined, value: "c"}),
        ]})
        this.axisLabel0 = axisLabel0
        this.axisLabel1 = axisLabel1
        this.axisLabel2 = axisLabel2
        this.axisLabel3 = axisLabel3
        this.axisLabel4 = axisLabel4
    }

    protected validate = (): AxesKeys | Error => {
        let axes = new Set<AxisKey>([this.axisLabel0.value]);
        for(const [idx, selector] of [this.axisLabel1, this.axisLabel2, this.axisLabel3, this.axisLabel4].entries()){
            axes.add(selector.value)
            if(axes.size < idx + 2){
                // selector.element.setCustomValidity("...")
                return Error("Repeated axis")
            }//else{selector.element.setCustomValidity("")}
        }
        return [
            this.axisLabel0.value, this.axisLabel1.value, this.axisLabel2.value, this.axisLabel3.value, this.axisLabel4.value
        ]
    }

    public get value(): AxesKeys | undefined{
        const value = this.validate()
        if(value instanceof Error){
            return undefined
        }
        return value
    }

    public set value(value: AxesKeys | undefined){
        if(value === undefined){
            return //FIXME? forced to accept undefined because of get/set semantics
        }
        this.axisLabel0.value = value[0]
        this.axisLabel1.value = value[1]
        this.axisLabel2.value = value[2]
        this.axisLabel3.value = value[3]
        this.axisLabel4.value = value[4]
    }
}

export class RangeInput extends ValueInputWidget<number, "range">{
    constructor(params: ValueInputWidgetParams<number> & {value: number, min: number, max: number, step: number}){
        super({...params, inputType: "range"})
        this.element.min = params.min.toString()
        this.element.max = params.max.toString()
        this.element.step = params.step.toString()
        this.value = params.value
    }

    public get value(): number {
        return parseFloat(this.raw)
    }
    public set value(val: number) {
        this.raw = val.toString()
    }
}