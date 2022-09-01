import { vec3 } from "gl-matrix"
import { fetchJson, sleep } from "../util/misc"
import { Path, Url } from "../util/parsed_url"
import { DataType, Scale } from "../util/precomputed_chunks"
import {
    ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonNumberPair, ensureJsonNumberTripplet, ensureJsonObject,
    ensureJsonString, ensureOptional, IJsonable, IJsonableObject, JsonObject, JsonValue, toJsonValue
} from "../util/serialization"

export const slurmJobStates = [
    "BOOT_FAIL", "CANCELLED", "COMPLETED", "DEADLINE", "FAILED", "NODE_FAIL", "OUT_OF_MEMORY",
    "PENDING", "PREEMPTED", "RUNNING", "REQUEUED", "RESIZING", "REVOKED", "SUSPENDED", "TIMEOUT"
] as const;

export const slurmJobRunnableStates = [
    "PENDING", "RUNNING", "REQUEUED", "RESIZING", "SUSPENDED"
] as const;

export const slurmJobFailedStates = [
    "BOOT_FAIL", "CANCELLED", "DEADLINE", "FAILED", "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED", "REVOKED", "TIMEOUT"
] as const;

export const slurmJobDoneStates = [
    "COMPLETED", ...slurmJobFailedStates
] as const;

export type SlurmJobState = typeof slurmJobStates[number]
export function ensureSlurmJobState(value: string): SlurmJobState{
    const variant = slurmJobStates.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid slurm job state: ${value}`)
    }
    return variant
}

export class SlurmJob{
    public readonly job_id: number
    public readonly state: string
    public readonly start_time_utc_sec?: number
    public readonly time_elapsed_sec: number
    public readonly time_limit_minutes: number
    public readonly num_nodes: number
    public readonly name: string
    public readonly session_id: string

    constructor(params: {
        job_id: number,
        state: SlurmJobState
        start_time_utc_sec?: number,
        time_elapsed_sec: number,
        time_limit_minutes: number,
        num_nodes: number,
        name: string,
        session_id: string,
    }){
        this.job_id = params.job_id
        this.state = params.state
        this.start_time_utc_sec = params.start_time_utc_sec
        this.time_elapsed_sec = params.time_elapsed_sec
        this.time_limit_minutes = params.time_limit_minutes
        this.num_nodes = params.num_nodes
        this.name = params.name
        this.session_id = params.session_id
    }

    public is_failure(): boolean{
        return this.state in slurmJobFailedStates
    }

    public is_done(): boolean{
        return this.state in slurmJobDoneStates
    }

    public static fromJsonValue(value: JsonValue): SlurmJob{
        const value_obj = ensureJsonObject(value)
        return new this({
            job_id: ensureJsonNumber(value_obj['job_id']),
            state: ensureSlurmJobState(ensureJsonString(value_obj['state'])),
            start_time_utc_sec: ensureOptional(ensureJsonNumber, value_obj['start_time_utc_sec']),
            time_elapsed_sec: ensureJsonNumber(value_obj['time_elapsed_sec']),
            time_limit_minutes: ensureJsonNumber(value_obj['time_limit_minutes']),
            num_nodes: ensureJsonNumber(value_obj['num_nodes']),
            name: ensureJsonString(value_obj['name']),
            session_id: ensureJsonString(value_obj['session_id']),
        })
    }
}

export class SessionStatus{
    public readonly slurm_job: SlurmJob
    public readonly session_url: Url
    public readonly connected: boolean

    constructor(params:{
        slurm_job: SlurmJob,
        session_url: Url,
        connected: boolean,
    }){
        this.slurm_job = params.slurm_job
        this.session_url = params.session_url
        this.connected = params.connected
    }

    public static fromJsonValue(value: JsonValue): SessionStatus{
        const value_obj = ensureJsonObject(value)
        return new this({
            slurm_job: SlurmJob.fromJsonValue(value_obj['slurm_job']),
            session_url: Url.parse(ensureJsonString(value_obj['session_url'])),
            connected: ensureJsonBoolean(value_obj['connected'])
        })
    }
}

export class Session{
    public readonly ilastikUrl: Url
    public readonly sessionStatus: SessionStatus
    private websocket: WebSocket
    private messageHandlers = new Array<(ev: MessageEvent) => void>();
    private readonly onUsageError: (message: string) => void

    protected constructor(params: {
        ilastikUrl: Url,
        sessionStatus: SessionStatus,
        onUsageError: (message: string) => void,
    }){
        this.ilastikUrl = params.ilastikUrl
        this.sessionStatus = params.sessionStatus
        this.onUsageError = params.onUsageError
        this.websocket = this.openWebsocket()
    }

    public get sessionUrl(): Url{
        return this.sessionStatus.session_url
    }

    public get startTime(): Date | undefined{
        const {start_time_utc_sec} = this.sessionStatus.slurm_job
        if(start_time_utc_sec === undefined){
            return undefined
        }
        return new Date(start_time_utc_sec * 1000)
    }

    public get timeLimitMinutes(): number{
        return this.sessionStatus.slurm_job.time_limit_minutes
    }

    public get sessionId(): string{
        return this.sessionStatus.slurm_job.session_id
    }

    private openWebsocket(): WebSocket{
        const wsUrl = this.sessionUrl.updatedWith({
            protocol: this.sessionUrl.protocol == "http" ? "ws" : "wss"
        }).joinPath("ws")
        let websocket = new WebSocket(wsUrl.schemeless_raw)
        websocket.addEventListener("error", this.refreshWebsocket)
        websocket.addEventListener("close", this.refreshWebsocket)
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

    public closeWebsocket(){
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

    public async terminate(): Promise<true | undefined>{
        this.closeWebsocket()
        let closeSession_response = await fetch(this.sessionUrl.joinPath("close").schemeless_raw, {method: "DELETE"})
        if(closeSession_response.ok){
            return undefined
        }
        return true
    }

    public async saveProject(params: {fs: FileSystem, project_file_path: Path}): Promise<Error | undefined>{
        let response = await fetch(
            this.sessionUrl.joinPath("save_project").schemeless_raw,
            {
                method: "POST",
                body: JSON.stringify(toJsonValue(params)),
            })
        if(response.ok){
            return undefined
        }
        return Error(`Could not save project: ${await response.text()}`)
    }

    public async loadProject(params: {fs: FileSystem, project_file_path: Path}): Promise<Error | undefined>{
        let response = await fetch(
            this.sessionUrl.joinPath("load_project").schemeless_raw,
            {
                method: "POST",
                body: JSON.stringify(toJsonValue(params)),
            })
        if(response.ok){
            return undefined
        }
        return Error(`Could not load project: ${await response.text()}`)
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
            credentials: "include",
            cache: "no-store",
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

    public static async getStatus(params: {ilastikUrl: Url, sessionId: string}): Promise<SessionStatus | Error>{
        let result = await fetchJson(
            params.ilastikUrl.joinPath(`/api/session/${params.sessionId}`).raw,
            {cache: "no-store"}
        )
        if(result instanceof Error){
            return result
        }
        return SessionStatus.fromJsonValue(result)
    }

    public static getEbrainsToken(): string | undefined{
        return document.cookie.split('; ')
            .find(row => row.startsWith('ebrains_user_access_token='))?.split('=')[1];
    }

    public static async create({ilastikUrl, session_duration_minutes, timeout_minutes, onProgress=(_) => {}, onUsageError}: {
        ilastikUrl: Url,
        session_duration_minutes: number,
        timeout_minutes: number,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void,
    }): Promise<Session | Error>{
        const newSessionUrl = ilastikUrl.joinPath("/api/session")
        onProgress("Requesting session...")

        let session_creation_response = await fetch(newSessionUrl.schemeless_raw, {
            method: "POST",
            body: JSON.stringify({session_duration_minutes})
        })
        if(Math.floor(session_creation_response.status / 100) == 5){
            onProgress(`Server-side error when creating a session`)
            return Error(`Server could not create session: ${await session_creation_response.text()}`)
        }
        if(!session_creation_response.ok){
            return Error(`Requesting session failed (${session_creation_response.status}): ${await session_creation_response.text()}`)
        }
        const sessionStatus = SessionStatus.fromJsonValue(await session_creation_response.json())
        onProgress(`Successfully requested a session! Waiting for it to be ready...`)
        return Session.load({
            ilastikUrl, timeout_minutes, sessionId: sessionStatus.slurm_job.session_id, onProgress, onUsageError
        })
    }

    public static async load({ilastikUrl, sessionId, timeout_minutes, onProgress=() => {}, onUsageError}: {
        ilastikUrl: Url,
        sessionId: string,
        timeout_minutes: number,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void,
    }): Promise<Session | Error>{
        const start_time_ms = Date.now()
        const timeout_ms = timeout_minutes * 60 * 1000
        while(Date.now() - start_time_ms < timeout_ms){
            let sessionStatus = await Session.getStatus({ilastikUrl, sessionId})
            if(sessionStatus instanceof Error){
                return sessionStatus
            }
            if(sessionStatus.slurm_job.is_done()){
                return Error(`Session ${sessionId} is already closed`)
            }
            if(!sessionStatus.connected){
                onProgress(`Session is not ready yet`)
                await sleep(2000)
                continue
            }
            onProgress(`Session is ready!`)
            let session = new Session({
                ilastikUrl,
                sessionStatus,
                onUsageError,
            })

            //FIXME
            return new Promise((resolve) => {
                let websocket = session.websocket
                let resolveThenClean = () => {
                    resolve(session)
                    websocket.removeEventListener("open", resolveThenClean)
                }
                websocket.addEventListener("open", resolveThenClean)
            })
        }
        return Error(`Could not create a session: timeout`)
    }
}

const FeatureClassNames = [
    "IlpGaussianSmoothing", "IlpGaussianGradientMagnitude", "IlpHessianOfGaussianEigenvalues", "IlpLaplacianOfGaussian", "IlpDifferenceOfGaussians", "IlpStructureTensorEigenvalues"
] as const;
export type FeatureClassName = (typeof FeatureClassNames)[number]

export function ensureFeatureClassName(value: string): FeatureClassName{
    const variant = FeatureClassNames.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid feature class name: ${value}`)
    }
    return variant
}

export class IlpFeatureExtractor implements IJsonable{
    public readonly ilp_scale: number
    public readonly axis_2d: string
    public readonly __class__: FeatureClassName

    constructor(params: {ilp_scale: number, axis_2d: string, __class__: FeatureClassName}){
        this.ilp_scale = params.ilp_scale
        this.axis_2d = params.axis_2d
        this.__class__ = params.__class__
    }

    public static fromJsonValue(value: JsonValue): IlpFeatureExtractor{
        let value_obj = ensureJsonObject(value)
        let feature_class_name = ensureFeatureClassName(ensureJsonString(value_obj["__class__"]))
        let ilp_scale = ensureJsonNumber(value_obj["ilp_scale"])
        let axis_2d = ensureJsonString(value_obj["axis_2d"])
        return new IlpFeatureExtractor({ilp_scale, axis_2d, __class__: feature_class_name})
    }

    public toJsonValue(): JsonValue{
        return {
            "ilp_scale": this.ilp_scale,
            "axis_2d": this.axis_2d,
            "__class__": this.__class__,
        }
    }

    public static fromJsonArray(data: JsonValue): IlpFeatureExtractor[]{
        const array = ensureJsonArray(data)
        return array.map((v: JsonValue) => IlpFeatureExtractor.fromJsonValue(v))
    }

    public equals(other: IlpFeatureExtractor) : boolean{
        return this.ilp_scale == other.ilp_scale && this.axis_2d == other.axis_2d && this.__class__ == other.__class__
    }
}

export class Color{
    public readonly r: number;
    public readonly g: number;
    public readonly b: number;
    public readonly vec3f: vec3;
    public readonly vec3i: vec3;
    public readonly hashValue: number
    public readonly hexCode: string

    public constructor({r=0, g=0, b=0}: {r: number, g: number, b: number}){
        this.r = r; this.g = g; this.b = b;
        this.vec3f = vec3.fromValues(r/255, g/255, b/255) // FIXME: rounding errors?
        this.vec3i = vec3.fromValues(r, g, b) // FIXME: rounding errors?
        this.hashValue = r * 256 * 256 + g * 256 + b
        this.hexCode = "#" + [r,g,b].map((val) => {
            const val_str = val.toString(16)
            return val_str.length < 2 ? "0" + val_str : val_str
        }).join("")
    }

    public static fromHexCode(hexCode: string): Color{
        let channels = hexCode.slice(1).match(/../g)!.map(c => parseInt(c, 16))
        return new Color({r: channels[0], g: channels[1], b: channels[2]})
    }

    public static fromJsonValue(value: JsonValue){
        let color_object = ensureJsonObject(value)
        return new Color({
            r: ensureJsonNumber(color_object["r"]),
            g: ensureJsonNumber(color_object["g"]),
            b: ensureJsonNumber(color_object["b"]),
        })
    }

    public toJsonValue(): JsonObject{
        return {
            r: this.r,
            g: this.g,
            b: this.b,
        }
    }

    public equals(other: Color): boolean{
        return this.hashValue == other.hashValue
    }

    public inverse(): Color{
        return new Color({r: 255 - this.r, g: 255 - this.g, b: 255 - this.b})
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
            Color.fromJsonValue(data["color"]),
            DataSource.fromJsonValue(data["raw_data"])
        )
    }
}

export class Point5D{
    public readonly x: number;
    public readonly y: number;
    public readonly z: number;
    public readonly t: number;
    public readonly c: number;

    constructor({x=0, y=0, z=0, t=0, c=0}: {
        x?: number, y?: number, z?: number,t?: number, c?: number
    }){
        this.x = x; this.y = y; this.z = z; this.t = t; this.c = c;
    }

    public static fromJsonData(data: JsonValue){
        let value_obj = ensureJsonObject(data)
        return new this({
            x: ensureOptional(ensureJsonNumber, value_obj.x) || 0,
            y: ensureOptional(ensureJsonNumber, value_obj.y) || 0,
            z: ensureOptional(ensureJsonNumber, value_obj.z) || 0,
            t: ensureOptional(ensureJsonNumber, value_obj.t) || 0,
            c: ensureOptional(ensureJsonNumber, value_obj.c) || 0,
        })
    }

    public toJsonValue(): JsonValue {
        return {x: this.x, y: this.y, z: this.z, t: this.t, c: this.c}
    }
}

export class Shape5D extends Point5D{
    constructor({x=1, y=1, z=1, t=1, c=1}: {
        x?: number, y?: number, z?: number, t?: number, c?: number
    }){
        super({x, y, z, t, c})
    }

    public updated(params: {x?: number, y?: number, z?: number, t?: number, c?: number}): Shape5D{
        return new Shape5D({
            x: params.x !== undefined ? params.x : this.x,
            y: params.y !== undefined ? params.y : this.y,
            z: params.z !== undefined ? params.z : this.z,
            t: params.t !== undefined ? params.t : this.t,
            c: params.c !== undefined ? params.c : this.c,
        })
    }

    public static fromJsonData(data: JsonValue){
        let value_obj = ensureJsonObject(data)
        return new this({
            x: ensureOptional(ensureJsonNumber, value_obj.x) || 1,
            y: ensureOptional(ensureJsonNumber, value_obj.y) || 1,
            z: ensureOptional(ensureJsonNumber, value_obj.z) || 1,
            t: ensureOptional(ensureJsonNumber, value_obj.t) || 1,
            c: ensureOptional(ensureJsonNumber, value_obj.c) || 1,
        })
    }

    public toInterval5D({offset=new Point5D({})}: {offset?: Point5D}): Interval5D{
        return new Interval5D({
            x: [offset.x, offset.x + this.x],
            y: [offset.y, offset.y + this.y],
            z: [offset.z, offset.z + this.z],
            t: [offset.t, offset.t + this.t],
            c: [offset.c, offset.c + this.c],
        })
    }
}

export class Interval5D{
    public readonly x: [number, number];
    public readonly y: [number, number];
    public readonly z: [number, number];
    public readonly t: [number, number];
    public readonly c: [number, number];
    public readonly shape: Shape5D
    public readonly start: Point5D
    public readonly stop: Point5D

    constructor({x, y, z, t, c}: {
        x: [number, number],
        y: [number, number],
        z: [number, number],
        t: [number, number],
        c: [number, number],
    }){
        this.x = x; this.y = y; this.z = z; this.t = t; this.c = c;
        this.shape = new Shape5D({
            x: x[1] - x[0],
            y: y[1] - y[0],
            z: z[1] - z[0],
            t: t[1] - t[0],
            c: c[1] - c[0],
        })
        this.start = new Point5D({x: x[0], y: y[0], z: z[0], t: t[0], c: c[0]})
        this.stop = new Point5D({x: x[1], y: y[1], z: z[1], t: t[1], c: c[1]})
    }

    public static fromJsonData(data: any){
        let value_obj = ensureJsonObject(data)
        return new this({
            x: ensureJsonNumberPair(value_obj.x),
            y: ensureJsonNumberPair(value_obj.y),
            z: ensureJsonNumberPair(value_obj.z),
            t: ensureJsonNumberPair(value_obj.t),
            c: ensureJsonNumberPair(value_obj.c),
        })
    }

    public toJsonValue(): JsonObject{
        return {"start": this.start.toJsonValue(), "stop": this.stop.toJsonValue()}
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

    constructor(params: {bucket_name: string, prefix: Path}){
        super()
        this.bucket_name = params.bucket_name
        this.prefix = params.prefix
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
        return new this({
            bucket_name: ensureJsonString(valueObj.bucket_name),
            prefix: Path.parse(ensureJsonString(valueObj.prefix)),
        })
    }

    public toJsonValue(): JsonObject {
        return {
            bucket_name: this.bucket_name,
            prefix: this.prefix.toString(),
            __class__: "BucketFs"
        }
    }

    public static fromDataProxyUrl(url: Url): BucketFs{
        if(!url.schemeless_raw.startsWith(BucketFs.API_URL.schemeless_raw)){
            throw `Expected data-proxy url, got this: ${url.toString()}`
        }

        return new BucketFs({
            bucket_name: url.path.components[2],
            prefix: new Path({components: url.path.components.slice(3)}),
        })
    }
}

export abstract class DataSource implements IJsonable{
    public readonly filesystem: FileSystem
    public readonly path: Path
    public readonly spatial_resolution: vec3
    public readonly shape: Shape5D
    public readonly tile_shape: Shape5D
    public readonly url: Url

    constructor(params: {
        filesystem: FileSystem, path: Path, shape: Shape5D, spatial_resolution?: vec3, tile_shape: Shape5D, url: Url
    }){
        this.filesystem = params.filesystem
        this.path = params.path
        this.spatial_resolution = params.spatial_resolution || vec3.fromValues(1,1,1)
        this.shape = params.shape
        this.tile_shape = params.tile_shape
        this.url = params.url
    }

    public get hashValue(): string{
        return JSON.stringify(this.toJsonValue())
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
            spatial_resolution: spatial_resolution === undefined ? vec3.fromValues(1,1,1) : ensureJsonNumberTripplet(spatial_resolution),
            shape: Shape5D.fromJsonData(json_object["shape"]),
            tile_shape: Shape5D.fromJsonData(json_object["tile_shape"]),
            url: Url.parse(ensureJsonString(json_object["url"])),
        }
    }

    public toJsonValue(): JsonObject{
        return {
            filesystem: this.filesystem.toJsonValue(),
            path: this.path.raw,
            spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
            shape: this.shape.toJsonValue(),
            tile_shape: this.tile_shape.toJsonValue(),
            url: this.url.raw,
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

    public static async getDatasourcesFromUrl(params: {datasource_url: Url, session: Session}): Promise<Array<DataSource> | Error>{
        let response = await fetch(params.session.sessionUrl.joinPath("get_datasources_from_url").raw, {
            method: "POST",
            body: JSON.stringify({url: params.datasource_url.raw})
        })
        if(!response.ok){
            let error_message = (await response.json())["error"]
            return Error(error_message)
        }
        let payload = ensureJsonObject(await response.json())
        if("error" in payload){
            return Error(ensureJsonString(payload.error))
        }
        return ensureJsonArray(payload["datasources"]).map(rds => DataSource.fromJsonValue(rds))
    }
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

    public toTrainingUrl(session: Session): Url{
        const original_url = this.filesystem.getUrl().joinPath(this.path.raw).updatedWith({datascheme: "precomputed"})
        const resolution_str = `${this.spatial_resolution[0]}_${this.spatial_resolution[1]}_${this.spatial_resolution[2]}`
        return session.sessionUrl
            .ensureDataScheme("precomputed")
            .joinPath(`stripped_precomputed/url=${Session.btoa(original_url.raw)}/resolution=${resolution_str}`)
    }
}

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

    public toTrainingUrl(_session: Session): Url{
        return this.filesystem.getUrl().joinPath(this.path.raw)
    }
}

export class FsDataSink{
    public readonly tile_shape: Shape5D
    public readonly interval: Interval5D
    public readonly dtype: DataType
    public readonly shape: any
    public readonly location: any
    public readonly filesystem: FileSystem
    public readonly path: Path

    constructor (params: {
        filesystem: FileSystem,
        path: Path,
        tile_shape: Shape5D,
        interval: Interval5D,
        dtype: DataType,
    }){
        this.filesystem = params.filesystem
        this.path = params.path
        this.tile_shape = params.tile_shape
        this.interval = params.interval
        this.dtype = params.dtype
        this.shape = this.interval.shape
        this.location = params.interval.start
    }

    public toJsonValue(): JsonObject{
        return {
            filesystem: this.filesystem.toJsonValue(),
            path: this.path.toString(),
            tile_shape: this.tile_shape.toJsonValue(),
            interval: this.interval.toJsonValue(),
            dtype: this.dtype.toString(),
        }
    }

    public static fromJsonValue(value: JsonValue): "DataSink"{
        let valueObj = ensureJsonObject(value)
        let className = valueObj.__class__
        if(className == "PrecomputedChunksScaleDataSink"){
            return PrecomputedChunksScaleDataSink.fromJsonValue(value)
        }
        throw Error(`Unrecognized DataSink class name: ${className}`)
    }
}

export class PrecomputedChunksScaleDataSink extends FsDataSink{
    public readonly info_dir: Path
    public readonly scale: Scale

    constructor(params: {
        filesystem: FileSystem,
        info_dir: Path,
        scale: Scale,
        dtype: DataType,
        num_channels: number,
    }){
        let shape = new Shape5D({x: params.scale.size[0], y: params.scale.size[1], z: params.scale.size[2], c: params.num_channels})
        let location = new Point5D({x: params.scale.voxel_offset[0], y: params.scale.voxel_offset[1], z: params.scale.voxel_offset[2]})
        let interval = shape.toInterval5D({offset: location})
        let chunk_sizes_5d = params.scale.chunk_sizes.map(cs => new Shape5D({x: cs[0], y: cs[1], z: cs[2], c: params.num_channels}))

        super({
            filesystem: params.filesystem,
            path: params.info_dir,
            tile_shape: chunk_sizes_5d[0], //FIXME?
            interval: interval,
            dtype: params.dtype,
        })
        this.info_dir = params.info_dir
        this.scale = params.scale
    }

    public toJsonValue(): JsonObject {
        return {
            ...super.toJsonValue(),
            __class__: "PrecomputedChunksScaleSink",
            info_dir: this.info_dir.raw,
            scale: this.scale.toJsonValue(),
            num_channels: this.shape.c,
        }
    }

    public updatedWith(params: {filesystem?: FileSystem, info_dir?: Path}): PrecomputedChunksScaleDataSink{
        return new PrecomputedChunksScaleDataSink({
            filesystem: params.filesystem || this.filesystem,
            info_dir: params.info_dir || this.info_dir,
            scale: this.scale,
            dtype: this.dtype,
            num_channels: this.shape.c,
        })
    }
}