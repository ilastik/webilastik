import { BucketFs, FileSystem } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { PathInput } from "./path_input";

export class BucketFsInput{
    private readonly bucketNameInput: HTMLInputElement;
    private readonly prefixInput: PathInput;

    constructor(params: {parentElement: HTMLElement}){
        this.bucketNameInput = createInputParagraph({inputType: "text", parentElement: params.parentElement, label_text: "Bucket Name: "})

        createElement({tagName: "label", parentElement: params.parentElement, innerHTML: "Prefix: "})
        this.prefixInput = new PathInput({parentElement: params.parentElement})
    }

    public tryGetFileSystem(): FileSystem | undefined{
        let bucketName = this.bucketNameInput.value
        let prefix = this.prefixInput.value
        if(!bucketName || !prefix){
            return undefined
        }
        return new BucketFs({bucket_name: bucketName, prefix})
    }

    public static createLabeledFieldset(params: {legend: string} & ConstructorParameters<typeof BucketFsInput>[0]): BucketFsInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new BucketFsInput({...params, parentElement: fieldset})
    }
}