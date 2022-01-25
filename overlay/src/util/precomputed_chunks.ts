import { Url } from "../util/parsed_url";
import { ensureJsonArray, ensureJsonNumber, ensureJsonNumberTripplet, ensureJsonObject, ensureJsonString, JsonObject, JsonValue } from "../util/serialization"


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
    public readonly base_url: Url
    public readonly key: string
    public readonly size: [number, number, number]
    public readonly resolution: [number, number, number]
    public readonly voxel_offset: [number, number, number]
    public readonly chunk_sizes: [number, number, number][]
    public readonly encoding: Encoding

    constructor(base_url: Url, params: {
        key: string,
        size: [number, number, number],
        resolution: [number, number, number],
        voxel_offset: [number, number, number],
        chunk_sizes: Array<[number, number, number]>,
        encoding: Encoding,
    }){
        this.base_url = base_url
        this.key = params.key.replace(/^\//, "")
        this.size = params.size
        this.resolution = params.resolution
        this.voxel_offset = params.voxel_offset
        this.chunk_sizes = params.chunk_sizes
        this.encoding = params.encoding
    }

    public getChunkUrl(interval: {x: [number, number], y: [number, number], z: [number, number]}): Url{
        return this.base_url.joinPath(
            `${this.key}/${interval.x[0]}-${interval.x[1]}_${interval.y[0]}-${interval.y[1]}_${interval.z[0]}-${interval.z[1]}`
        )
    }

    public static fromJsonValue(base_url: Url, value: JsonValue){
        const obj = ensureJsonObject(value)
        return new Scale(base_url, {
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

const dataTypes = ["uint8", "uint16", "uint32", "uint64", "float32"] as const;
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

    public static async tryFromUrl(url: Url): Promise<PrecomputedChunks | undefined>{
        if(url.datascheme !== "precomputed"){
            return undefined
        }
        if(url.protocol != "http" && url.protocol != "https"){
            return undefined
        }
        const info_url = url.joinPath("info").schemeless_raw
        const info_resp = await fetch(info_url)
        if(!info_resp.ok){
            throw `Failed requesting ${info_url}`
        }

        const raw_info = ensureJsonObject(await info_resp.json())
        return new PrecomputedChunks({
            url,
            type: ensureType(ensureJsonString(raw_info["type"])),
            data_type: ensureDataType(ensureJsonString(raw_info["data_type"])),
            num_channels: ensureJsonNumber(raw_info["num_channels"]),
            scales: ensureJsonArray(raw_info["scales"]).map(raw_scale => Scale.fromJsonValue(url, raw_scale))
        })
    }
}