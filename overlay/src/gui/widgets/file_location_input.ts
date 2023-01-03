import { Filesystem } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { FsInputWidget } from "./fs_input";
import { PathInput } from "./value_input_widget";
import { Div, Label, Paragraph } from "./widget";
import { InputWidget, InputWidgetParams } from "./input_widget";
import { getNowString } from "../../util/misc";

export class PathPatternInput extends InputWidget<"text">{
    constructor(params: InputWidgetParams & {value?: string}){ //FIXME: string really?
        super({...params, inputType: "text", cssClasses: [CssClasses.ItkCharacterInput].concat(params.cssClasses || [])})
        this.element.value = params.value || ""
        this.element.addEventListener("change", () => {
            const value = this.tryGetPath({item_index: 1, name: "_name_", output_type: "_output_type_"})
            this.element.setCustomValidity(value instanceof Error ? value.message : "")
        })
    }

    public tryGetPath(params:{
        item_index: number,
        name: string,
        output_type: string
    }): Path | undefined | Error{
        if(!this.element.value){
            return undefined
        }
        let replaced = this.element.value
            .replace(/\{item_index\}/g, params.item_index.toString())
            .replace(/\{name\}/g, params.name.toString().replace(/ /g, "_")) //FIXME: use safer escape?
            .replace(/\{output_type\}/g, params.output_type.toString().replace(/ /g, "_")) //FIXME: use safer escape?
            .replace(/\{timestamp\}/g, getNowString())

        for(const brace of "{}"){
            let braceIndex = replaced.indexOf(brace)
            if(braceIndex >= 0){
                return new Error(`Unexpected '${brace}'`)
            }
        }
        //FIXME: parse should check for bad paths
        let parsed = Path.parse(replaced);
        if(parsed instanceof Error){
            return new Error(`Bad path`)
        }
        return parsed
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
    public readonly pathPatternInput: PathPatternInput;

    constructor(params: {
        parentElement: HTMLElement,
        defaultBucketName?: string,
        defaultPathPattern?: string,
        required?: boolean,
        filesystemChoices: Array<"http" | "data-proxy">,
    }){
        this.fsInput = new FsInputWidget({
            parentElement: params.parentElement, defaultBucketName: params.defaultBucketName, filesystemChoices: params.filesystemChoices
        })
        new Paragraph({parentElement: params.parentElement, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Label({innerText: "Path pattern: ", parentElement: undefined}),
            this.pathPatternInput = new PathPatternInput({value: params.defaultPathPattern, parentElement: undefined})
        ]})

    }

    public tryGetLocation(params: {item_index: number, name: string, output_type: string}): {filesystem: Filesystem, path: Path} | undefined{
        const filesystem = this.fsInput.value
        const path = this.pathPatternInput.tryGetPath(params)
        if(!filesystem || !(path instanceof Path)){
            return undefined
        }
        return {filesystem, path}
    }
}
