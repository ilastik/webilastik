import { FsDataSink } from "../../client/ilastik";
import { NumberInput } from "./number_input";
import { PrecomputedChunksScale_DataSink_Input } from "./precomputed_chunks_scale_datasink_input";

export class SimpleSegmentationDatasinksInput{
    private readonly sinkInput: PrecomputedChunksScale_DataSink_Input;
    private readonly numberOfClassesInput: NumberInput;

    constructor(params: {parentElement: HTMLElement}){
        this.numberOfClassesInput = NumberInput.createLabeled({
            label: "Number of output classes: ", parentElement: params.parentElement, disabled: true
        })
        this.sinkInput = PrecomputedChunksScale_DataSink_Input.createLabeled({
            legend: "Simple Segmentation Output:",
            parentElement: params.parentElement,
            encoding: "raw",
            dataType: "float32",
            disableShape: true,
            disableTileShape: true,
            disableDataType: true,
            disableEncoding: true,
        })
    }

    public setParameters(params: {numberOfClasses?: number} & Parameters<PrecomputedChunksScale_DataSink_Input["setParameters"]>[0]){
        if(params.numberOfClasses){
            this.numberOfClassesInput.value = params.numberOfClasses
        }
        this.sinkInput.setParameters(params)
    }

    public get value(): FsDataSink[] | undefined{
        let referenceSink = this.sinkInput.value
        let numberOfClasses = this.numberOfClassesInput.value
        if(!referenceSink || !numberOfClasses){
            return undefined
        }

        let out = new Array<FsDataSink>()
        for(let i=0; i<numberOfClasses; i++){
            out.push(
                referenceSink.updatedWith({info_dir: referenceSink.info_dir.joinPath(`class_${i}`)})
            )
        }
        return out
    }
}