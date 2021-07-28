import { vec3 } from "gl-matrix"
import { DataSource, Session } from "../client/ilastik"
import { uuidv4 } from "../util/misc";
import { Url } from "../util/parsed_url";
import { ensureJsonArray, ensureJsonNumber, ensureJsonNumberTripplet, ensureJsonObject, ensureJsonString, JsonValue } from "../util/serialization"
import { IDataScale, IMultiscaleDataSource } from "./datasource";


const encodings = ["raw", "jpeg", "compressed_segmentation"] as const;
export type Encoding = typeof encodings[number];
export function ensureEncoding(value: string): Encoding{
    const variant = encodings.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid encoding: ${value}`)
    }
    return variant
}

export class PrecomputedChunksScale implements IDataScale{
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

    public getUrl() : Url{
        const resolution_str = `${this.resolution[0]}_${this.resolution[1]}_${this.resolution[2]}`;
        return this.base_url.updatedWith({
            extra_search: new Map([["resolution", resolution_str]])
        })
    }

    public getChunkUrl(interval: {x: [number, number], y: [number, number], z: [number, number]}): Url{
        return this.getUrl().joinPath(
            `${interval.x[0]}-${interval.x[1]}_${interval.y[0]}-${interval.y[1]}_${interval.z[0]}-${interval.z[1]}`
        )
    }

    public toDisplayString(): string{
        return `${this.resolution[0]} x ${this.resolution[1]} x ${this.resolution[2]} nm`
    }

    public isSameResolutionAs(other: PrecomputedChunksScale): boolean{
        return vec3.equals(this.resolution, other.resolution)
    }

    public async toStrippedMultiscaleDataSource(session: Session): Promise<StrippedPrecomputedChunks>{
        const original = await PrecomputedChunks.fromUrl(this.base_url)
        return await StrippedPrecomputedChunks.strip(original, this.resolution, session)
    }

    public toIlastikDataSource() : DataSource{
        return new DataSource(this.getUrl().double_protocol_raw, this.resolution)
    }

    public static fromJsonValue(base_url: Url, value: JsonValue){
        const obj = ensureJsonObject(value)
        return new PrecomputedChunksScale(base_url, {
            key: ensureJsonString(obj.key),
            size: ensureJsonNumberTripplet(obj.size),
            resolution: ensureJsonNumberTripplet(obj.resolution),
            voxel_offset: ensureJsonNumberTripplet(obj.voxel_offset),
            chunk_sizes: ensureJsonArray(obj.chunk_sizes).map(element => ensureJsonNumberTripplet(element)),
            encoding: ensureEncoding(ensureJsonString(obj.encoding)),
        })
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

export class PrecomputedChunks implements IMultiscaleDataSource{
    public readonly url: Url;
    public readonly type: Type;
    public readonly data_type: DataType;
    public readonly num_channels: number;
    public readonly scales: PrecomputedChunksScale[];

    constructor(params: {
        url: Url,
        type: Type,
        data_type: DataType,
        num_channels: number,
        scales: Array<PrecomputedChunksScale>,
    }){
        this.url = params.url
        this.type = params.type
        this.data_type = params.data_type
        this.num_channels = params.num_channels
        this.scales = params.scales
    }

    public static async fromUrl(url: Url): Promise<PrecomputedChunks>{
        url = url.ensureDataScheme("precomputed")
        if(url.protocol != "http" && url.protocol != "https"){
            throw Error(`Unsupported precomputed chunks URL: ${url.double_protocol_raw}`)
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
            scales: ensureJsonArray(raw_info["scales"]).map(raw_scale => PrecomputedChunksScale.fromJsonValue(url, raw_scale))
        })
    }

    public findScale(target: vec3 | PrecomputedChunksScale): PrecomputedChunksScale | undefined{
        const resolution = target instanceof PrecomputedChunksScale ? target.resolution : target
        return this.scales.find(scale => vec3.equals(scale.resolution, resolution))
    }
}

export class StrippedPrecomputedChunks extends PrecomputedChunks{
    public readonly original: PrecomputedChunks;
    public readonly scale: PrecomputedChunksScale;
    private constructor(params: {
        url: Url,
        type: Type,
        data_type: DataType,
        num_channels: number,
        scales: Array<PrecomputedChunksScale>,
        original: PrecomputedChunks
    }){
        super(params)
        const parsed_args = StrippedPrecomputedChunks.parse(params.url)
        if(params.scales.length != 1){
            throw Error(`Expected single scale, got ${params.scales.length}`)
        }
        if(!vec3.equals(params.scales[0].resolution, parsed_args.resolution)){
            throw Error(`Bad resolution ${vec3.str(parsed_args.resolution)}`)
        }
        this.original = params.original
        this.scale = this.scales[0]
    }

    public static match(url: Url): RegExpMatchArray | null{
        let url_regex = /stripped_precomputed\/url=(?<url>[^/]+)\/resolution=(?<resolution>\d+_\d+_\d+)/
        return  url.path.match(url_regex)
    }

    public static parse(url: Url): {url: Url, original_url: Url, resolution: vec3}{
        const match = this.match(url)
        if(!match){
            throw Error(`Url ${url.double_protocol_raw} is not a stripped precomputed chunks URL`)
        }
        const raw_resolution = match.groups!["resolution"].split("_").map(axis => parseInt(axis))
        const resolution = vec3.fromValues(raw_resolution[0], raw_resolution[1], raw_resolution[2])
        return {
            url,
            original_url: Url.parse(Session.atob(match.groups!["url"])),
            resolution,
        }
    }

    public static async strip(original: PrecomputedChunks, resolution: vec3, session: Session): Promise<StrippedPrecomputedChunks>{
        const original_url = original.url.double_protocol_raw
        const resolution_str = `${resolution[0]}_${resolution[1]}_${resolution[2]}`
        const compound_url = Url.parse(session.session_url)
            .ensureDataScheme("precomputed")
            .joinPath(`stripped_precomputed/url=${Session.btoa(original_url)}/resolution=${resolution_str}`)
        const chunks = await PrecomputedChunks.fromUrl(compound_url)

        return new StrippedPrecomputedChunks({
            url: compound_url,
            type: chunks.type,
            data_type: chunks.data_type,
            num_channels: chunks.num_channels,
            scales: chunks.scales,
            original,
        })
    }

    public static async fromUrl(url: Url): Promise<StrippedPrecomputedChunks>{
        const parsed = this.parse(url.ensureDataScheme("precomputed"))
        const chunks = await PrecomputedChunks.fromUrl(url)
        return new StrippedPrecomputedChunks({
            url,
            type: chunks.type,
            data_type: chunks.data_type,
            num_channels: chunks.num_channels,
            scales: chunks.scales,
            original: await PrecomputedChunks.fromUrl(parsed.original_url),
        })
    }
}

export class PredictionsPrecomputedChunks extends PrecomputedChunks{
    public readonly raw_data_url: Url;
    private constructor(params: {
        url: Url,
        type: Type,
        data_type: DataType,
        num_channels: number,
        scales: Array<PrecomputedChunksScale>,
    }){
        super(params)
        const parsed_args = PredictionsPrecomputedChunks.parse(params.url)
        this.raw_data_url = parsed_args.raw_data_url
    }

    public static match(url: Url): RegExpMatchArray | null{
        let url_regex = /predictions\/raw_data=(?<raw_data>[^/?]+)/
        return url.double_protocol_raw.match(url_regex)
    }

    public static parse(url: Url): {url: Url, raw_data_url: Url}{
        const match = this.match(url)
        if(!match){
            throw Error(`Url ${url.double_protocol_raw} is not a predictions precomputed chunks URL`)
        }
        const raw_data_url = Url.parse(Session.atob(match.groups!["raw_data"]))
        return {
            url,
            raw_data_url,
        }
    }

    public static async fromUrl(url: Url): Promise<PredictionsPrecomputedChunks>{
        const chunks = await PrecomputedChunks.fromUrl(url.ensureDataScheme("precomputed"))
        return new PredictionsPrecomputedChunks({
            ...chunks
        })
    }

    public static async createFor({raw_data, ilastik_session}: {raw_data: Url, ilastik_session: Session}): Promise<PredictionsPrecomputedChunks>{
        let raw_data_url = raw_data.double_protocol_raw
        let predictions_url = Url.parse(ilastik_session.session_url)
            .updatedWith({datascheme: "precomputed"})
            .joinPath(`predictions/raw_data=${Session.btoa(raw_data_url)}/run_id=${uuidv4()}`);
        let precomp_chunks = await PrecomputedChunks.fromUrl(predictions_url)
        return new PredictionsPrecomputedChunks({
            url: predictions_url,
            type: precomp_chunks.type,
            data_type: precomp_chunks.data_type,
            num_channels: precomp_chunks.num_channels,
            scales: precomp_chunks.scales,
        })
    }
}
