import { DataSinkUnion, Filesystem, Interval5D, PrecomputedChunksSink, Shape5D } from "../../client/ilastik";
import { Path } from "../../util/parsed_url";
import { DataType } from "../../util/precomputed_chunks";
import { CssClasses } from "../css_classes";
import { Select } from "./input_widget";
import { ErrorPopupWidget } from "./popup";
import { TabsWidget } from "./tabs_widget";
import { PathInput } from "./value_input_widget";
import { Div, Label, Paragraph, Span } from "./widget";


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

export class DatasinkConfigWidget{
    public readonly element: Div;
    private readonly tabs: TabsWidget<DatasinkInputForm>;

    constructor(params: {parentElement: HTMLElement}){
        this.tabs = new TabsWidget({
            parentElement: params.parentElement,
            tabBodyWidgets: new Map<string, DatasinkInputForm>([
                ["Precomputed Chunks", new PrecomputedChunksDatasinkConfigWidget({parentElement: undefined, disableEncoding: true})],
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
    }): PrecomputedChunksSink | undefined{
        return this.tabs.current.widget.tryMakeDataSink(params)
    }
}