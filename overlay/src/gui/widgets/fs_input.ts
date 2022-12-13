import { BucketFs, Filesystem } from "../../client/ilastik";
import { createElement, createInput } from "../../util/misc";
import { TabsWidget } from "./tabs_widget";


export interface IFsInputWidget<FS extends Filesystem>{
    readonly element: HTMLElement;
    readonly value: FS | undefined;
    required: boolean;
}

export class BucketFsInputWidget implements IFsInputWidget<BucketFs>{
    public readonly element: HTMLSpanElement;
    private readonly bucketNameInput: HTMLInputElement;

    constructor(params: {
        parentElement: HTMLElement | undefined,
        bucketName?: string,
        required?: boolean,
        value?: BucketFs,
    }){
        let required = params.required === undefined ? false : params.required;
        this.element = createElement({tagName: "span", parentElement: params.parentElement})
        createElement({tagName: "label", innerText: "Bucket Name: ", parentElement: this.element})
        this.bucketNameInput = createInput({
            inputType: "text", parentElement: this.element, value: params.bucketName, required
        })

        if(params.value){
            this.value = params.value
        }
    }

    public get value(): BucketFs | undefined{
        let bucketName = this.bucketNameInput.value
        if(!bucketName){
            return undefined
        }
        return new BucketFs({bucket_name: bucketName})
    }

    public set value(fs: BucketFs | undefined){
        if(fs){
            this.bucketNameInput.value = fs.bucket_name
        }else{
            this.bucketNameInput.value = ""
        }
    }

    public get required(): boolean{
        return this.bucketNameInput.required
    }

    public set required(val: boolean){
        this.bucketNameInput.required = val
    }

}

export class FsInputWidget{
    tabs: TabsWidget<IFsInputWidget<Filesystem>>;
    private _required: boolean;

    constructor(params: {
        parentElement: HTMLElement, defaultBucketName?: string, required?: boolean
    }){
        this._required = params.required === undefined ? false : params.required;
        this.tabs = new TabsWidget({
            parentElement: params.parentElement,
            onSwitch: (_, activeWidget, allWidgets) => this.refreshRequiredProperty(activeWidget, allWidgets),
            tabBodyWidgets: new Map<string, IFsInputWidget<Filesystem>>([
                [
                    "Data-Proxy",
                    new BucketFsInputWidget({parentElement: undefined, bucketName: params.defaultBucketName})
                ],
            ])
        })
        const fsWidgets = Array.from(this.tabs.getTabBodyWidgets())
        this.refreshRequiredProperty(fsWidgets[0], fsWidgets)
    }

    public get value(): Filesystem | undefined{
        return this.tabs.current.widget.value
    }

    private refreshRequiredProperty = (currentWidget: IFsInputWidget<Filesystem>, allWidgets: IFsInputWidget<Filesystem>[]) => {
        if(!this._required){
            allWidgets.forEach(widget => {widget.required = false})
            return
        }

        for(const widget of allWidgets){
            if(widget == currentWidget ){
                widget.required = true
            }else{
                widget.required = false
            }
        }
    }
}