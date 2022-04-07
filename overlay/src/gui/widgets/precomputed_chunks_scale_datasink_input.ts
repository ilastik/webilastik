import { vec3 } from "gl-matrix";
import { Shape5D, PrecomputedChunksScaleDataSink } from "../../client/ilastik";
import { createElement, createFieldset, getNowString } from "../../util/misc";
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
        resolution?: vec3,
        voxelOffset?: vec3,
        disableShape?: boolean,
        disableTileShape?: boolean,
    }){
        let parentElement = params.parentElement
        this.fileSystemSelector = BucketFsInput.createLabeledFieldset({
            parentElement, legend: "Data Proxy Bucket:", bucketName: "hbp-image-service", prefix: Path.parse("ilastik_exports")
        })

        this.infoDirectoryPathInput = new PathInput({
            parentElement: createFieldset({parentElement, legend: "'info' Directory Path: "}), value: Path.parse(`/ilastik_export_${getNowString()}`)
        })

        this.scaleKeyInput = new PathInput({
            parentElement: createFieldset({parentElement, legend: "Scale Key: "}), value: new Path({components: ["exported_data"]})
        })

        let dataTypeFieldset = createFieldset({parentElement, legend: "Data Type: "})
        this.dataTypeSelector = new SelectorWidget<DataType>({
            parentElement: dataTypeFieldset,
            options: dataTypes.slice(),
            optionRenderer: (dt) => dt,
        })

        this.sinkShapeInput = Shape5DInput.createLabeledFieldset({
            parentElement,
            legend: "Output Shape:",
            disabled: params.disableShape,
        })

        this.tileShapeInput = Shape5DInput.createLabeledFieldset({
            parentElement,
            legend: "Tile Shape:",
            value: params.tileShape,
            disabled: params.disableTileShape
        })

        this.resolutionInput = Vec3Input.createLabeledFieldset({
            legend: "Resolution (nm)",
            parentElement,
            inlineFields: true,
            value: params.resolution,
        })

        this.voxelOffsetInput = Vec3Input.createLabeledFieldset({
            legend: "Voxel Offset:",
            parentElement,
            inlineFields: true,
            value: params.voxelOffset || vec3.fromValues(0,0,0)
        })

        let encodingFieldset = createFieldset({parentElement, legend: "Encoding:"})
        this.encoderSelector = new SelectorWidget({
            parentElement: encodingFieldset,
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

    public setParameters(params: {
        shape?: Shape5D,
        tileShape?: Shape5D,
        resolution?: vec3,
        voxelOffset?: vec3,
    }){
        if(params.shape){
            this.sinkShapeInput.value = params.shape
        }
        if(params.tileShape){
            this.tileShapeInput.value = params.tileShape
        }
        if(params.resolution){
            this.resolutionInput.value = params.resolution
        }
        if(params.voxelOffset){
            this.resolutionInput.value = params.voxelOffset
        }
    }

    public static createLabeled(
        params: {legend: string} & ConstructorParameters<typeof PrecomputedChunksScaleDataSinkInput>[0]
    ): PrecomputedChunksScaleDataSinkInput{
        let fieldset = createElement({tagName: "fieldset", parentElement: params.parentElement})
        createElement({tagName: "legend", parentElement: fieldset, innerHTML: params.legend})
        return new PrecomputedChunksScaleDataSinkInput({
            ...params, parentElement: fieldset
        })
    }
}