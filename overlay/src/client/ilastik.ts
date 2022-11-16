import { vec3 } from "gl-matrix"
import { INativeView } from "../drivers/viewer_driver"
import { assertUnreachable, fetchJson, sleep } from "../util/misc"
import { Path, Url } from "../util/parsed_url"
import { DataType } from "../util/precomputed_chunks"
import {
    ensureJsonObject, ensureJsonString, JsonableValue, JsonValue, toJsonValue
} from "../util/serialization"
import {
    BucketFSDto,
    CheckLoginResultDto,
    CloseComputeSessionParamsDto,
    ColorDto,
    ComputeSessionStatusDto,
    CreateComputeSessionParamsDto,
    DataSourceDto,
    FailedViewDto,
    GetAvailableHpcSitesResponseDto,
    GetComputeSessionStatusParamsDto,
    GetDatasourcesFromUrlParamsDto,
    GetDatasourcesFromUrlResponseDto,
    HttpFsDto,
    IlpFeatureExtractorDto,
    Interval5DDto,
    ListComputeSessionsParamsDto,
    ListComputeSessionsResponseDto,
    LoadProjectParamsDto,
    MakeDataViewParams,
    OsfsDto,
    Point5DDto,
    PrecomputedChunksSinkDto,
    PredictionsViewDto,
    RawDataViewDto,
    SaveProjectParamsDto,
    Shape5DDto,
    StrippedPrecomputedViewDto,
    UnsupportedDatasetViewDto
} from "./dto"

export type HpcSiteName = ComputeSessionStatusDto["hpc_site"] //FIXME?

export const SESSION_DONE_STATES = [
    "BOOT_FAIL",
    "CANCELLED",
    "DEADLINE",
    "FAILED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "PREEMPTED",
    "REVOKED",
    "TIMEOUT",
    "COMPLETED",
]; //FIXME: shouldn't this be autogenerated?

export class Session{
    public readonly ilastikUrl: Url
    public readonly sessionStatus: ComputeSessionStatusDto
    private websocket: WebSocket
    private messageHandlers = new Array<(ev: MessageEvent) => void>();
    private readonly onUsageError: (message: string) => void

    protected constructor(params: {
        ilastikUrl: Url,
        sessionStatus: ComputeSessionStatusDto,
        onUsageError: (message: string) => void,
    }){
        this.ilastikUrl = params.ilastikUrl
        this.sessionStatus = params.sessionStatus
        this.onUsageError = params.onUsageError
        this.websocket = this.openWebsocket()
    }

    public get sessionUrl(): Url{
        return Url.fromDto(this.sessionStatus.session_url)
    }

    public get startTime(): Date | undefined{
        const {start_time_utc_sec} = this.sessionStatus.compute_session
        if(start_time_utc_sec === undefined){
            return undefined
        }
        return new Date(start_time_utc_sec * 1000)
    }

    public get timeLimitMinutes(): number{
        return this.sessionStatus.compute_session.time_limit_minutes
    }

    public get sessionId(): string{
        return this.sessionStatus.compute_session.compute_session_id
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

    public async saveProject(params: SaveProjectParamsDto): Promise<Error | undefined>{
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

    public async loadProject(params: LoadProjectParamsDto): Promise<Error | undefined>{
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

    public static async check_login({ilastikUrl}: {ilastikUrl: Url}): Promise<CheckLoginResultDto | Error>{
        let response = await fetchJson(ilastikUrl.joinPath("/api/check_login").raw, {
            credentials: "include",
            cache: "no-store",
        });
        if(response instanceof Error){
            return response
        }
        return CheckLoginResultDto.fromJsonValue(response)
    }

    public static async getStatus(params: {ilastikUrl: Url, rpcParams: GetComputeSessionStatusParamsDto}): Promise<ComputeSessionStatusDto | Error>{
        let result = await fetchJson(
            params.ilastikUrl.joinPath(`/api/get_session_status`).raw,
            {
                cache: "no-store",
                method: "POST",
                body: JSON.stringify(params.rpcParams.toJsonValue())
            }
        )
        if(result instanceof Error){
            return result
        }
        return ComputeSessionStatusDto.fromJsonValue(result)
    }

    public static async listSessions(params: {ilastikUrl: Url, rpcParams: ListComputeSessionsParamsDto}): Promise<ListComputeSessionsResponseDto | Error>{
        let payload_result = await fetchJson(
            params.ilastikUrl.joinPath("/api/list_sessions").raw,
            {
                cache: "no-store",
                method: "POST",
                body: JSON.stringify(params.rpcParams.toJsonValue())
            },
        )
        if(payload_result instanceof Error){
            return payload_result
        }
        return ListComputeSessionsResponseDto.fromJsonValue(payload_result)
    }

    public static async getAvailableHpcSites(params: {ilastikUrl: Url}): Promise<GetAvailableHpcSitesResponseDto | Error>{
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
        return GetAvailableHpcSitesResponseDto.fromJsonValue(payload_result)
    }

    public static getEbrainsToken(): string | undefined{
        return document.cookie.split('; ')
            .find(row => row.startsWith('ebrains_user_access_token='))?.split('=')[1];
    }

    public static async create(params: {
        ilastikUrl: Url,
        rpcParams: CreateComputeSessionParamsDto,
        timeout_minutes: number,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void,
        autoCloseOnTimeout: boolean,
    }): Promise<Session | Error>{
        const onProgress = params.onProgress || (() => {})
        const newSessionUrl = params.ilastikUrl.joinPath("/api/create_compute_session")
        onProgress("Requesting session...")

        let session_creation_response = await fetch(newSessionUrl.schemeless_raw, {
            method: "POST",
            body: JSON.stringify(params.rpcParams.toJsonValue())
        })
        if(Math.floor(session_creation_response.status / 100) == 5){
            onProgress(`Server-side error when creating a session`)
            return Error(`Server could not create session: ${await session_creation_response.text()}`)
        }
        if(!session_creation_response.ok){
            return Error(`Requesting session failed (${session_creation_response.status}): ${await session_creation_response.text()}`)
        }
        const sessionStatusMsg = ComputeSessionStatusDto.fromJsonValue(await session_creation_response.json())
        if(sessionStatusMsg instanceof Error){
            return sessionStatusMsg
        }
        onProgress(`Successfully requested a session! Waiting for it to be ready...`)
        return Session.load({
            ilastikUrl: params.ilastikUrl,
            getStatusRpcParams: new GetComputeSessionStatusParamsDto({
                compute_session_id: sessionStatusMsg.compute_session.compute_session_id,
                hpc_site: params.rpcParams.hpc_site,
            }),
            timeout_minutes: params.timeout_minutes,
            onProgress,
            onUsageError: params.onUsageError,
            autoCloseOnTimeout: params.autoCloseOnTimeout,
        })
    }

    public static async load(params: {
        ilastikUrl: Url,
        getStatusRpcParams: GetComputeSessionStatusParamsDto,
        timeout_minutes: number,
        onProgress?: (message: string) => void,
        onUsageError: (message: string) => void,
        autoCloseOnTimeout: boolean,
    }): Promise<Session | Error>{
        const start_time_ms = Date.now()
        const timeout_ms = params.timeout_minutes * 60 * 1000
        const onProgress = params.onProgress || (() => {})
        while(Date.now() - start_time_ms < timeout_ms){
            let sessionStatus = await Session.getStatus({ilastikUrl: params.ilastikUrl, rpcParams: params.getStatusRpcParams})
            if(sessionStatus instanceof Error){
                return sessionStatus
            }
            if(SESSION_DONE_STATES.includes(sessionStatus.compute_session.state)){ //FIXME
                return Error(`Session ${params.getStatusRpcParams.compute_session_id} is already closed`)
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
        onProgress(`Timed out waiting for session ${params.getStatusRpcParams.compute_session_id}`)
        if(params.autoCloseOnTimeout){
            onProgress(`Cancelling session ${params.getStatusRpcParams.compute_session_id}`)
            const cancellation_result = await Session.cancel({
                ilastikUrl: params.ilastikUrl,
                rpcParams: new CloseComputeSessionParamsDto({
                    compute_session_id: params.getStatusRpcParams.compute_session_id,
                    hpc_site: params.getStatusRpcParams.hpc_site,
                })
            })
            if(cancellation_result instanceof Error){
                onProgress(`Could not cancel session ${params.getStatusRpcParams.compute_session_id}: ${cancellation_result.message}`)
            }else{
                onProgress(`Cancelled session ${params.getStatusRpcParams.compute_session_id}`)
            }
        }
        return Error(`Could not create a session: timeout`)
    }

    public static async cancel(params: {ilastikUrl: Url, rpcParams: CloseComputeSessionParamsDto}): Promise<Error | undefined>{
        let result = await fetchJson(
            params.ilastikUrl.joinPath(`api/close_session`).raw,
            {
                method: "POST",
                body: JSON.stringify(params.rpcParams.toJsonValue())
            }
        )
        if(result instanceof Error){
            return result
        }
        return undefined
    }

    public async getDatasourcesFromUrl(params: GetDatasourcesFromUrlParamsDto): Promise<Array<DataSource> | Error>{
        let result = await fetchJson(this.sessionUrl.joinPath("get_datasources_from_url").raw, {
            method: "POST",
            body: JSON.stringify(toJsonValue(params)),
            cache: "no-store", //FIXME: why can't this be cached again? Nonces in URLs? Tokens in Filesystems?
        })
        if(result instanceof Error){
            return result
        }
        const responseDto =  GetDatasourcesFromUrlResponseDto.fromJsonValue(result);
        if(responseDto instanceof Error){
            return responseDto
        }
        return responseDto.datasources.map(msg => DataSource.fromDto(msg))
    }

    public async makeDataView(params: MakeDataViewParams): Promise<DataViewUnion | Error>{
        let result = await fetchJson(
            this.sessionUrl.joinPath("make_data_view").raw,
            {
                method: "POST",
                body: JSON.stringify(params.toJsonValue()),
            }
        )
        if(result instanceof Error){
            return result
        }
        return parseAsDataViewUnion(result)
    }

}

export type FeatureClassName = IlpFeatureExtractorDto["class_name"]

export class IlpFeatureExtractor{
    public readonly ilp_scale: number
    public readonly axis_2d: "x" | "y" | "z" | undefined
    public readonly __class__: FeatureClassName

    constructor(params: {ilp_scale: number, axis_2d: "x" | "y" | "z" | undefined, __class__: FeatureClassName}){
        this.ilp_scale = params.ilp_scale
        this.axis_2d = params.axis_2d
        this.__class__ = params.__class__
    }

    public static fromDto(message: IlpFeatureExtractorDto): IlpFeatureExtractor{
        return new IlpFeatureExtractor({
            ilp_scale: message.ilp_scale,
            axis_2d: message.axis_2d || "z",
            __class__: message.class_name
        })
    }

    public toDto(): IlpFeatureExtractorDto{
        return new IlpFeatureExtractorDto({
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

    public static fromDto(message: ColorDto): Color{
        return new Color({
            r: message.r,
            g: message.g,
            b: message.b,
        })
    }

    public toDto(): ColorDto{
        return new ColorDto({
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

    public static fromVec3(value: vec3){
        return new Point5D({x: value[0], y: value[1], z: value[2]})
    }

    public static fromDto(message: Point5DDto): Point5D{
        return new this({
            x: message.x,
            y: message.y,
            z: message.z,
            t: message.t,
            c: message.c,
        })
    }

    public toDto(): Point5DDto {
        return new Point5DDto({x: this.x, y: this.y, z: this.z, t: this.t, c: this.c})
    }

    public plus(other: Point5D): Point5D{
        return new Point5D({
            x: this.x + other.x,
            y: this.y + other.y,
            z: this.z + other.z,
            t: this.t + other.t,
            c: this.c + other.c,
        })
    }
}

export class Shape5D extends Point5D{
    constructor({x=1, y=1, z=1, t=1, c=1}: {
        x?: number, y?: number, z?: number, t?: number, c?: number
    }){
        super({x, y, z, t, c})
    }

    public static fromDto(message: Shape5DDto): Shape5D{
        return new this({
            x: message.x,
            y: message.y,
            z: message.z,
            t: message.t,
            c: message.c,
        })
    }

    public toDto(): Shape5DDto {
        return new Shape5DDto({x: this.x, y: this.y, z: this.z, t: this.t, c: this.c})
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

    public static fromStartStop(params: {start: Point5D, stop: Point5D}): Interval5D{
        return new Interval5D({
            x: [params.start.x, params.stop.x],
            y: [params.start.y, params.stop.y],
            z: [params.start.z, params.stop.z],
            t: [params.start.t, params.stop.t],
            c: [params.start.c, params.stop.c],
        })
    }

    public static fromDto(message: Interval5DDto){
        return new this({
            x: [message.start.x, message.stop.x],
            y: [message.start.y, message.stop.y],
            z: [message.start.z, message.stop.z],
            t: [message.start.t, message.stop.t],
            c: [message.start.c, message.stop.c],
        })
    }

    public toDto(): Interval5DDto{
        return new Interval5DDto({
            start: this.start.toDto(), stop: this.stop.toDto(),
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

    public static fromDto(message: DataSourceDto) : DataSource{
        return new DataSource({
            url: Url.fromDto(message.url),
            interval: Interval5D.fromDto(message.interval),
            tile_shape: Shape5D.fromDto(message.tile_shape),
            spatial_resolution: message.spatial_resolution,
        })
    }

    public toDto(): DataSourceDto{
        return new DataSourceDto({
            url: this.url.toDto(),
            interval: this.interval.toDto(),
            tile_shape: this.tile_shape.toDto(),
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
}

export abstract class Filesystem{
    public constructor(public readonly url: Url){}

    public static fromDto(message: BucketFSDto | HttpFsDto | OsfsDto): Filesystem{
        if(message instanceof BucketFSDto){
            return BucketFs.fromDto(message)
        }
        if(message instanceof HttpFsDto){
            return HttpFs.fromDto(message)
        }
        if(message instanceof OsfsDto){
            return OsFs.fromDto(message)
        }
        assertUnreachable(message)
    }
}

export class OsFs extends Filesystem{
    public constructor(public readonly path: Path){
        super(new Url({
            protocol: "file",
            hostname: "localhost", //FIXME?
            path: path,
        }))
    }

    public static fromDto(message: OsfsDto): OsFs {
        return new OsFs(Path.parse(message.path))
    }
}

export class HttpFs extends Filesystem{
    public constructor(params: {
        protocol: "http" | "https",
        hostname: string,
        port?: number,
        path: Path,
        search?: Map<string, string>
    }){
        super(new Url({
            protocol: params.protocol,
            hostname: params.hostname,
            port: params.port,
            path: params.path,
            search: params.search
        }))
    }
    public static fromDto(message: HttpFsDto): HttpFs {
        const search = new Map<string, string>();
        for(let key in message.search){
            search.set(key, message.search[key])
        }
        return new HttpFs({
            protocol: message.protocol,
            hostname: message.hostname,
            path: Path.parse(message.path),
            port: message.port,
            search,
        })
    }
}

export class BucketFs extends Filesystem{
    public readonly bucket_name: string
    public readonly prefix: Path

    public constructor(params: {
        bucket_name: string,
        prefix: Path,
    }){
        super(new Url({
            protocol: "https",
            hostname: "data-proxy.ebrains.eu",
            path: Path.parse(`/api/v1/buckets/${params.bucket_name}`).joinPath(params.prefix.raw),
        }))
        this.bucket_name = params.bucket_name
        this.prefix = params.prefix
    }
    public static fromDto(message: BucketFSDto): BucketFs{
        return new BucketFs({bucket_name: message.bucket_name, prefix: Path.parse(message.prefix)})
    }
}

export abstract class FsDataSink{
    public readonly filesystem: Filesystem
    public readonly path: Path
    public readonly tile_shape: Shape5D
    public readonly interval: Interval5D
    public readonly dtype: DataType

    public constructor(params: {
        filesystem: Filesystem,
        path: Path,
        dtype: DataType,
        tile_shape: Shape5D,
        interval: Interval5D,
    }){
        this.tile_shape = params.tile_shape
        this.interval = params.interval
        this.dtype = params.dtype
        this.filesystem = params.filesystem
        this.path = params.path
    }

    public static fromDto(message: PrecomputedChunksSinkDto): FsDataSink{
        return PrecomputedChunksSink.fromDto(message)
    }

    public abstract toDataSource(): DataSource;
}

export class PrecomputedChunksSink extends FsDataSink{
    public readonly scale_key: Path
    public readonly resolution: [number, number, number]
    public readonly encoding: string

    public constructor(params: ConstructorParameters<typeof FsDataSink>[0] & {
        scale_key: Path,
        resolution: [number, number, number],
        encoding: "raw" | "jpeg",
    }){
        super(params)
        this.scale_key = params.scale_key
        this.resolution = params.resolution
        this.encoding = params.encoding
    }

    public static fromDto(message: PrecomputedChunksSinkDto): PrecomputedChunksSink{
        return new PrecomputedChunksSink({
            filesystem: Filesystem.fromDto(message.filesystem),
            path: Path.parse(message.path),
            dtype: message.dtype,
            tile_shape: Shape5D.fromDto(message.tile_shape),
            interval: Interval5D.fromDto(message.interval),
            scale_key: Path.parse(message.scale_key),
            resolution: message.resolution,
            encoding: message.encoding,
        })
    }

    public toDataSource(): DataSource{
        //FIXME: stop using URLs; have datasources encode al the stuff they need in properties
        const datasourceUrl = this.filesystem.url.joinPath(this.path).updatedWith({
            datascheme: "precomputed",
            hash: `resolution=${this.resolution[0]}_${this.resolution[1]}_${this.resolution[2]}`
        })
        return new DataSource({
            url: datasourceUrl,
            interval: this.interval,
            spatial_resolution: this.resolution,
            tile_shape: this.tile_shape,
        })
    }
}


export type DataViewMessageUnion = RawDataViewDto | StrippedPrecomputedViewDto | UnsupportedDatasetViewDto | FailedViewDto
export type ViewMessageUnion = DataViewMessageUnion | PredictionsViewDto
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

    public static fromDto(message: ViewMessageUnion): ViewUnion{
        if(message instanceof PredictionsViewDto){
            return PredictionsView.fromDto(message)
        }
        return DataView.fromDto(message)
    }
}

export function parseAsView(value: JsonValue): ViewUnion | Error{
    const predictionsViewDto = PredictionsViewDto.fromJsonValue(value)
    if(!(predictionsViewDto instanceof Error)){
        return PredictionsView.fromDto(predictionsViewDto)
    }
    return parseAsDataViewUnion(value)
}

export function parseAsDataViewUnion(value: JsonValue): DataViewUnion | Error{
    //FIXME: this should probably be autogenerated
    const rawDataViewDto = RawDataViewDto.fromJsonValue(value)
    if(!(rawDataViewDto instanceof Error)){
        return RawDataView.fromDto(rawDataViewDto)
    }

    const strippedPrecompViewDto = StrippedPrecomputedViewDto.fromJsonValue(value)
    if(!(strippedPrecompViewDto instanceof Error)){
        return StrippedPrecomputedView.fromDto(strippedPrecompViewDto)
    }

    const failedViewDto = FailedViewDto.fromJsonValue(value)
    if(!(failedViewDto instanceof Error)){
        return FailedView.fromDto(failedViewDto)
    }

    const unsupportedDatasetViewDto = UnsupportedDatasetViewDto.fromJsonValue(value)
    if(!(unsupportedDatasetViewDto instanceof Error)){
        return UnsupportedDatasetView.fromDto(unsupportedDatasetViewDto)
    }
    return Error(`Could not parse ${JSON.stringify(value)}`)
}

export abstract class DataView extends View{
    public static fromDto(message: DataViewMessageUnion): DataViewUnion{
        if(message instanceof RawDataViewDto){
            return RawDataView.fromDto(message)
        }
        if(message instanceof StrippedPrecomputedViewDto){
            return StrippedPrecomputedView.fromDto(message)
        }
        if(message instanceof UnsupportedDatasetViewDto){
            return UnsupportedDatasetView.fromDto(message)
        }
        if(message instanceof FailedViewDto){
            return FailedView.fromDto(message)
        }
        throw `Should be unreachable`
    }

    public abstract getDatasources(): Array<DataSource> | undefined;
}

export class RawDataView extends DataView{
    public readonly datasources: DataSource[]
    constructor(params: {name: string, url: Url, datasources: Array<DataSource>}){
        super(params)
        this.datasources = params.datasources
    }

    public static fromDto(message: RawDataViewDto): RawDataView {
        return new RawDataView({
            datasources: message.datasources.map(ds_msg => DataSource.fromDto(ds_msg)),
            name: message.name,
            url: Url.fromDto(message.url)
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

    public static fromDto(message: StrippedPrecomputedViewDto): StrippedPrecomputedView {
        return new StrippedPrecomputedView({
            datasource: DataSource.fromDto(message.datasource),
            name: message.name,
            url: Url.fromDto(message.url)
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

    public static fromDto(message: PredictionsViewDto): PredictionsView {
        return new PredictionsView({
            classifier_generation: message.classifier_generation,
            name: message.name,
            raw_data: DataSource.fromDto(message.raw_data),
            url: Url.fromDto(message.url)
        })
    }

}

export class UnsupportedDatasetView extends DataView{
    public static fromDto(message: UnsupportedDatasetViewDto): UnsupportedDatasetView {
        return new UnsupportedDatasetView({
            name: message.name,
            url: Url.fromDto(message.url)
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

    public static fromDto(message: FailedViewDto): FailedView {
        return new FailedView({
            error_message: message.error_message,
            name: message.name,
            url: Url.fromDto(message.url)
        })
    }

    public getDatasources(): undefined{
        return undefined
    }
}
