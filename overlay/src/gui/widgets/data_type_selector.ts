import { DataType, dataTypes } from "../../util/precomputed_chunks";
import { SelectorWidget } from "./selector_widget";

export class DataTypeSelector extends SelectorWidget<DataType>{
    constructor({parentElement, onSelection=() => {} }: {
        parentElement: HTMLElement,
        onSelection?: (selection: DataType, selection_index: number) => void,
    }){
        super({
            parentElement,
            options: dataTypes.slice(),
            optionRenderer: (dt) => dt,
            onSelection
        })
    }
}