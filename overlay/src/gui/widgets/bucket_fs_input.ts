import { BucketFSDto } from "../../client/dto";
import { createElement, createInputParagraph } from "../../util/misc";

export class BucketFsInput{
    private readonly bucketNameInput: HTMLInputElement;

    constructor(params: {
        parentElement: HTMLElement,
        bucketName?: string,
        required?: boolean,
        value?: BucketFSDto,
    }){
        let required = params.required === undefined ? true : params.required;
        this.bucketNameInput = createInputParagraph({
            inputType: "text", parentElement: params.parentElement, label_text: "Bucket Name: ", value: params.bucketName, required
        })

        if(params.value){
            this.value = params.value
        }
    }

    public get value(): BucketFSDto | undefined{
        let bucketName = this.bucketNameInput.value
        if(!bucketName){
            return undefined
        }
        return new BucketFSDto({bucket_name: bucketName})
    }

    public set value(fs: BucketFSDto | undefined){
        if(fs){
            this.bucketNameInput.value = fs.bucket_name
        }else{
            this.bucketNameInput.value = ""
        }
    }

    public static createLabeledFieldset(params: {legend: string} & ConstructorParameters<typeof BucketFsInput>[0]): BucketFsInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new BucketFsInput({...params, parentElement: fieldset})
    }
}