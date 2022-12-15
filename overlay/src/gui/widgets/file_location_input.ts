import { Filesystem } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { FsInputWidget } from "./fs_input";
import { PathInput } from "./value_input_widget";

export const replacements = ["item_index", "name"] as const;
export type Replacement = typeof replacements[number];

export class PathPatternInput{
    public readonly element: HTMLInputElement;
    private _raw_value: string | undefined;

    constructor(params: {
        parentElement: HTMLElement | undefined,
        pattern?: string,
    }){
        this.element = createInput({inputType: "text", parentElement: params.parentElement, value: params.pattern})
        this.element.addEventListener("change", () => {
            const raw = this.element.value.trim()
            this._raw_value = undefined
            this.element.setCustomValidity("")
            if(!raw){
                return
            }
            let cleaned = raw
            for(const replacement of replacements){
                cleaned = cleaned.replace(`{${replacement}}`, `_${replacement}_`)
            }

            for(const brace of "{}"){
                let braceIndex = cleaned.indexOf(brace)
                if(braceIndex >= 0){
                    this.element.setCustomValidity(`Unexpected '${brace}' at ${braceIndex + 1}`)
                    return
                }
            }

            //FIXME: parse should check for bad paths
            let parsed = Path.parse(cleaned);
            if(parsed instanceof Error){
                this.element.setCustomValidity(`Bad path: ${parsed.message}`)
                return
            }
            this._raw_value = raw
        })
    }

    public tryGetPath(params:{
        item_index: number,
        name: string,
    }): Path | undefined{
        if(!this._raw_value){
            return undefined
        }
        let out = this._raw_value
            .replace(/\{item_index\}/, params.item_index.toString())
            .replace(/\{name\}/, params.name.toString())
        return Path.parse(out)
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
    }){
        this.fsInput = new FsInputWidget({
            parentElement: params.parentElement, defaultBucketName: params.defaultBucketName,
        })
        createElement({tagName: "label", innerText: "Path: ", parentElement: params.parentElement})
        this.pathInput = new PathInput({parentElement: params.parentElement, value: params.defaultPath})
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
    }){
        this.fsInput = new FsInputWidget({
            parentElement: params.parentElement, defaultBucketName: params.defaultBucketName,
        })
        createElement({tagName: "label", innerText: "Path pattern: ", parentElement: params.parentElement})
        this.pathPatternInput = new PathPatternInput({parentElement: params.parentElement, pattern: params.defaultPathPattern})
    }

    public tryGetLocation(params: {item_index: number, name: string}): {filesystem: Filesystem, path: Path} | undefined{
        const filesystem = this.fsInput.value
        const path = this.pathPatternInput.tryGetPath(params)
        if(!filesystem || !path){
            return undefined
        }
        return {filesystem, path}
    }
}
