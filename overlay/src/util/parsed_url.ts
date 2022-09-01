import { ensureJsonString, IJsonable, JsonValue } from "./serialization";

export const data_schemes = ["precomputed"] as const;
export type DataScheme = typeof data_schemes[number];
export function ensureDataScheme(value: string): DataScheme{
    const variant = data_schemes.find(variant => variant === value)
    if(variant === undefined){
        throw Error(`Invalid data scheme: ${value}`)
    }
    return variant
}

export const protocols = ["http", "https", "ws", "wss"] as const;
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

    public get parent(): Path{
        let new_components = this.components.slice()
        new_components.pop()
        return new Path({components: new_components})
    }

    public get extension(): string | undefined{
        if(!this.name.includes(".")){
            return undefined
        }
        return this.name.split(".").slice(-1)[0]
    }

    public joinPath(subpath: string): Path{
        return new Path({components: this.components.concat(subpath.split("/"))})
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

    public toJsonValue(): string{
        return this.toString()
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
        this.schemeless_raw = `${this.protocol}://${this.host}${this.path.raw}`

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

    public toJsonValue(): string{
        return this.raw
    }

    public get hashValue(): string{
        return this.toString()
    }

    public static fromJsonValue(value: JsonValue): Url{
        return Url.parse(ensureJsonString(value))
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
