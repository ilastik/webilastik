import { vec3 } from "gl-matrix";
import { Shape5D, PrecomputedChunksScaleDataSink } from "../../client/ilastik";
import { createElement, getNowString } from "../../util/misc";
import { Path } from "../../util/parsed_url";
import { DataType, dataTypes, Scale } from "../../util/precomputed_chunks";
import { DataTypeSelector } from "./data_type_selector";
import { PathInput } from "./path_input";
import { SelectorWidget } from "./selector_widget";
import { Shape5DInput } from "./shape5d_input";
import { Vec3Input } from "./vec3_input";
import { encodings as precomputed_encodings } from "../../util/precomputed_chunks";
import { BucketFsInput } from "./bucket_fs_input";


export class PrecomputedChunksScaleDataSinkInput{
    private element: HTMLDivElement;
    private infoDirectoryPathInput: PathInput;
    private scaleKeyInput: PathInput;
    private fileSystemSelector: BucketFsInput;
    private dataTypeSelector: DataTypeSelector;
    private encoderSelector: SelectorWidget<"raw" | "jpeg" | "compressed_segmentation">;
    private tileShapeInput: Shape5DInput;
    private sinkShapeInput: Shape5DInput;
    private resolutionInput: Vec3Input;
    private voxelOffsetInput: Vec3Input;

    constructor(params: {
        parentElement: HTMLElement,
        tileShape?: Shape5D,
        voxelOffset?: vec3,
        forceShape?: Shape5D,
        forceResolution?: vec3,
    }){
        this.element = createElement({tagName: "div", parentElement: params.parentElement})

        this.fileSystemSelector = BucketFsInput.createLabeledFieldset({parentElement: params.parentElement, legend: "Data Proxy Bucket:"})

        let p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: p, innerHTML: "'info' Directory Path: "})
        this.infoDirectoryPathInput = new PathInput({parentElement: p, value: Path.parse(`/ilastik_export_${getNowString()}`)})

        p = createElement({tagName: "p", parentElement: this.element})
        createElement({tagName: "label", parentElement: p, innerHTML: "Scale Key: "})
        this.scaleKeyInput = new PathInput({parentElement: p, value: new Path({components: ["exported_data"]})})

        createElement({tagName: "label", parentElement: this.element, innerHTML: "Data Type: "})
        this.dataTypeSelector = new SelectorWidget<DataType>({
            parentElement: this.element,
            options: dataTypes.slice(),
            optionRenderer: (dt) => dt,
        })

        this.sinkShapeInput = Shape5DInput.createLabeledFieldset({
            parentElement: this.element,
            legend: "Output Shape:",
            disabled: params.forceShape !== undefined,
            value: params.forceShape,
        })

        this.tileShapeInput = Shape5DInput.createLabeledFieldset({
            parentElement: this.element,
            legend: "Tile Shape:",
            value: params.tileShape,
        })

        this.resolutionInput = new Vec3Input({
            parentElement: this.element, inlineFields: true, value: params.forceResolution
        })

        this.voxelOffsetInput = new Vec3Input({
            parentElement: this.element, inlineFields: true, value: params.forceResolution || vec3.fromValues(0, 0, 0)
        })

        createElement({tagName: "label", parentElement: this.element, innerHTML: "Encoding:"})
        this.encoderSelector = new SelectorWidget({
            parentElement: this.element,
            options: precomputed_encodings.filter(e => e == "raw"), //FIXME?
            optionRenderer: (opt) => opt,
        })
    }

    public get value(): PrecomputedChunksScaleDataSink | undefined{
        let filesystem = this.fileSystemSelector.tryGetFileSystem()
        let infoPath = this.infoDirectoryPathInput.value
        let dtype = this.dataTypeSelector.getSelection()
        let scaleKey = this.scaleKeyInput.value
        let sinkShape = this.sinkShapeInput.value
        let tileShape = this.tileShapeInput.value
        let resolution = this.resolutionInput.value
        let voxelOffset = this.voxelOffsetInput.value
        let encoding = this.encoderSelector.getSelection()

        if(!filesystem || !infoPath || !scaleKey || !sinkShape || !tileShape || !dtype || !resolution || !voxelOffset || !encoding){
            return undefined
        }

        return new PrecomputedChunksScaleDataSink({
            filesystem,
            info_dir: infoPath,
            dtype,
            num_channels: sinkShape.c,
            scale: new Scale(filesystem.getUrl().joinPath(infoPath), {
                key: scaleKey.raw,
                size: [sinkShape.x, sinkShape.y, sinkShape.z],
                resolution: [resolution[0], resolution[1], resolution[2]],
                voxel_offset: [voxelOffset[0], voxelOffset[1], voxelOffset[2]],
                chunk_sizes: [[tileShape.x, tileShape.y, tileShape.z]],
                encoding,
            })
        })
    }
}