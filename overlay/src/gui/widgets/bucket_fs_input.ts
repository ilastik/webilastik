import { BucketFs } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { PathInput } from "./path_input";

export class BucketFsInput{
    private readonly bucketNameInput: HTMLInputElement;
    private readonly prefixInput: PathInput;

    constructor(params: {
        parentElement: HTMLElement, bucketName?: string, prefix?: Path, required?: boolean, value?: BucketFs
    }){
        let required = params.required === undefined ? true : params.required;
        this.bucketNameInput = createInputParagraph({
            inputType: "text", parentElement: params.parentElement, label_text: "Bucket Name: ", value: params.bucketName, required
        })

        createElement({tagName: "label", parentElement: params.parentElement, innerHTML: "Prefix: "})
        this.prefixInput = new PathInput({parentElement: params.parentElement, value: params.prefix, required})

        if(params.value){
            this.value = params.value
        }
    }

    public tryGetFileSystem(): BucketFs | undefined{
        let bucketName = this.bucketNameInput.value
        let prefix = this.prefixInput.value
        if(!bucketName || !prefix){
            return undefined
        }
        return new BucketFs({bucket_name: bucketName, prefix})
    }

    public get value(): BucketFs | undefined{
        return this.tryGetFileSystem()
    }

    public set value(fs: BucketFs | undefined){
        if(fs){
            this.bucketNameInput.value = fs.bucket_name
            this.prefixInput.value = fs.prefix
        }else{
            this.bucketNameInput.value = ""
            this.prefixInput.value = undefined
        }
    }

    public static createLabeledFieldset(params: {legend: string} & ConstructorParameters<typeof BucketFsInput>[0]): BucketFsInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new BucketFsInput({...params, parentElement: fieldset})
    }
}