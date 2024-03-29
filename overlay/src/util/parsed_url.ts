import { UrlDto } from "../client/dto";
import { IJsonable } from "./serialization";

export const data_schemes = ["precomputed", "n5", "deepzoom"] as const;
export type DataScheme = typeof data_schemes[number];
export function ensureDataScheme(value: string): DataScheme{
    const variant = data_schemes.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid data scheme: ${value}`)
    }
    return variant
}

export const protocols = ["http", "https", "ws", "wss", "memory", "file"] as const;
export type Protocol = typeof protocols[number];
export function ensureProtocol(value: string): Protocol{
    const variant = protocols.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid protocol: ${value}`)
    }
    return variant
}

export class Path{
    public readonly components: Array<string>;
    public static readonly root = new Path({components: []})

    public static parse(raw: string): Path{
        return new Path({components: raw.split("/")})
    }

    constructor({components}: {components: Array<string>}){
        var clean_components = new Array<string>()
        for(let component of  components){
            if(component == "." || component == ""){
                continue;
            }if(component == ".."){
                if(clean_components.length > 0){
                    clean_components.pop()
                }
            }else{
                clean_components.push(component)
            }
        }
        this.components = clean_components
    }

    public get raw(): string{
        return "/" + this.components.join("/")
    }

    public get name(): string{
        return this.components[this.components.length - 1] || "/" //FIXME ?
    }

    public get stem(): string{
        let parts = this.name.split(".")
        if(parts.length > 1){
            parts.pop()
        }
        return parts.join(".")
    }

    public get suffix(): string{
        const parts = this.name.split(".")
        return parts.length > 1 ? parts[parts.length - 1] : ""
    }

    public get parent(): Path{
        let new_components = this.components.slice()
        new_components.pop()
        return new Path({components: new_components})
    }

    public isParentOf(other: Path): boolean{
        if(this.components.length >= other.components.length){
            return false
        }
        for(let i=0; i<this.components.length; i++){
            if(this.components[i] != other.components[i]){
                return false
            }
        }
        return true
    }

    public get extension(): string | undefined{
        if(!this.name.includes(".")){
            return undefined
        }
        return this.name.split(".").slice(-1)[0]
    }

    public joinPath(subpath: string | Path): Path{
        const subcomponents = subpath instanceof Path ? subpath.components : Path.parse(subpath).components
        return new Path({components: this.components.concat(subcomponents)})
    }

    public equals(other: Path): boolean{
        for(let i=0; i < Math.max(this.components.length, other.components.length); i++){
            if(this.components[i] != other.components[i]){
                return false
            }
        }
        return true
    }

    public toString(){
        return this.raw
    }

    public get hashValue(): string{
        return this.toString()
    }

    public toJsonValue(): string{
        return this.toString()
    }
    public static fromDto(dto: string): Path{
        return Path.parse(dto)
    }
    public toDto(): string{
        return this.raw
    }
}

export class Url implements IJsonable{
    public readonly datascheme?: DataScheme
    public readonly protocol: Protocol
    public readonly hostname: string
    public readonly host: string
    public readonly port?: number
    public readonly path: Path
    public readonly search: Map<string, string>
    public readonly hash?: string
    public readonly schemeless_raw: string
    public readonly raw: string
    public readonly double_protocol_raw: string

    constructor(params: {
        datascheme?: DataScheme,
        protocol: Protocol,
        hostname: string,
        port?: number,
        path: Path,
        search?: Map<string, string>,
        hash?: string,
    }){
        this.datascheme = params.datascheme
        this.protocol = params.protocol
        this.hostname = params.hostname
        this.host = params.hostname + (params.port === undefined ? "" : `:${params.port}`)
        this.port = params.port
        this.path = params.path
        this.search = params.search || new Map<string, string>()
        this.hash = params.hash
        this.schemeless_raw = `${this.protocol}://${this.host}${encodeURI(this.path.raw)}`

        if(this.search.size > 0){
            const encoded_search = "?" + Array.from(this.search)
                .map(([key, value]) => encodeURIComponent(key) + "=" + encodeURIComponent(value))
                .join("&")
            this.schemeless_raw += encoded_search
        }
        if(this.hash){
            this.schemeless_raw += "#" + this.hash
        }

        if(this.datascheme){
            this.raw = `${this.datascheme}+${this.schemeless_raw}`
            this.double_protocol_raw = `${this.datascheme}://${this.schemeless_raw}`
        }else{
            this.raw = this.schemeless_raw
            this.double_protocol_raw = this.raw
        }
    }

    public toBase64(): string{
        return btoa(this.raw.toString()).replace("+", "-").replace("/", "_")
    }

    public static fromBase64(encoded: String): Url{
        const decoded = atob(encoded.replace("-", "+").replace("_", "/"))
        return Url.parse(decoded)
    }

    public toJsonValue(): string{
        return this.raw
    }

    public get hashValue(): string{
        return this.toString()
    }

    public static fromDto(message: UrlDto): Url{
        const search = new Map<string, string>();
        for(const key in message.search){
            search.set(key, message.search[key])
        }
        return new Url({
            datascheme: message.datascheme,
            protocol: message.protocol,
            hostname: message.hostname,
            port: message.port,
            path: Path.parse(message.path),
            hash: message.fragment,
            search: search,
        })
    }

    public toDto(): UrlDto{
        if(this.protocol == "ws" || this.protocol == "wss"){
            throw `FIXME!!!`
        }
        let searchObj: {[key: string]: string} = {}
        for(let [key, value] of this.search){
            searchObj[key] = value
        }
        return new UrlDto({
            datascheme: this.datascheme,
            protocol: this.protocol,
            hostname: this.hostname,
            port: this.port,
            path: this.path.raw,
            search: searchObj,
            fragment: this.hash,
        })
    }

    public static readonly url_pattern = new RegExp(
        "(" +
            `(?<datascheme>${data_schemes.join("|").replace("+", "\\+")})` + String.raw`(\+|://)` +
        ")?" +

        `(?<protocol>${protocols.join("|").replace("+", "\\+")})` + "://" +

        String.raw`(?<hostname>[0-9a-z\-\.]+)` +

        "(:" +
            String.raw`(?<port>\d+)` +
        ")?" +

        String.raw`(?<path>/[^?#]*)` +

        String.raw`(\?` +
            "(?<search>[^#]*)" +
        ")?" +

        "(#" +
            "(?<hash>.*)" +
        ")?",

        "i"
    )

    public static parse(url: string): Url{
        const match = url.match(Url.url_pattern)
        if(match === null){
            throw Error(`Invalid URL: ${url}`);
        }
        const groups = match.groups!
        const raw_datascheme = groups["datascheme"]
        const raw_port = groups["port"]
        const raw_search = groups["search"]
        let parsed_search = new URLSearchParams(raw_search || "")
        var search =  new Map<string, string>(parsed_search.entries())

        return new Url({
            datascheme: raw_datascheme === undefined ? undefined : ensureDataScheme(raw_datascheme),
            protocol: ensureProtocol(groups["protocol"]),
            hostname: groups["hostname"],
            port: raw_port === undefined ? undefined : parseInt(raw_port),
            path: Path.parse(groups["path"]),
            search: search,
            hash: groups["hash"]
        })
    }

    public static safe_parse(url: string): Url | Error{
        try{
            return Url.parse(url)
        }catch(e){
            return Error(`${e.message}`)
        }
    }

    public updatedWith(params: {
        datascheme?: DataScheme,
        protocol?: Protocol,
        hostname?: string,
        port?: number,
        path?: Path,
        search?: Map<string, string>,
        extra_search?: Map<string, string>
        hash?: string,
    }): Url{
        var new_search = new Map<string, string>()
        Array.from(params.search || this.search).forEach(([key, value]) => new_search.set(key, value))
        Array.from(params.extra_search || new Map<string, string>()).forEach(([key, value]) => new_search.set(key, value))

        return new Url({
            datascheme: "datascheme" in params ? params.datascheme : this.datascheme,
            protocol: params.protocol === undefined ? this.protocol : params.protocol,
            hostname: params.hostname === undefined ? this.hostname : params.hostname,
            port: "port" in params ? params.port : this.port,
            path: params.path === undefined ? this.path : params.path,
            search: new_search,
            hash: "hash" in params ? params.hash : this.hash,
        })
    }

    public get parent(): Url{
        return this.updatedWith({path: this.path.parent})
    }

    public isParentOf(other: Url): boolean{
        if(!this.equals(other.updatedWith({datascheme: this.datascheme, path: this.path}))){
            return false
        }
        return this.path.isParentOf(other.path)
    }

    public joinPath(subpath: string | Path): Url{
        let pathStr = typeof subpath === "string" ? subpath : subpath.raw
        return this.updatedWith({path: this.path.joinPath(pathStr)})
    }

    public ensureDataScheme(datascheme: DataScheme): Url{
        if(this.datascheme && this.datascheme != datascheme){
            throw Error(`Url ${this.raw} had unexpected datascheme: ${this.datascheme}. Expected ${datascheme}`)
        }
        return this.updatedWith({
            datascheme: datascheme
        })
    }

    public get name(): string{
        return this.path.name
    }

    public equals(other: Url): boolean{
        return this.double_protocol_raw == other.double_protocol_raw
    }

    public get root(): Url{
        return this.updatedWith({path: Path.parse("/")})
    }

    public toString(): string{
        return this.raw
    }
}
