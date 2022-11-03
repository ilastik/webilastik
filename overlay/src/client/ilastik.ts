import { vec3 } from "gl-matrix"
import { INativeView } from "../drivers/viewer_driver"
import { fetchJson, sleep } from "../util/misc"
import { Path, Url } from "../util/parsed_url"
import { DataType, Scale } from "../util/precomputed_chunks"
import {
    ensureJsonArray, ensureJsonBoolean, ensureJsonNumber, ensureJsonObject,
    ensureJsonString, ensureOptional, IJsonable, JsonableValue, JsonObject, JsonValue, toJsonValue
} from "../util/serialization"
import {
    ColorMessage,
    DataSourceMessage,
    FailedViewMessage,
    IlpFeatureExtractorMessage,
    Interval5DMessage,
    Point5DMessage,
    PredictionsViewMessage,
    RawDataViewMessage,
    Shape5DMessage,
    StrippedPrecomputedViewMessage,
    UnsupportedDatasetViewMessage
} from "./message_schema"

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

export const hpcSiteNames = ["CSCS", "JUSUF", "LOCAL"] as const;
export type HpcSiteName = typeof hpcSiteNames[number]

export function ensureHpcSiteName(value: string): HpcSiteName{
    const variant = hpcSiteNames.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid hpc site name: ${value}`)
    }
    return variant
}

export class SlurmJob{
    public readonly job_id: number
    public readonly state: SlurmJobState
    public readonly start_time_utc_sec?: number
    public readonly time_elapsed_sec: number
    public readonly time_limit_minutes: number
    public readonly num_nodes: number
    public readonly session_id: string

    constructor(params: {
        job_id: number,
        state: SlurmJobState
        start_time_utc_sec?: number,
        time_elapsed_sec: number,
        time_limit_minutes: number,
        num_nodes: number,
        session_id: string,
    }){
        this.job_id = params.job_id
        this.state = params.state
        this.start_time_utc_sec = params.start_time_utc_sec
        this.time_elapsed_sec = params.time_elapsed_sec
        this.time_limit_minutes = params.time_limit_minutes
        this.num_nodes = params.num_nodes
        this.session_id = params.session_id
    }

    public is_failure(): boolean{
        return slurmJobFailedStates.find(st => st == this.state) !== undefined
    }

    public is_done(): boolean{
        return slurmJobDoneStates.find(st => st == this.state) !== undefined
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
            session_id: ensureJsonString(value_obj['session_id']),
        })
    }
}

export class SessionStatus{
    public readonly slurm_job: SlurmJob
    public readonly session_url: Url
    public readonly connected: boolean
    public readonly hpc_site: HpcSiteName

    constructor(params:{
        slurm_job: SlurmJob,
        session_url: Url,
        connected: boolean,
        hpc_site: HpcSiteName
    }){
        this.slurm_job = params.slurm_job
        this.session_url = params.session_url
        this.connected = params.connected
        this.hpc_site = params.hpc_site
    }

    public static fromJsonValue(value: JsonValue): SessionStatus{
        const value_obj = ensureJsonObject(value)
        return new this({
            slurm_job: SlurmJob.fromJsonValue(value_obj['slurm_job']),
            session_url: Url.parse(ensureJsonString(value_obj['session_url'])),
            connected: ensureJsonBoolean(value_obj['connected']),
            hpc_site: ensureHpcSiteName(ensureJsonString(value_obj['hpc_site'])),
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

    public doRPC(params: {applet_name: string, method_name: string, method_arguments: JsonableValue}){
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

    public static async check_login({ilastikUrl}: {ilastikUrl: Url}): Promise<Error | boolean>{
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
        return new Error(`Checking loging faield with ${response.status}:\n${contents}`)
    }

    public static async getStatus(params: {ilastikUrl: Url, sessionId: string, hpc_site: HpcSiteName}): Promise<SessionStatus | Error>{
        let result = await fetchJson(
            params.ilastikUrl.joinPath(`/api/get_session_status`).raw,
            {
                cache: "no-store",
                method: "POST",
                body: JSON.stringify({
                    session_id: params.sessionId,
                    hpc_site: params.hpc_site,
                })
            }
        )
        if(result instanceof Error){
            return result
        }
        return SessionStatus.fromJsonValue(result)
    }

    public static async listSessions(params: {ilastikUrl: Url, hpc_site: HpcSiteName}): Promise<SessionStatus[] | Error>{
        let payload_result = await fetchJson(
            params.ilastikUrl.joinPath("/api/list_sessions").raw,
            {
                cache: "no-store",
                method: "POST",
                body: JSON.stringify({
                    hpc_site: params.hpc_site
                })
            },
        )
        if(payload_result instanceof Error){
            return payload_result
        }
        return ensureJsonArray(payload_result).map(item => SessionStatus.fromJsonValue(item))
    }

    public static async getAvailableHpcSites(params: {ilastikUrl: Url}): Promise<HpcSiteName[] | Error>{
        let payload_result = await fetchJson(
            params.ilastikUrl.joinPath("/api/get_available_hpc_sites").raw,
            {
                cache: "no-store",
                method: "POST",
            },
        )
        if(payload_result instanceof Error){
            return payload_result
        }
        return ensureJsonArray(payload_result).map(item => ensureHpcSiteName(ensureJsonString(item)))
    }

    public static getEbrainsToken(): string | undefined{
        return document.cookie.split('; ')
            .find(row => row.startsWith('ebrains_user_access_token='))?.split('=')[1];
    }

    public static async create(params: {
        ilastikUrl: Url,
        session_duration_minutes: number,
        timeout_minutes: number,
        hpc_site: HpcSiteName,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void,
        autoCloseOnTimeout: boolean,
    }): Promise<Session | Error>{
        const onProgress = params.onProgress || (() => {})
        const newSessionUrl = params.ilastikUrl.joinPath("/api/session")
        onProgress("Requesting session...")

        let session_creation_response = await fetch(newSessionUrl.schemeless_raw, {
            method: "POST",
            body: JSON.stringify({
                session_duration_minutes: params.session_duration_minutes,
                hpc_site: params.hpc_site
            })
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
            ilastikUrl: params.ilastikUrl,
            timeout_minutes: params.timeout_minutes,
            sessionId: sessionStatus.slurm_job.session_id,
            hpc_site: params.hpc_site,
            onProgress,
            onUsageError: params.onUsageError,
            autoCloseOnTimeout: params.autoCloseOnTimeout,
        })
    }

    public static async load(params: {
        ilastikUrl: Url,
        sessionId: string,
        timeout_minutes: number,
        hpc_site: HpcSiteName,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void,
        autoCloseOnTimeout: boolean,
    }): Promise<Session | Error>{
        const start_time_ms = Date.now()
        const timeout_ms = params.timeout_minutes * 60 * 1000
        const onProgress = params.onProgress || (() => {})
        while(Date.now() - start_time_ms < timeout_ms){
            let sessionStatus = await Session.getStatus({ilastikUrl: params.ilastikUrl, sessionId: params.sessionId, hpc_site: params.hpc_site})
            if(sessionStatus instanceof Error){
                return sessionStatus
            }
            if(sessionStatus.slurm_job.is_done()){
                return Error(`Session ${params.sessionId} is already closed`)
            }
            if(!sessionStatus.connected){
                onProgress(`Session is not ready yet`)
                await sleep(2000)
                continue
            }
            onProgress(`Session is ready!`)
            let session = new Session({
                ilastikUrl: params.ilastikUrl,
                sessionStatus,
                onUsageError: params.onUsageError,
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
        onProgress(`Timed out waiting for session ${params.sessionId}`)
        if(params.autoCloseOnTimeout){
            onProgress(`Cancelling session ${params.sessionId}`)
            const cancellation_result = await Session.cancel({ilastikUrl: params.ilastikUrl, sessionId: params.sessionId, hpc_site: params.hpc_site})
            if(cancellation_result instanceof Error){
                onProgress(`Could not cancel session ${params.sessionId}: ${cancellation_result.message}`)
            }else{
                onProgress(`Cancelled session ${params.sessionId}`)
            }
        }
        return Error(`Could not create a session: timeout`)
    }

    public static async cancel(params: {ilastikUrl: Url, sessionId: string, hpc_site: HpcSiteName}): Promise<Error | undefined>{
        let result = await fetchJson(
            params.ilastikUrl.joinPath(`api/delete_session`).raw,
            {
                method: "POST",
                body: JSON.stringify({
                    session_id: params.sessionId,
                    hpc_site: params.hpc_site,
                })
            }
        )
        if(result instanceof Error){
            return result
        }
        return undefined
    }
}

export type FeatureClassName = IlpFeatureExtractorMessage["class_name"]

export class IlpFeatureExtractor{
    public readonly ilp_scale: number
    public readonly axis_2d: "x" | "y" | "z" | undefined
    public readonly __class__: FeatureClassName

    constructor(params: {ilp_scale: number, axis_2d: "x" | "y" | "z" | undefined, __class__: FeatureClassName}){
        this.ilp_scale = params.ilp_scale
        this.axis_2d = params.axis_2d
        this.__class__ = params.__class__
    }

    public static fromMessage(message: IlpFeatureExtractorMessage): IlpFeatureExtractor{
        return new IlpFeatureExtractor({
            ilp_scale: message.ilp_scale,
            axis_2d: message.axis_2d || "z",
            __class__: message.class_name
        })
    }

    public toMessage(): IlpFeatureExtractorMessage{
        return new IlpFeatureExtractorMessage({
            ilp_scale: this.ilp_scale,
            axis_2d: this.axis_2d,
            class_name: this.__class__,
        })
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

    public static fromMessage(message: ColorMessage): Color{
        return new Color({
            r: message.r,
            g: message.g,
            b: message.b,
        })
    }

    public toMessage(): ColorMessage{
        return new ColorMessage({
            r: this.r,
            g: this.g,
            b: this.b,
        })
    }

    public equals(other: Color): boolean{
        return this.hashValue == other.hashValue
    }

    public inverse(): Color{
        return new Color({r: 255 - this.r, g: 255 - this.g, b: 255 - this.b})
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

    public static fromMessage(message: Point5DMessage): Point5D{
        return new this({
            x: message.x,
            y: message.y,
            z: message.z,
            t: message.t,
            c: message.c,
        })
    }

    public toMessage(): Point5DMessage {
        return new Point5DMessage({x: this.x, y: this.y, z: this.z, t: this.t, c: this.c})
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

    public static fromMessage(message: Shape5DMessage): Shape5D{
        return new this({
            x: message.x,
            y: message.y,
            z: message.z,
            t: message.t,
            c: message.c,
        })
    }

    public toMessage(): Shape5DMessage {
        return new Shape5DMessage({x: this.x, y: this.y, z: this.z, t: this.t, c: this.c})
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

    public static fromMessage(message: Interval5DMessage){
        return new this({
            x: [message.start.x, message.stop.x],
            y: [message.start.y, message.stop.y],
            z: [message.start.z, message.stop.z],
            t: [message.start.t, message.stop.t],
            c: [message.start.c, message.stop.c],
        })
    }

    public toMessage(): Interval5DMessage{
        return new Interval5DMessage({
            start: this.start.toMessage(), stop: this.stop.toMessage(),
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

export class DataSource{
    public readonly url: Url
    public readonly interval: Interval5D
    public readonly tile_shape: Shape5D
    public readonly spatial_resolution: [number, number, number]

    constructor(params: {
        url: Url,
        interval: Interval5D,
        tile_shape: Shape5D,
        spatial_resolution: [number, number, number]
    }){
        this.url = params.url
        this.interval = params.interval
        this.tile_shape = params.tile_shape
        this.spatial_resolution = params.spatial_resolution
    }

    public get shape(): Shape5D{
        return this.interval.shape
    }

    public get hashValue(): string{
        return this.url.raw
    }

    public static fromMessage(message: DataSourceMessage) : DataSource{
        return new DataSource({
            url: Url.fromMessage(message.url),
            interval: Interval5D.fromMessage(message.interval),
            tile_shape: Shape5D.fromMessage(message.tile_shape),
            spatial_resolution: message.spatial_resolution,
        })
    }

    public toMessage(): DataSourceMessage{
        return new DataSourceMessage({
            url: this.url.toMessage(),
            interval: this.interval.toMessage(),
            tile_shape: this.tile_shape.toMessage(),
            spatial_resolution: this.spatial_resolution,
        })
    }

    public get resolutionString(): string{
        return `${this.spatial_resolution[0]} x ${this.spatial_resolution[1]} x ${this.spatial_resolution[2]}nm`
    }

    public getDisplayString() : string{
        return `${this.url.raw} (${this.resolutionString})`
    }

    public equals(other: DataSource): boolean{
        return (
            this.url.equals(other.url) && vec3.equals(this.spatial_resolution, other.spatial_resolution)
        )
    }

    public static async getDatasourcesFromUrl(params: {datasource_url: Url, session: Session}): Promise<Array<DataSource> | Error>{
        let url = params.session.sessionUrl.joinPath("get_datasources_from_url")
            .updatedWith({
                search: new Map([["url", Session.btoa(params.datasource_url.raw)]])
            })
        let response = await fetch(url.raw, {
            method: "POST",
            body: JSON.stringify({url: params.datasource_url.raw}),
            cache: "no-store", //FIXME: why can't this be cached again? Nonces in URLs? Tokens in Filesystems?
        })
        if(!response.ok){
            let error_message = (await response.json())["error"]
            return Error(error_message)
        }
        let payload = ensureJsonObject(await response.json())
        if("error" in payload){
            return Error(ensureJsonString(payload.error))
        }
        //FIXME: maybe fix this array processing? This should probably be a Message itself
        const out = new Array<DataSource>()
        const rawArray = ensureJsonArray(payload);
        for(let item of rawArray){
            let datasourceResult = DataSourceMessage.fromJsonValue(item)
            if(datasourceResult instanceof Error){
                return datasourceResult
            }
            out.push(DataSource.fromMessage(datasourceResult))
        }
        return out
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

export type DataViewMessageUnion = RawDataViewMessage | StrippedPrecomputedViewMessage | UnsupportedDatasetViewMessage | FailedViewMessage
export type ViewMessageUnion = DataViewMessageUnion | PredictionsViewMessage
export type DataViewUnion = RawDataView | StrippedPrecomputedView | UnsupportedDatasetView | FailedView
export type ViewUnion = DataViewUnion | PredictionsView

export abstract class View{
    public readonly name: string;
    public readonly url: Url;

    constructor(params: {name: string, url: Url}){
        this.name = params.name
        this.url = params.url
    }

    public toNative(name?: string): INativeView{
        return {
            name: name || this.name,
            url: this.url.updatedWith({search: new Map(), hash: ""}).raw
        }
    }

    public static fromMessage(message: ViewMessageUnion): ViewUnion{
        if(message instanceof PredictionsViewMessage){
            return PredictionsView.fromMessage(message)
        }
        return DataView.fromMessage(message)
    }
}

export function parseAsView(value: JsonValue): ViewUnion | Error{
    const predictionsViewMessage = PredictionsViewMessage.fromJsonValue(value)
    if(!(predictionsViewMessage instanceof Error)){
        return PredictionsView.fromMessage(predictionsViewMessage)
    }
    return parseAsDataViewUnion(value)
}

export function parseAsDataViewUnion(value: JsonValue): DataViewUnion | Error{
    //FIXME: this should probably be autogenerated
    const rawDataViewMessage = RawDataViewMessage.fromJsonValue(value)
    if(!(rawDataViewMessage instanceof Error)){
        return RawDataView.fromMessage(rawDataViewMessage)
    }

    const strippedPrecompViewMessage = StrippedPrecomputedViewMessage.fromJsonValue(value)
    if(!(strippedPrecompViewMessage instanceof Error)){
        return StrippedPrecomputedView.fromMessage(strippedPrecompViewMessage)
    }

    const failedViewMessage = FailedViewMessage.fromJsonValue(value)
    if(!(failedViewMessage instanceof Error)){
        return FailedView.fromMessage(failedViewMessage)
    }

    const unsupportedDatasetViewMessage = UnsupportedDatasetViewMessage.fromJsonValue(value)
    if(!(unsupportedDatasetViewMessage instanceof Error)){
        return UnsupportedDatasetView.fromMessage(unsupportedDatasetViewMessage)
    }
    return Error(`Could not parse ${JSON.stringify(value)}`)
}

export abstract class DataView extends View{
    public static fromMessage(message: DataViewMessageUnion): DataViewUnion{
        if(message instanceof RawDataViewMessage){
            return RawDataView.fromMessage(message)
        }
        if(message instanceof StrippedPrecomputedViewMessage){
            return StrippedPrecomputedView.fromMessage(message)
        }
        if(message instanceof UnsupportedDatasetViewMessage){
            return UnsupportedDatasetView.fromMessage(message)
        }
        if(message instanceof FailedViewMessage){
            return FailedView.fromMessage(message)
        }
        throw `Should be unreachable`
    }

    public static async makeDataView(params: {name: string, url: Url, session: Session}): Promise<DataViewUnion | Error>{
        let result = await fetchJson(
            params.session.sessionUrl.joinPath("make_data_view").raw,
            {
                method: "POST",
                body: JSON.stringify({
                    name: params.name, url: params.url.toString()
                }),
            }
        )
        if(result instanceof Error){
            return result
        }
        return parseAsDataViewUnion(result)
    }

    public abstract getDatasources(): Array<DataSource> | undefined;
}

export class RawDataView extends DataView{
    public readonly datasources: DataSource[]
    constructor(params: {name: string, url: Url, datasources: Array<DataSource>}){
        super(params)
        this.datasources = params.datasources
    }

    public static fromMessage(message: RawDataViewMessage): RawDataView {
        return new RawDataView({
            datasources: message.datasources.map(ds_msg => DataSource.fromMessage(ds_msg)),
            name: message.name,
            url: Url.fromMessage(message.url)
        })
    }

    public getDatasources(): Array<DataSource> | undefined{
        return this.datasources.slice()
    }
}

export class StrippedPrecomputedView extends DataView{
    public readonly datasource: DataSource
    constructor(params: {name: string, url: Url, datasource: DataSource}){
        super(params)
        this.datasource = params.datasource
    }

    public static fromMessage(message: StrippedPrecomputedViewMessage): StrippedPrecomputedView {
        return new StrippedPrecomputedView({
            datasource: DataSource.fromMessage(message.datasource),
            name: message.name,
            url: Url.fromMessage(message.url)
        })
    }

    public getDatasources(): Array<DataSource>{
        return [this.datasource]
    }
}

export class PredictionsView extends View{
    public readonly raw_data: DataSource
    public readonly classifier_generation: number
    constructor(params: {name: string, url: Url, raw_data: DataSource, classifier_generation: number}){
        super(params)
        this.raw_data = params.raw_data
        this.classifier_generation = params.classifier_generation
    }

    public static fromMessage(message: PredictionsViewMessage): PredictionsView {
        return new PredictionsView({
            classifier_generation: message.classifier_generation,
            name: message.name,
            raw_data: DataSource.fromMessage(message.raw_data),
            url: Url.fromMessage(message.url)
        })
    }

}

export class UnsupportedDatasetView extends DataView{
    public static fromMessage(message: UnsupportedDatasetViewMessage): UnsupportedDatasetView {
        return new UnsupportedDatasetView({
            name: message.name,
            url: Url.fromMessage(message.url)
        })
    }

    public getDatasources(): undefined{
        return undefined
    }
}

export class FailedView extends DataView{
    public readonly error_message: string
    constructor(params: {name: string, url: Url, error_message: string}){
        super(params)
        this.error_message = params.error_message
    }

    public static fromMessage(message: FailedViewMessage): FailedView {
        return new FailedView({
            error_message: message.error_message,
            name: message.name,
            url: Url.fromMessage(message.url)
        })
    }

    public getDatasources(): undefined{
        return undefined
    }
}
