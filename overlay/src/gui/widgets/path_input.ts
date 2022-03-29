import { createInput } from "../../util/misc";
import { Path } from "../../util/parsed_url";

export class PathInput{
    private inputElement: HTMLInputElement;
    constructor(params: {parentElement: HTMLElement, value?: Path}){
        this.inputElement = createInput({inputType: "text", parentElement: params.parentElement})
        if(params.value){
            this.inputElement.value = params.value.raw
        }
    }

    public get value(): Path | undefined{
        let raw = this.inputElement.value
        if(!raw){
            return undefined
        }
        return Path.parse(raw) //FIXME: bad path?
    }
}