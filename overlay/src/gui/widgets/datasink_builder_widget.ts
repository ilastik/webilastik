import { Filesystem, Interval5D, PrecomputedChunksSink, Shape5D } from "../../client/ilastik";
import { createElement } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { DataType } from "../../util/precomputed_chunks";
import { PathInput } from "./path_input";
import { ErrorPopupWidget } from "./popup";
import { PopupSelect } from "./selector_widget";
import { TabsWidget } from "./tabs_widget";


export interface IDatasinkConfigWidget{
    readonly element: HTMLElement;

    tryMakeDataSink(params: {
        filesystem: Filesystem,
        path: Path,
        interval: Interval5D,
        dtype: DataType,
        resolution: [number, number, number],
        tile_shape: Shape5D,
    }): PrecomputedChunksSink | undefined;
}

export class PrecomputedChunksDatasinkConfigWidget implements IDatasinkConfigWidget{
    public readonly element: HTMLDivElement;
    public readonly encoderSelector: PopupSelect<"raw" | "jpeg">;
    public readonly scaleKeyInput: PathInput;

    constructor(params: {parentElement: HTMLElement | undefined, disableEncoding: boolean}){
        this.element = createElement({tagName: "div", parentElement: params.parentElement})

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: p, innerText: "Scale Key: "})
        this.scaleKeyInput = new PathInput({
            parentElement: p,
            value: new Path({components: ["exported_data"]})
        })

        p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: p, innerText: "Encoding: "})
        this.encoderSelector = new PopupSelect<"raw" | "jpeg">({
            popupTitle: "Select an encoding",
            parentElement: p,
            options: ["raw", "jpeg"], //FIXME?
            optionRenderer: (args) => createElement({tagName: "span", parentElement: args.parentElement, innerText: args.option}),
            disabled: params.disableEncoding,
        })
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


export class DummySinkParamsInput implements IDatasinkConfigWidget{
    public readonly element: HTMLDivElement;

    constructor(params: {parentElement: HTMLElement | undefined}){
        this.element = createElement({tagName: "div", parentElement: params.parentElement, innerText: "BLAS"})
    }

    public tryMakeDataSink(_params: {
        filesystem: Filesystem,
        path: Path,
        interval: Interval5D,
        dtype: DataType,
        resolution: [number, number, number],
        tile_shape: Shape5D,
    }): PrecomputedChunksSink | undefined{
        return undefined
    }
}

export class DatasinkConfigWidget{
    public readonly element: HTMLDivElement;
    private readonly tabs: TabsWidget<IDatasinkConfigWidget>;

    constructor(params: {parentElement: HTMLElement}){
        this.tabs = new TabsWidget({
            parentElement: params.parentElement,
            tabBodyWidgets: new Map<string, IDatasinkConfigWidget>([
                ["Precomputed Chunks", new PrecomputedChunksDatasinkConfigWidget({parentElement: undefined, disableEncoding: true})],
                ["Dummy", new DummySinkParamsInput({parentElement: undefined})],
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