import { BucketFs, Filesystem, HttpFs } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { TabsWidget } from "./tabs_widget";
import { BucketFsInput, HttpFsInput } from "./value_input_widget";
import { ContainerWidget, Div, Label, WidgetParams } from "./widget";


abstract class FsInputForm extends Div{
    public abstract readonly fs: Filesystem | undefined;
    public abstract required: boolean
}

class BucketFsInputForm extends FsInputForm{
    public readonly fsInput: BucketFsInput;

    constructor(params: WidgetParams & {value?: BucketFs}){
        let fsInput = new BucketFsInput({parentElement: undefined, value: params.value})
        super({...params, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Label({parentElement: undefined, innerText: "Data-Proxy Bucket Name: "}),
            fsInput
        ]})
        this.fsInput = fsInput
    }
    public get fs(): BucketFs | undefined{
        return this.fsInput.value
    }
    public get required(): boolean{
        return this.fsInput.required
    }
    public set required(val: boolean){
        this.fsInput.required = val
    }
}

class HttpFsInputForm extends FsInputForm{
    public readonly fsInput: HttpFsInput;

    constructor(params: WidgetParams & {value?: HttpFs}){
        let fsInput = new HttpFsInput({parentElement: undefined, value: params.value})
        super({...params, cssClasses: [CssClasses.ItkInputParagraph], children: [
            new Label({parentElement: undefined, innerText: "Base Url: "}),
            fsInput
        ]})
        this.fsInput = fsInput
    }
    public get fs(): HttpFs | undefined{
        return this.fsInput.value
    }
    public get required(): boolean{
        return this.fsInput.required
    }
    public set required(val: boolean){
        this.fsInput.required = val
    }
}

export class FsInputWidget{
    tabs: TabsWidget<string, FsInputForm>;
    private _required: boolean;

    constructor(params: {
        parentElement: ContainerWidget<any> | HTMLElement, defaultBucketName?: string, required?: boolean, filesystemChoices: Array<"http" | "data-proxy">
    }){
        this._required = params.required === undefined ? false : params.required;
        let filesystemWidgets = new Array<[string, FsInputForm]>()

        if(params.filesystemChoices.includes("data-proxy")){
            filesystemWidgets.push(
                [
                    "Data-Proxy",
                    new BucketFsInputForm({
                        parentElement: undefined,
                        value: params.defaultBucketName ? new BucketFs({bucket_name: params.defaultBucketName}) : undefined
                    })
                ]
            )
        }

        if(params.filesystemChoices.includes("http")){
            filesystemWidgets.push(
                [
                    "HTTP",
                    new HttpFsInputForm({
                        parentElement: undefined,
                        value: new HttpFs({protocol: "https", hostname: "app.ilastik.org", path: Path.parse("/public/images")}),
                    })
                ],
            )
        }

        this.tabs = new TabsWidget({
            parentElement: params.parentElement,
            onSwitch: (_, activeWidget, allWidgets) => this.refreshRequiredProperty(activeWidget, allWidgets),
            tabBodyWidgets: new Map<string, FsInputForm>(filesystemWidgets)
        })
        const fsWidgets = Array.from(this.tabs.getTabBodyWidgets())
        this.refreshRequiredProperty(fsWidgets[0], fsWidgets)
    }

    public get value(): Filesystem | undefined{
        return this.tabs.current.widget.fs
    }

    private refreshRequiredProperty = (currentWidget: FsInputForm, allWidgets: FsInputForm[]) => {
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