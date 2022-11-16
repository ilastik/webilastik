import { BucketFSDto } from "../../client/dto";
import { createElement, createInputParagraph } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { PathInput } from "./path_input";

export class BucketFsInput{
    private readonly bucketNameInput: HTMLInputElement;
    private readonly prefixInput: PathInput;

    constructor(params: {
        parentElement: HTMLElement,
        bucketName?: string,
        prefix?: Path,
        required?: boolean,
        value?: BucketFSDto,
        hidePrefix?: boolean,
    }){
        let required = params.required === undefined ? true : params.required;
        this.bucketNameInput = createInputParagraph({
            inputType: "text", parentElement: params.parentElement, label_text: "Bucket Name: ", value: params.bucketName, required
        })

        let prefixDisplay = params.hidePrefix === undefined || params.hidePrefix == false ? "block" : "none"
        let prefixContainer = createElement({tagName: "p", parentElement: params.parentElement, inlineCss: {display: prefixDisplay}})
        createElement({tagName: "label", parentElement: prefixContainer, innerHTML: "Prefix: "})
        this.prefixInput = new PathInput({parentElement: prefixContainer, value: params.prefix, required})

        if(params.value){
            this.value = params.value
        }
    }

    public get value(): BucketFSDto | undefined{
        let bucketName = this.bucketNameInput.value
        let prefix = this.prefixInput.value
        if(!bucketName || !prefix){
            return undefined
        }
        return new BucketFSDto({bucket_name: bucketName, prefix: prefix.raw})
    }

    public set value(fs: BucketFSDto | undefined){
        if(fs){
            this.bucketNameInput.value = fs.bucket_name
            this.prefixInput.value = Path.parse(fs.prefix)
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