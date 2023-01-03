import { Shape5D } from "../../client/ilastik";
import { createElement } from "../../util/misc";
import { CssClasses } from "../css_classes";
import { NumberInput } from "./value_input_widget";
import { Label, Span } from "./widget";

export class Shape5DInput{
    public readonly xInput: NumberInput;
    public readonly yInput: NumberInput;
    public readonly zInput: NumberInput;
    public readonly tInput: NumberInput;
    public readonly cInput: NumberInput;
    public readonly tField: Span;
    public readonly zField: Span;
    public readonly yField: Span;
    public readonly xField: Span;
    public readonly cField: Span;
    constructor(params: {parentElement: HTMLElement, value?: Shape5D, disabled?: boolean}){
        let disabled = params.disabled === undefined ? false : params.disabled
        let parentElement = params.parentElement

        this.xField = new Span({parentElement, inlineCss: {whiteSpace: "nowrap"}, cssClasses: [CssClasses.ItkAxisLengthField], children: [
            new Label({parentElement: undefined, innerText: "x: "}),
            this.xInput = new NumberInput({parentElement: undefined, value: undefined, min: 1, disabled}),
        ]})
        this.yField = new Span({parentElement, inlineCss: {whiteSpace: "nowrap"}, cssClasses: [CssClasses.ItkAxisLengthField], children: [
            new Label({parentElement: undefined, innerText: " y: "}),
            this.yInput = new NumberInput({parentElement: undefined, value: undefined, min: 1, disabled}),
        ]})
        this.zField = new Span({parentElement, inlineCss: {whiteSpace: "nowrap"}, cssClasses: [CssClasses.ItkAxisLengthField], children: [
            new Label({parentElement: undefined, innerText: " z: "}),
            this.zInput = new NumberInput({parentElement: undefined, value: undefined, min: 1, disabled}),
        ]})
        this.tField = new Span({parentElement, inlineCss: {whiteSpace: "nowrap"}, cssClasses: [CssClasses.ItkAxisLengthField], children: [
            new Label({parentElement: undefined, innerText: " t: "}),
            this.tInput = new NumberInput({parentElement: undefined, value: 1, min: 1, disabled}),
        ]})
        this.cField = new Span({parentElement, inlineCss: {whiteSpace: "nowrap"}, cssClasses: [CssClasses.ItkAxisLengthField], children: [
            new Label({parentElement: undefined, innerText: " c: "}),
            this.cInput = new NumberInput({parentElement: undefined, value: undefined, min: 1, disabled}),
        ]})

        if(params.value){
            this.value = params.value
        }
    }

    public set value(shape: Shape5D | undefined){
        this.xInput.value = shape?.x
        this.yInput.value = shape?.y
        this.zInput.value = shape?.z
        this.tInput.value = shape?.t
        this.cInput.value = shape?.c
    }

    public get value(): Shape5D | undefined{
        let x = this.xInput.value
        let y = this.yInput.value
        let z = this.zInput.value
        let t = this.tInput.value
        let c = this.cInput.value
        if(x === undefined || y === undefined || z === undefined || t === undefined || c === undefined){
            return undefined
        }
        return new Shape5D({x, y, z, t, c})
    }

    public get disabled(): boolean{
        return this.xInput.disabled
    }

    public set disabled(value: boolean){
        this.xInput.disabled = value
        this.yInput.disabled = value
        this.zInput.disabled = value
        this.tInput.disabled = value
        this.cInput.disabled = value
    }

    public static createLabeledFieldset(params: {legend: string} & ConstructorParameters<typeof Shape5DInput>[0]): Shape5DInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new Shape5DInput({...params, parentElement: fieldset})
    }
}

export class Shape5DInputNoChannel{
    public readonly shapeInput: Shape5DInput;
    constructor(params: {parentElement: HTMLElement, disabled?: boolean}){
        this.shapeInput = new Shape5DInput(params)
        this.shapeInput.cField.show(false)
    }

    public getShape(params: {c: number}): Shape5D | undefined{
        this.shapeInput.cInput.value = params.c
        return this.shapeInput.value
    }


    public get disabled(): boolean{
        return this.shapeInput.disabled
    }

    public set disabled(value: boolean){
        this.shapeInput.disabled = value
    }
}