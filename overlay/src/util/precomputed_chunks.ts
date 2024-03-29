import { Url } from "../util/parsed_url";
import { ensureJsonArray, ensureJsonNumberTripplet, ensureJsonObject, ensureJsonString, JsonObject, JsonValue } from "../util/serialization"


export const encodings = ["raw", "jpeg", "compressed_segmentation"] as const;
export type Encoding = typeof encodings[number];
export function ensureEncoding(value: string): Encoding{
    const variant = encodings.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid encoding: ${value}`)
    }
    return variant
}

export class Scale{
    public readonly key: string
    public readonly size: [number, number, number]
    public readonly resolution: [number, number, number]
    public readonly voxel_offset: [number, number, number]
    public readonly chunk_sizes: [number, number, number][]
    public readonly encoding: Encoding

    constructor(params: {
        key: string,
        size: [number, number, number],
        resolution: [number, number, number],
        voxel_offset: [number, number, number],
        chunk_sizes: Array<[number, number, number]>,
        encoding: Encoding,
    }){
        this.key = params.key.replace(/^\//, "")
        this.size = params.size
        this.resolution = params.resolution
        this.voxel_offset = params.voxel_offset
        this.chunk_sizes = params.chunk_sizes
        this.encoding = params.encoding
    }

    public static fromJsonValue(value: JsonValue){
        const obj = ensureJsonObject(value)
        return new Scale({
            key: ensureJsonString(obj.key),
            size: ensureJsonNumberTripplet(obj.size),
            resolution: ensureJsonNumberTripplet(obj.resolution),
            voxel_offset: obj.voxel_offset === undefined ? [0,0,0] : ensureJsonNumberTripplet(obj.voxel_offset),
            chunk_sizes: ensureJsonArray(obj.chunk_sizes).map(element => ensureJsonNumberTripplet(element)),
            encoding: ensureEncoding(ensureJsonString(obj.encoding)),
        })
    }

    public toJsonValue(): JsonObject{
        return {
            key: this.key,
            size: this.size,
            resolution: this.resolution,
            voxel_offset: this.voxel_offset,
            chunk_sizes: this.chunk_sizes,
            encoding: this.encoding,
        }
    }
}


const types = ["image", "segmentation"] as const;
export type Type = typeof types[number];
export function ensureType(value: string): Type{
    const variant = types.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid type: ${value}`)
    }
    return variant
}

export const dataTypes = ["uint8", "uint16", "uint32", "uint64", "int64", "float32"] as const;
export type DataType = typeof dataTypes[number];
export function ensureDataType(value: string): DataType{
    const variant = dataTypes.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid data type: ${value}`)
    }
    return variant
}

export class PrecomputedChunks{
    public readonly url: Url;
    public readonly type: Type;
    public readonly data_type: DataType;
    public readonly num_channels: number;
    public readonly scales: Scale[];

    constructor(params: {
        url: Url,
        type: Type,
        data_type: DataType,
        num_channels: number,
        scales: Array<Scale>,
    }){
        this.url = params.url
        this.type = params.type
        this.data_type = params.data_type
        this.num_channels = params.num_channels
        this.scales = params.scales
    }
}