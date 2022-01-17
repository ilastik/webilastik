import { Applet } from "../../client/applets/applet";
import { PrecomputedChunksScaleSink, Session } from "../../client/ilastik";
import { createElement, createInputParagraph } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { Encoding, ensureEncoding, encodings as precomputed_encodings} from "../../util/precomputed_chunks";
import { ensureJsonNumberTripplet, ensureJsonObject, ensureJsonString, ensureOptional, JsonValue, toJsonValue } from "../../util/serialization";
import { SelectorWidget } from "./selector_widget";


type State = {
    bucket_name?: string,
    prefix?: Path,
    voxel_offset?: [number, number, number],
    encoder: Encoding,
}

export class DataSinkSelectorWidget extends Applet<State>{
    public readonly element: HTMLDivElement;
    private state: State = {encoder: "raw"}

    private readonly bucketNameInput: HTMLInputElement;
    private readonly prefixInput: HTMLInputElement;
    private readonly encoderSelector: SelectorWidget<Encoding>;
    // private readonly dataTypeSelector: SelectorWidget<DataType>;

    constructor(params: {name: string, session: Session, parentElement: HTMLElement}){
        super({
            name: params.name,
            deserializer: (value: JsonValue) => {
                const valueObject = ensureJsonObject(value)
                return {
                    bucket_name: ensureOptional(ensureJsonString, valueObject.bucket_name),
                    prefix: ensureOptional((raw) => Path.parse(ensureJsonString(raw)), valueObject.prefix),
                    voxel_offset: ensureOptional(ensureJsonNumberTripplet, valueObject.voxel_offset),
                    encoder: ensureEncoding(ensureJsonString(valueObject.encoder)),
                    datasink: ensureOptional(PrecomputedChunksScaleSink.fromJsonValue, valueObject.datasink),
                }
            },
            session: params.session,
            onNewState: (state: State) => this.onNewState(state)
        })

        this.element = createElement({tagName: "div", parentElement: params.parentElement})

        this.bucketNameInput = createInputParagraph({
            inputType: "text", parentElement: this.element, label_text: "Bucket name: "
        })
        this.bucketNameInput.addEventListener("focusout", () => this.setParams())

        this.prefixInput = createInputParagraph({
            inputType: "text", parentElement: this.element, label_text: "Path: "
        })
        this.prefixInput.addEventListener("focusout", () => this.setParams())

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: p, innerHTML: "Compression: "})
        this.encoderSelector = new SelectorWidget({
            parentElement: p,
            options: precomputed_encodings.filter(e => e == "raw"), //FIXME?
            optionRenderer: (opt) => opt,
            onSelection: () => this.setParams(),
        })

        // p = createElement({tagName: "p", parentElement: this.element})
        // createElement({tagName: "label", parentElement: p, innerHTML: "Data Type: "})
        // this.dataTypeSelector = new SelectorWidget({
        //     parentElement: p,
        //     options: new Array<DataType>("float32"), //FIXME?
        //     optionRenderer: (opt) => opt,
        //     onSelection: () => {},
        // })
    }

    private setParams(){
        this.doRPC("set_params", {
            bucket_name: this.bucketNameInput.value || null,
            prefix: this.prefixInput.value || null,
            encoder: toJsonValue(this.encoderSelector.getSelection() || null),
        })
    }

    private onNewState(state: State){
        this.state = state
        this.bucketNameInput.value = state.bucket_name || ""
        this.prefixInput.value = state.prefix?.toString() || ""
        this.encoderSelector.setSelection({selection: this.state.encoder})
    }
}