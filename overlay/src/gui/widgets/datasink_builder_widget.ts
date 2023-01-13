import { Bzip2Compressor, DataSinkUnion, Filesystem, GzipCompressor, Interval5D, N5DataSink, PrecomputedChunksSink, RawCompressor, Shape5D, XzCompressor } from "../../client/ilastik";
import { assertUnreachable } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { DataType } from "../../util/precomputed_chunks";
import { CssClasses } from "../css_classes";
import { Select } from "./input_widget";
import { ErrorPopupWidget } from "./popup";
import { TabsWidget } from "./tabs_widget";
import { AxesKeysInput, NumberInput, PathInput } from "./value_input_widget";
import { ContainerWidget, Div, Label, Paragraph, Span, TagName } from "./widget";


abstract class DatasinkInputForm extends Div{
    abstract tryMakeDataSink(params: {
        filesystem: Filesystem,
        path: Path,
        interval: Interval5D,
        dtype: DataType,
        resolution: [number, number, number],
        tile_shape: Shape5D,
    }): DataSinkUnion | undefined;
}

class PrecomputedChunksDatasinkConfigWidget extends DatasinkInputForm{
    public readonly encoderSelector: Select<"raw" | "jpeg">;
    public readonly scaleKeyInput: PathInput;

    constructor(params: {parentElement: HTMLElement | undefined, disableEncoding: boolean}){
        const scaleKeyInput = new PathInput({
            parentElement: undefined,
            value: new Path({components: ["exported_data"]})
        })
        const encoderSelector = new Select<"raw" | "jpeg">({
            popupTitle: "Select an encoding",
            parentElement: undefined,
            options: ["raw", "jpeg"], //FIXME?
            renderer: (opt) => new Span({parentElement: undefined, innerText: opt}),
            disabled: params.disableEncoding,
        })
        super({...params, children: [
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({innerText: "Scale Key: ", parentElement: undefined}),
                scaleKeyInput,
            ]}),
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({innerText: "Encoding: ", parentElement: undefined}),
                encoderSelector,
            ]})
        ]})
        this.scaleKeyInput = scaleKeyInput
        this.encoderSelector = encoderSelector
    }

    public tryMakeDataSink(params: {
        filesystem: Filesystem,
        path: Path,
        interval: Interval5D,
        dtype: DataType,
        resolution: [number, number, number],
        tile_shape: Shape5D,
    }): PrecomputedChunksSink | undefined{
        const encoding = this.encoderSelector.value;
        const scaleKey = this.scaleKeyInput.value;
        if(!scaleKey){
            new ErrorPopupWidget({message: "Missing some paramenters"})
            return
        }

        return new PrecomputedChunksSink({
            filesystem: params.filesystem,
            path: params.path,
            scale_key: scaleKey,
            dtype: params.dtype,
            encoding: encoding,
            interval: params.interval,
            resolution: params.resolution,
            tile_shape: params.tile_shape,
        })
    }
}

class N5RawCompressotInput{
    public getValue(): RawCompressor{
        return new RawCompressor()
    }
    public setValue(_value: RawCompressor){
    }
}

class N5GzipCompressorInput{
    private numberInput: NumberInput;
    constructor(params: {parentElement: ContainerWidget<TagName>, value?: GzipCompressor}){
        new Label({parentElement: params.parentElement, innerText: "Level: "})
        this.numberInput = new NumberInput({
            parentElement: params.parentElement,
            value: params.value === undefined ? 9 : params.value.level,
            min: 0,
            max: 9,
            step: 1
        })
    }
    public getValue(): GzipCompressor | undefined{
        let level = this.numberInput.value
        return level === undefined ? undefined : new GzipCompressor({level})
    }
    public setValue(value: GzipCompressor | undefined){
        this.numberInput.value = value?.level
    }
}

class N5Bzip2CompressorInput{
    private numberInput: NumberInput;
    constructor(params: {parentElement: ContainerWidget<TagName>, value?: Bzip2Compressor}){
        new Label({parentElement: params.parentElement, innerText: "Compression Level: "})
        this.numberInput = new NumberInput({
            parentElement: params.parentElement,
            value: params.value === undefined ? 9 : params.value.compressionLevel,
            min: 1,
            max: 9,
            step: 1
        })
    }
    public getValue(): Bzip2Compressor | undefined{
        let compressionLevel = this.numberInput.value
        return compressionLevel === undefined ? undefined : new Bzip2Compressor({compressionLevel})
    }
    public setValue(value: Bzip2Compressor | undefined){
        this.numberInput.value = value?.compressionLevel
    }
}

class N5XzCompressorInput{
    private numberInput: NumberInput;
    constructor(params: {parentElement: ContainerWidget<TagName>, value?: XzCompressor}){
        new Label({parentElement: params.parentElement, innerText: "Preset: "})
        this.numberInput = new NumberInput({
            parentElement: params.parentElement,
            value: params.value === undefined ? 9 : params.value.preset,
            min: 1,
            max: 9,
            step: 1
        })
    }
    public getValue(): XzCompressor | undefined{
        let preset = this.numberInput.value;
        return preset === undefined ? undefined : new XzCompressor({preset})
    }
    public setValue(value: XzCompressor | undefined){
        this.numberInput.value = value?.preset
    }
}

class N5DatasinkConfigWidget extends DatasinkInputForm{
    private compressorParameterContainer: Paragraph;
    private compressorInput: N5GzipCompressorInput | N5Bzip2CompressorInput | N5XzCompressorInput | N5RawCompressotInput
    private readonly axisKeysInput: AxesKeysInput;

    constructor(params: {parentElement: HTMLElement | undefined, disabled?: boolean}){
        let compressorParameterContainer: Paragraph;
        let axisKeysInput: AxesKeysInput;
        super({...params, children: [
            new Paragraph({parentElement: undefined, children: [
                new Label({parentElement: undefined, innerText: "C Axis Keys: "}),
                axisKeysInput = new AxesKeysInput({parentElement: undefined, value: ["t", "z", "y", "x", "c"]}),
            ]}),
            new Paragraph({parentElement: undefined, cssClasses: [CssClasses.ItkInputParagraph], children: [
                new Label({parentElement: undefined, innerText: "Compression scheme: "}),
                new Select<"raw" | "gzip" | "bzip" | "xz">({
                    popupTitle: "Select a compression mode",
                    parentElement: undefined,
                    options: ["raw", "gzip", "bzip", "xz"],
                    renderer: (opt) => new Span({parentElement: undefined, innerText: opt}),
                    disabled: params.disabled,
                    onChange: (val) => {
                        this.compressorParameterContainer.clear()
                        if(val == "raw"){
                            this.compressorInput = new N5RawCompressotInput()
                        }else if(val == "gzip"){
                            this.compressorInput = new N5GzipCompressorInput({parentElement: this.compressorParameterContainer})
                        }else if(val == "bzip"){
                            this.compressorInput = new N5Bzip2CompressorInput({parentElement: this.compressorParameterContainer})
                        }else if(val == "xz"){
                            this.compressorInput = new N5XzCompressorInput({parentElement: this.compressorParameterContainer})
                        }else{
                            assertUnreachable(val)
                        }
                    }
                }),
            ]}),
            compressorParameterContainer = new Paragraph({parentElement: undefined}),
        ]})
        this.compressorParameterContainer = compressorParameterContainer;
        this.compressorInput = new N5RawCompressotInput()
        this.axisKeysInput = axisKeysInput;
    }

    public tryMakeDataSink(params: {
        filesystem: Filesystem,
        path: Path,
        interval: Interval5D,
        dtype: DataType,
        resolution: [number, number, number],
        tile_shape: Shape5D,
    }): N5DataSink | undefined{
        const axiskeys = this.axisKeysInput.value
        const compressor = this.compressorInput.getValue()
        if(!axiskeys || !compressor){
            return undefined
        }
        return new N5DataSink({
            filesystem: params.filesystem,
            path: params.path,
            dtype: params.dtype,
            compressor,
            c_axiskeys: axiskeys.join(""),
            interval: params.interval,
            resolution: params.resolution,
            tile_shape: params.tile_shape,
        })
    }
}

export class DatasinkConfigWidget{
    public readonly element: Div;
    private readonly tabs: TabsWidget<DatasinkInputForm>;

    constructor(params: {parentElement: HTMLElement}){
        this.tabs = new TabsWidget({
            parentElement: params.parentElement,
            tabBodyWidgets: new Map<string, DatasinkInputForm>([
                ["Precomputed Chunks", new PrecomputedChunksDatasinkConfigWidget({parentElement: undefined, disableEncoding: true})],
                ["N5", new N5DatasinkConfigWidget({parentElement: undefined})],
            ])
        })
        this.element = this.tabs.element
    }

    public tryMakeDataSink(params: {
        filesystem: Filesystem,
        path: Path,
        interval: Interval5D,
        dtype: DataType,
        resolution: [number, number, number],
        tile_shape: Shape5D,
    }): DataSinkUnion | undefined{
        return this.tabs.current.widget.tryMakeDataSink(params)
    }
}