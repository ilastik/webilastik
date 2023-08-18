import { Filesystem } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { FsInputWidget } from "./fs_input";
import { PathInput, ValueInputWidget } from "./value_input_widget";
import { Div, Label, Paragraph } from "./widget";
import { InputWidgetParams } from "./input_widget";
import { ExportPattern, ReplacementParams } from "../../util/export_pattern";


export class ExportPatternInput extends ValueInputWidget<ExportPattern | undefined, "text">{
    constructor(params: InputWidgetParams & {value?: ExportPattern}){
        super({...params, inputType: "text", cssClasses: [CssClasses.ItkCharacterInput].concat(params.cssClasses || [])})
        this.element.addEventListener("input", () => {
            const parsed = ExportPattern.parse(this.raw)
            this.element.setCustomValidity(parsed instanceof Error ? parsed.message : "")
            this.element.reportValidity()
        })
        this.value = params.value
    }

    public get value(): ExportPattern | undefined{
        const out = ExportPattern.parse(this.raw)
        return out instanceof Error ? undefined : out
    }

    public set value(pattern: ExportPattern | undefined){
        this.raw = pattern ? pattern.toString() : ""
    }
}

export class FileLocationInputWidget{
    public readonly fsInput: FsInputWidget;
    public readonly pathInput: PathInput;

    constructor(params: {
        parentElement: HTMLElement,
        defaultBucketName?: string,
        defaultPath?: Path,
        required?: boolean,
        filesystemChoices: Array<"http" | "data-proxy">
    }){
        new Div({parentElement: params.parentElement, children: [

        ]})
        this.fsInput = new FsInputWidget({
            parentElement: params.parentElement, defaultBucketName: params.defaultBucketName, filesystemChoices: params.filesystemChoices
        })
        new Paragraph({parentElement: params.parentElement, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Label({innerText: "Path: ", parentElement: undefined}),
            this.pathInput = new PathInput({parentElement: undefined, value: params.defaultPath}),
        ]})
    }

    public get value(): {filesystem: Filesystem, path: Path} | undefined{
        const filesystem = this.fsInput.value
        const path = this.pathInput.value
        if(!filesystem || !path){
            return undefined
        }
        return {filesystem, path}
    }
}

export class FileLocationPatternInputWidget{
    public readonly fsInput: FsInputWidget;
    public readonly pathPatternInput: ExportPatternInput;

    constructor(params: {
        parentElement: HTMLElement,
        defaultBucketName?: string,
        defaultPathPattern?: ExportPattern,
        required?: boolean,
        filesystemChoices: Array<"http" | "data-proxy">,
        tooltip?: string,
    }){
        this.fsInput = new FsInputWidget({
            parentElement: params.parentElement,
            defaultBucketName: params.defaultBucketName,
            filesystemChoices: params.filesystemChoices,
        })
        new Paragraph({parentElement: params.parentElement, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Label({innerText: "Path pattern: ", parentElement: undefined, title: params.tooltip}),
            this.pathPatternInput = new ExportPatternInput({value: params.defaultPathPattern, parentElement: undefined, title: params.tooltip})
        ]})

    }

    public tryGetLocation(params: ReplacementParams): {filesystem: Filesystem, path: Path} | undefined{
        const filesystem = this.fsInput.value
        const pattern = this.pathPatternInput.value
        if(!pattern){
            return undefined
        }
        const path = pattern.expanded(params)
        if(!filesystem || !(path instanceof Path)){
            return undefined
        }
        return {filesystem, path}
    }
}
