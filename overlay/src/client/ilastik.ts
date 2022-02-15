import { vec3 } from "gl-matrix"
import { sleep } from "../util/misc"
import { Path, Url } from "../util/parsed_url"
import { PrecomputedChunks } from "../util/precomputed_chunks"
import { ensureJsonArray, ensureJsonNumberTripplet, ensureJsonObject, ensureJsonString, IJsonable, IJsonableObject, JsonObject, JsonValue, toJsonValue } from "../util/serialization"

export class Session{
    public readonly ilastikUrl: Url
    public readonly sessionUrl: Url
    private websocket: WebSocket
    private messageHandlers = new Array<(ev: MessageEvent) => void>();
    private readonly onUsageError: (message: string) => void

    protected constructor(params: {
        ilastikUrl: Url,
        sessionUrl: Url,
        onUsageError: (message: string) => void,
    }){
        this.ilastikUrl = params.ilastikUrl
        this.sessionUrl = params.sessionUrl
        this.onUsageError = params.onUsageError
        this.websocket = this.openWebsocket()
    }

    private openWebsocket(): WebSocket{
        const wsUrl = this.sessionUrl.updatedWith({
            protocol: this.sessionUrl.protocol == "http" ? "ws" : "wss"
        }).joinPath("ws")
        let websocket = new WebSocket(wsUrl.schemeless_raw)
        websocket.addEventListener("close", this.refreshWebsocket)
        websocket.addEventListener("error", this.refreshWebsocket)
        websocket.addEventListener("message", (ev: MessageEvent) => {
            let payload = JSON.parse(ev.data)
            let payload_obj = ensureJsonObject(payload)
            if("error" in payload_obj){
                this.onUsageError(ensureJsonString(payload_obj.error))
            }
        })
        for(let handler of this.messageHandlers){
            websocket.addEventListener("message", handler)
        }
        return websocket
    }

    private closeWebsocket(){
        this.websocket.removeEventListener("close", this.refreshWebsocket)
        this.websocket.removeEventListener("error", this.refreshWebsocket)
        for(let handler of this.messageHandlers){
            this.websocket.removeEventListener("message", handler)
        }
        this.websocket.close()
    }

    private refreshWebsocket = (ev: Event) => {
        console.warn("Refreshing socket because of this:", ev)
        this.closeWebsocket()
        this.websocket = this.openWebsocket()
    }

    public addMessageListener(handler: (ev: MessageEvent) => void){
        this.messageHandlers.push(handler)
        this.websocket.addEventListener("message", handler)
    }

    public async close(): Promise<true | undefined>{
        this.closeWebsocket()
        let closeSession_response = await fetch(this.sessionUrl.joinPath("close").schemeless_raw, {method: "DELETE"})
        if(closeSession_response.ok){
            return undefined
        }
        return true
    }

    public doRPC(params: {applet_name: string, method_name: string, method_arguments: IJsonableObject}){
        return this.websocket.send(JSON.stringify({
            applet_name: params.applet_name,
            method_name: params.method_name,
            arguments: toJsonValue(params.method_arguments),
        }))
    }

    public static btoa(url: String): string{
        return btoa(url.toString()).replace("+", "-").replace("/", "_")
    }

    public static atob(encoded: String): string{
        return atob(encoded.replace("-", "+").replace("_", "/"))
    }

    public static async check_login({ilastikUrl}: {ilastikUrl: Url}): Promise<boolean>{
        let response = await fetch(ilastikUrl.joinPath("/api/check_login").raw, {
            credentials: "include"
        });
        if(response.ok){
            return true
        }
        if(response.status == 401){
            return false
        }
        let contents = await response.text()
        throw new Error(`Checking loging faield with ${response.status}:\n${contents}`)
    }

    public static getEbrainsToken(): string | undefined{
        return document.cookie.split('; ')
            .find(row => row.startsWith('ebrains_user_access_token='))?.split('=')[1];
    }

    public static async create({ilastikUrl, session_duration_seconds, timeout_s, onProgress=(_) => {}, onUsageError}: {
        ilastikUrl: Url,
        session_duration_seconds: number,
        timeout_s: number,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void

    }): Promise<Session>{
        const newSessionUrl = ilastikUrl.joinPath("/api/session")
        while(timeout_s > 0){
            let session_creation_response = await fetch(newSessionUrl.schemeless_raw, {
                method: "POST",
                body: JSON.stringify({session_duration: session_duration_seconds})
            })
            if(!session_creation_response.ok){
                onProgress(
                    `Requesting session failed (${session_creation_response.status}): ${session_creation_response.body}`
                )
                timeout_s -= 2
                await sleep(2000)
                continue
            }
            onProgress(`Successfully requested a session!`)
            let rawSession_data: {url: string, id: string, token: string} = await session_creation_response.json()
            while(timeout_s){
                let session_status_response = await fetch(ilastikUrl.joinPath(`/api/session/${rawSession_data.id}`).schemeless_raw)
                if(session_status_response.ok  && (await session_status_response.json())["status"] == "ready"){
                    onProgress(`Session has become ready!`)
                    break
                }
                onProgress(`Session is not ready yet`)
                timeout_s -= 2
                await sleep(2000)
            }
            return new Session({ilastikUrl, sessionUrl: Url.parse(rawSession_data.url), onUsageError})
        }
        throw `Could not create a session`
    }

    public static async load({ilastikUrl, sessionUrl, onUsageError}: {
        ilastikUrl: Url, sessionUrl:Url, onUsageError: (message: string) => void
    }): Promise<Session>{
        let session_status_resp = await fetch(sessionUrl.joinPath("/api/status").schemeless_raw)
        if(!session_status_resp.ok){
            throw Error(`Bad response from session: ${session_status_resp.status}`)
        }
        return new Session({ilastikUrl, sessionUrl, onUsageError})
    }
}

export abstract class FeatureExtractor implements IJsonable{
    public static fromJsonValue(data: any): FeatureExtractor{
        let feature_class_name = data["__class__"]
        if(feature_class_name == "GaussianSmoothing"){
            return new GaussianSmoothing(data)
        }
        if(feature_class_name == "GaussianGradientMagnitude"){
            return new GaussianGradientMagnitude(data)
        }
        if(feature_class_name == "HessianOfGaussianEigenvalues"){
            return new HessianOfGaussianEigenvalues(data)
        }
        if(feature_class_name == "LaplacianOfGaussian"){
            return new LaplacianOfGaussian(data)
        }
        if(feature_class_name == "DifferenceOfGaussians"){
            return new DifferenceOfGaussians(data)
        }
        if(feature_class_name == "StructureTensorEigenvalues"){
            return new StructureTensorEigenvalues(data)
        }
        throw Error(`Bad feature extractor class name in ${JSON.stringify(data)}`)
    }

    public static fromJsonArray(data: JsonValue): FeatureExtractor[]{
        const array = ensureJsonArray(data)
        return array.map((v: JsonValue) => FeatureExtractor.fromJsonValue(v))
    }

    public equals(other: FeatureExtractor) : boolean{
        if(this.constructor !== other.constructor){
            return false
        }
        //FIXME: maybe impelment a faster comparison here?
        return JSON.stringify(this.toJsonValue()) == JSON.stringify(other.toJsonValue())
    }

    public toJsonValue(): JsonValue{
        let out = JSON.parse(JSON.stringify(this))
        //FIXME: Class name
        out["__class__"] = this.constructor.name
        return out
    }
}

export class GaussianSmoothing extends FeatureExtractor{
    public readonly sigma: number;
    public readonly axis_2d: string;
    public constructor({sigma, axis_2d="z"}:{
        sigma: number,
        axis_2d?: string
    }){
        super()
        this.sigma=sigma
        this.axis_2d=axis_2d
    }
}

export class GaussianGradientMagnitude extends FeatureExtractor{
    public readonly sigma: number;
    public readonly axis_2d: string;
    public constructor({sigma, axis_2d="z"}: {
        sigma: number,
        axis_2d?: string
    }){
        super()
        this.sigma=sigma
        this.axis_2d=axis_2d
    }
}

export class HessianOfGaussianEigenvalues extends FeatureExtractor{
    public readonly scale: number;
    public readonly axis_2d: string;
    public constructor({scale, axis_2d='z'}: {
        scale: number,
        axis_2d?: string
    }){
        super()
        this.scale=scale
        this.axis_2d=axis_2d
    }
}

export class LaplacianOfGaussian extends FeatureExtractor{
    public readonly scale: number;
    public readonly axis_2d: string;
    public constructor({scale, axis_2d='z'}: {
        scale: number,
        axis_2d?: string
    }){
        super()
        this.scale=scale
        this.axis_2d=axis_2d
    }
}

export class DifferenceOfGaussians extends FeatureExtractor{
    public readonly sigma0: number;
    public readonly sigma1: number;
    public readonly axis_2d: string;
    public constructor({sigma0, sigma1, axis_2d="z"}: {
        sigma0: number,
        sigma1: number,
        axis_2d?: string
    }){
        super()
        this.sigma0=sigma0
        this.sigma1=sigma1
        this.axis_2d=axis_2d
    }
}

export class StructureTensorEigenvalues extends FeatureExtractor{
    public readonly innerScale: number;
    public readonly outerScale: number;
    public readonly axis_2d: string;
    public constructor({innerScale, outerScale, axis_2d="z"}: {
        innerScale: number,
        outerScale: number,
        axis_2d?: string
    }){
        super()
        this.innerScale=innerScale
        this.outerScale=outerScale
        this.axis_2d=axis_2d
    }
}

export class Color{
    public readonly r: number;
    public readonly g: number;
    public readonly b: number;
    public readonly a: number;
    public constructor({r=0, g=0, b=0, a=255}: {r: number, g: number, b: number, a: number}){
        this.r = r; this.g = g; this.b = b; this.a = a;
    }
    public static fromJsonData(data: any): Color{
        return new Color(data)
    }
}

export class Annotation{
    public constructor(
        public readonly voxels: Array<{x:number, y:number, z:number}>,
        public readonly color: Color,
        public readonly raw_data: DataSource
    ){
    }
    public static fromJsonData(data: any): Annotation{
        return new Annotation(
            data["voxels"],
            Color.fromJsonData(data["color"]),
            DataSource.fromJsonValue(data["raw_data"])
        )
    }
}

export class Shape5D{
    public readonly x: number;
    public readonly y: number;
    public readonly z: number;
    public readonly t: number;
    public readonly c: number;
    constructor({x, y, z, t, c}: {x: number, y: number, z: number, t: number, c: number}){
        this.x = x; this.y = y; this.z = z; this.t = t; this.c = c;
    }
    public static fromJsonData(data: any){
        return new this(data)
    }
}

export abstract class FileSystem implements IJsonable{
    public abstract getDisplayString(): string;
    public abstract toJsonValue(): JsonObject
    public static fromJsonValue(value: JsonValue): FileSystem{
        const value_obj = ensureJsonObject(value)
        const class_name = ensureJsonString(value_obj["__class__"])
        if(class_name == "HttpFs"){
            return HttpFs.fromJsonValue(value)
        }
        if(class_name == "BucketFs"){
            return BucketFs.fromJsonValue(value)
        }
        throw Error(`Could not deserialize FileSystem from ${JSON.stringify(value)}`)
    }
    public abstract equals(other: FileSystem): boolean;
    public abstract getUrl(): Url;

    public static fromUrl(url: Url): FileSystem{
        if(url.hostname == "data-proxy.ebrains.eu"){
            return BucketFs.fromDataProxyUrl(url)
        }else{
            return new HttpFs({read_url: url})
        }
    }
}

export class HttpFs extends FileSystem{
    public readonly read_url: Url
    public constructor({read_url}: {read_url: Url}){
        super()
        this.read_url = read_url.updatedWith({datascheme: undefined})
    }

    public getDisplayString(): string{
        return this.read_url.raw
    }

    public toJsonValue(): JsonObject{
        return {
            __class__: "HttpFs",
            read_url: this.read_url.schemeless_raw,
        }
    }

    public static fromJsonValue(data: JsonValue) : HttpFs{
        const data_obj = ensureJsonObject(data)
        return new HttpFs({
            read_url: Url.parse(ensureJsonString(data_obj["read_url"]))
        })
    }

    public equals(other: FileSystem): boolean{
        return other instanceof HttpFs && this.read_url.equals(other.read_url)
    }

    public getUrl(): Url{
        return this.read_url
    }
}

export class BucketFs extends FileSystem{
    public static readonly API_URL = Url.parse("https://data-proxy.ebrains.eu/api/buckets")
    public readonly bucket_name: string
    public readonly prefix: Path
    public readonly ebrains_user_token: string // FIXME?

    constructor(params: {bucket_name: string, prefix: Path, ebrains_user_token: string}){
        super()
        this.bucket_name = params.bucket_name
        this.prefix = params.prefix
        this.ebrains_user_token = params.ebrains_user_token
    }

    public equals(other: FileSystem): boolean {
        return (
            other instanceof BucketFs &&
            other.bucket_name == this.bucket_name &&
            other.prefix.equals(this.prefix)
        )
    }

    public getUrl(): Url {
        return BucketFs.API_URL.joinPath(`${this.bucket_name}/${this.prefix}`)
    }

    public getDisplayString(): string {
        return this.getUrl().toString()
    }

    public static fromJsonValue(value: JsonValue): BucketFs {
        const valueObj = ensureJsonObject(value)
        const ebrains_token_obj = ensureJsonObject(valueObj.ebrains_user_token)
        return new this({
            bucket_name: ensureJsonString(valueObj.bucket_name),
            prefix: Path.parse(ensureJsonString(valueObj.prefix)),
            ebrains_user_token: ensureJsonString(ebrains_token_obj.access_token),
        })
    }

    public toJsonValue(): JsonObject {
        return {
            bucket_name: this.bucket_name,
            prefix: this.prefix.toString(),
            ebrains_user_token: {
                access_token: this.ebrains_user_token
            },
            __class__: "BucketFs"
        }
    }

    public static fromDataProxyUrl(url: Url): BucketFs{
        if(!url.schemeless_raw.startsWith(BucketFs.API_URL.schemeless_raw)){
            throw `Expected data-proxy url, got this: ${url.toString()}`
        }
        const ebrains_user_token = Session.getEbrainsToken()
        if(ebrains_user_token === undefined){
            throw `Can't create BucketFS yet: Not logged in`
        }

        return new BucketFs({
            bucket_name: url.path.components[2],
            prefix: new Path({components: url.path.components.slice(3)}),
            ebrains_user_token,
        })
    }
}

export abstract class DataSource implements IJsonable{
    public readonly filesystem: FileSystem
    public readonly path: Path
    public readonly spatial_resolution: vec3

    constructor({filesystem, path, spatial_resolution=vec3.fromValues(1,1,1)}: {filesystem: FileSystem, path: Path, spatial_resolution?: vec3}){
        this.filesystem = filesystem
        this.path = path
        this.spatial_resolution = spatial_resolution
    }

    public static fromJsonValue(data: JsonValue) : DataSource{
        const data_obj = ensureJsonObject(data)
        const class_name = ensureJsonString(data_obj["__class__"])
        switch(class_name){
            case "PrecomputedChunksDataSource":
                return PrecomputedChunksDataSource.fromJsonValue(data)
            case "SkimageDataSource":
                return SkimageDataSource.fromJsonValue(data)
            default:
                throw Error(`Could not create datasource of type ${class_name}`)
        }
    }

    public static extractBasicData(json_object: JsonObject): ConstructorParameters<typeof DataSource>[0]{
        const spatial_resolution = json_object["spatial_resolution"]
        return {
            filesystem: FileSystem.fromJsonValue(json_object["filesystem"]),
            path: Path.parse(ensureJsonString(json_object["path"])),
            spatial_resolution: spatial_resolution === undefined ? vec3.fromValues(1,1,1) : ensureJsonNumberTripplet(spatial_resolution)
        }
    }

    public toJsonValue(): JsonObject{
        return {
            filesystem: this.filesystem.toJsonValue(),
            path: this.path.raw,
            spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
            ...this.doToJsonValue()
        }
    }

    public getDisplayString() : string{
        const resolution_str = `${this.spatial_resolution[0]} x ${this.spatial_resolution[1]} x ${this.spatial_resolution[2]}`
        return `${this.filesystem.getUrl().joinPath(this.path.raw)} (${resolution_str})`
    }

    protected abstract doToJsonValue() : JsonObject & {__class__: string}

    public equals(other: DataSource): boolean{
        return (
            this.constructor.name == other.constructor.name &&
            this.filesystem.equals(other.filesystem) &&
            this.path.equals(other.path) &&
            vec3.equals(this.spatial_resolution, other.spatial_resolution)
        )
    }

    public abstract toTrainingUrl(_session: Session): Url;
}

// Represents a single scale from precomputed chunks
export class PrecomputedChunksDataSource extends DataSource{
    public static fromJsonValue(data: JsonValue) : PrecomputedChunksDataSource{
        const data_obj = ensureJsonObject(data)
        return new PrecomputedChunksDataSource({
            ...DataSource.extractBasicData(data_obj),
        })
    }

    protected doToJsonValue() : JsonObject & {__class__: string}{
        return { __class__: "PrecomputedChunksDataSource"}
    }

    public static async tryGetTrainingRawData(url: Url): Promise<PrecomputedChunksDataSource | undefined>{
        let training_regex = /stripped_precomputed\/url=(?<url>[^/]+)\/resolution=(?<resolution>\d+_\d+_\d+)/
        let match = url.path.raw.match(training_regex)
        if(!match){
            return undefined
        }
        const original_url = Url.parse(Session.atob(match.groups!["url"]));
        const raw_resolution = match.groups!["resolution"].split("_").map(axis => parseInt(axis));
        const resolution = vec3.fromValues(raw_resolution[0], raw_resolution[1], raw_resolution[2]);
        return new PrecomputedChunksDataSource({
            filesystem: FileSystem.fromUrl(original_url),
            path: Path.parse("/"),
            spatial_resolution: resolution
        })
    }

    public toTrainingUrl(session: Session): Url{
        const original_url = this.filesystem.getUrl().joinPath(this.path.raw)
        const resolution_str = `${this.spatial_resolution[0]}_${this.spatial_resolution[1]}_${this.spatial_resolution[2]}`
        return session.sessionUrl
            .ensureDataScheme("precomputed")
            .joinPath(`stripped_precomputed/url=${Session.btoa(original_url.raw)}/resolution=${resolution_str}`)
    }

    public static async tryArrayFromUrl(url: Url): Promise<Array<PrecomputedChunksDataSource> | undefined>{
        let chunks = await PrecomputedChunks.tryFromUrl(url);
        if(chunks === undefined){
            return undefined
        }
        return chunks.scales.map(scale => {
            return new PrecomputedChunksDataSource({
                filesystem: new HttpFs({read_url: url.root}),
                path: url.path,
                spatial_resolution: vec3.clone(scale.resolution)
            })
        })
    }
}

const image_content_types = ["image/png", "image/gif", "image/jpeg"]

export class SkimageDataSource extends DataSource{
    public static fromJsonValue(data: JsonValue) : SkimageDataSource{
        const data_obj = ensureJsonObject(data)
        return new SkimageDataSource({
            ...DataSource.extractBasicData(data_obj),
        })
    }

    protected doToJsonValue() : JsonObject & {__class__: string}{
        return { __class__: "SkimageDataSource"}
    }

    public static async tryFromUrl(url: Url): Promise<SkimageDataSource | undefined>{
        if(url.datascheme !== undefined){
            return undefined
        }
        if(url.protocol !== "http" && url.protocol !== "https"){
            return undefined
        }
        const head = await fetch(url.toString(), {method: "HEAD"});
        if(!head.ok || !image_content_types.includes(head.headers.get("Content-Type")!)){
            return undefined
        }
        return new SkimageDataSource({
            filesystem: new HttpFs({read_url: url.root}),
            path: url.path,
        })
    }

    public static async tryGetTrainingRawData(url: Url): Promise<SkimageDataSource | undefined>{
        return await this.tryFromUrl(url)
    }

    public static async tryArrayFromUrl(url: Url): Promise<Array<SkimageDataSource> | undefined>{
        let datasource = await this.tryFromUrl(url)
        return datasource === undefined ? undefined : [datasource]
    }

    public toTrainingUrl(_session: Session): Url{
        return this.filesystem.getUrl().joinPath(this.path.raw)
    }
}

export class Lane implements IJsonable{
    public constructor(public readonly raw_data: DataSource){
    }
    public static fromJsonValue(data: any): Lane{
        return new Lane(DataSource.fromJsonValue(data["raw_data"]))
    }
    public toJsonValue(): JsonObject{
        return {raw_data: this.raw_data.toJsonValue()}
    }
    public static fromJsonArray(data: JsonValue): Lane[]{
        const array = ensureJsonArray(data)
        return array.map((v: JsonValue) => Lane.fromJsonValue(v))
    }
}