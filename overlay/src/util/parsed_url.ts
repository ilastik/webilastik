
export class ParsedUrl {
    public readonly datascheme: string;
    public readonly protocol: string;
    public readonly hostname: string;
    public readonly host: string;
    public readonly port?: number;
    public readonly path: string;
    public readonly search: string;
    public readonly hash: string;
    public readonly href: string;

    public static readonly datascheme_pattern = /[a-zA-Z0-9\-\.]+/;
    public static readonly protocol_pattern = /[a-zA-Z0-9\-\.]+:\/\//;
    public static readonly hostname_pattern = /[a-zA-Z\-\.]+/;
    public static readonly port_pattern = /:\d+/;
    public static readonly path_pattern = /\/[^?]*/;
    public static readonly search_pattern = /\?[^#]*/;
    public static readonly hash_pattern = /#.*/;

    public static readonly url_pattern = new RegExp(
        "^" +
        "(" +
        `(?<datascheme>${ParsedUrl.datascheme_pattern.source})` + /(\+|:\/\/)/.source +
        ")?" +
        `(?<protocol>${ParsedUrl.protocol_pattern.source})` +
        `(?<hostname>${ParsedUrl.hostname_pattern.source})` +
        `(?<port>${ParsedUrl.port_pattern.source})?` +
        `(?<path>${ParsedUrl.path_pattern.source})` +
        `(?<search>${ParsedUrl.search_pattern.source})?` +
        `(?<hash>${ParsedUrl.hash_pattern.source})?`
    );

    constructor({
        datascheme, protocol, hostname, port, path, search = "", hash = ""
    }: {
        datascheme?: string;
        protocol: string;
        hostname: string;
        port?: number;
        path: string;
        search: string;
        hash: string;
    }) {
        const pathParts = new Array<string>();
        for (const part of `/${path}`.split('/')) {
            if (part == ".") {
                continue;
            }
            if (part == "..") {
                pathParts.pop();
            } else {
                pathParts.push(part);
            }
        }
        this.datascheme = datascheme || "";
        this.protocol = protocol;
        this.hostname = hostname;
        this.host = hostname + (port === undefined ? "" : `:${port}`);
        this.port = port;
        this.path = pathParts.join("/").replace(/\/+/g, "/");
        this.search = search;
        this.hash = hash;
        this.href = `${protocol}${this.host}${path}${search}${hash}`;
    }

    public static parse(url: string): ParsedUrl {
        let match = url.match(ParsedUrl.url_pattern);
        if (match === null) {
            throw new Error(`Invalid URL: ${JSON.stringify(url)}`);
        }
        let groups = match.groups!;
        return new ParsedUrl({
            datascheme: groups["datascheme"] || undefined,
            protocol: groups["protocol"],
            hostname: groups["hostname"],
            port: groups["port"] ? parseInt(groups["port"].slice(1)) : undefined,
            path: groups["path"],
            search: groups["search"] || "",
            hash: groups["hash"] || ""
        });
    }

    public getParent(): ParsedUrl {
        return new ParsedUrl({
            ...this,
            path: this.path.endsWith("/") ? this.path + "../" : this.path + "/..",
        });
    }

    public concat(subpath: string): ParsedUrl {
        const fullPath = subpath.startsWith("/") ? subpath : `${this.path}/${subpath}`;
        return new ParsedUrl({
            ...this,
            path: fullPath
        });
    }

    public get name(): string {
        if (this.path == "/") {
            return "/";
        }
        const path_components = this.path.split("/");
        return path_components[path_components.length - 1] || path_components[path_components.length - 2];
    }

    public withProtocol(protocol: string) {
        if (protocol.match(ParsedUrl.protocol_pattern) === null) {
            throw `Bad protocol: ${protocol}. Should match this: ${ParsedUrl.protocol_pattern}`;
        }
        return new ParsedUrl({ ...this, protocol });
    }

    public withDataScheme(datascheme: string) {
        if (datascheme.match(ParsedUrl.datascheme_pattern) === null) {
            throw `Bad datascheme: ${datascheme}. Should match this: ${ParsedUrl.datascheme_pattern}`;
        }
        return new ParsedUrl({ ...this, datascheme });
    }

    public ensureDataScheme(datascheme: string): ParsedUrl {
        if (this.datascheme && this.datascheme != datascheme) {
            throw `Url ${this.href} had unexpected datascheme: ${this.datascheme}`;
        }
        return new ParsedUrl({ ...this, datascheme });
    }

    public getSchemedHref(scheme_protocol_separator: "://" | "+"): string {
        return `${this.datascheme && (this.datascheme + scheme_protocol_separator)}${this.href}`;
    }

    public withAddedSearchParams(params: Map<string, string>): ParsedUrl {
        let search_params = new URLSearchParams(this.search.slice(1));
        params.forEach((value, key) => search_params.append(key, value));
        return new ParsedUrl({
            ...this,
            search: `?${search_params.toString()}`,
        });
    }
}
