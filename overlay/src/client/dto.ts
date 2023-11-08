import {
  isJsonableArray,
  isJsonableObject,
  JsonArray,
  JsonObject,
  JsonValue,
  toJsonValue,
} from "../util/serialization";

export class MessageParsingError extends Error {
  public readonly __class_name__ = "MessageParsingError";
}

export function ensureJsonUndefined(value: JsonValue): undefined | MessageParsingError {
  if (value !== undefined && value !== null) { //FIXME? null AND undefined?
    return new MessageParsingError(`Expected undefined/null, found ${JSON.stringify(value)}`);
  }
  return undefined;
}

export function ensureJsonBoolean(value: JsonValue): boolean | MessageParsingError {
  if (typeof value !== "boolean") {
    return new MessageParsingError(`Expected boolean, found ${JSON.stringify(value)}`);
  }
  return value;
}

export function ensureJsonNumber(value: JsonValue): number | MessageParsingError {
  if (typeof value !== "number") {
    return new MessageParsingError(`Expected number, found ${JSON.stringify(value)}`);
  }
  return value;
}

export function ensureJsonString(value: JsonValue): string | MessageParsingError {
  if (typeof value !== "string") {
    return new MessageParsingError(`Expected string, found ${JSON.stringify(value)}`);
  }
  return value;
}

export function ensureJsonObject(value: JsonValue): JsonObject | MessageParsingError {
  if (!isJsonableObject(value)) {
    return new MessageParsingError(`Expected JSON object, found this: ${JSON.stringify(value)}`);
  }
  return value;
}

export function ensureJsonArray(value: JsonValue): JsonArray | MessageParsingError {
  if (!isJsonableArray(value)) {
    return new MessageParsingError(`Expected JSON array, found this: ${JSON.stringify(value)}`);
  }
  return value;
}

export function parse_as_int(value: JsonValue): number | MessageParsingError {
  return ensureJsonNumber(value);
}
export function parse_as_ColorDto(value: JsonValue): ColorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ColorDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ColorDto`);
  }
  const temp_r = parse_as_int(valueObject.r);
  if (temp_r instanceof MessageParsingError) return temp_r;
  const temp_g = parse_as_int(valueObject.g);
  if (temp_g instanceof MessageParsingError) return temp_g;
  const temp_b = parse_as_int(valueObject.b);
  if (temp_b instanceof MessageParsingError) return temp_b;
  return new ColorDto({
    r: temp_r,
    g: temp_g,
    b: temp_b,
  });
}
// Automatically generated via DataTransferObject for ColorDto
// Do not edit!
export class ColorDto {
  public r: number;
  public g: number;
  public b: number;
  constructor(_params: {
    r: number;
    g: number;
    b: number;
  }) {
    this.r = _params.r;
    this.g = _params.g;
    this.b = _params.b;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ColorDto",
      r: this.r,
      g: this.g,
      b: this.b,
    };
  }
  public static fromJsonValue(value: JsonValue): ColorDto | MessageParsingError {
    return parse_as_ColorDto(value);
  }
}

export function parse_as_str(value: JsonValue): string | MessageParsingError {
  return ensureJsonString(value);
}
export function parse_as_LabelHeaderDto(value: JsonValue): LabelHeaderDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LabelHeaderDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a LabelHeaderDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_color = parse_as_ColorDto(valueObject.color);
  if (temp_color instanceof MessageParsingError) return temp_color;
  return new LabelHeaderDto({
    name: temp_name,
    color: temp_color,
  });
}
// Automatically generated via DataTransferObject for LabelHeaderDto
// Do not edit!
export class LabelHeaderDto {
  public name: string;
  public color: ColorDto;
  constructor(_params: {
    name: string;
    color: ColorDto;
  }) {
    this.name = _params.name;
    this.color = _params.color;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "LabelHeaderDto",
      name: this.name,
      color: this.color.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): LabelHeaderDto | MessageParsingError {
    return parse_as_LabelHeaderDto(value);
  }
}

export function parse_as_Literal_of__quote_precomputed_quote_0_quote_n5_quote_0_quote_deepzoom_quote__endof_(
  value: JsonValue,
): "precomputed" | "n5" | "deepzoom" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "precomputed") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "n5") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "deepzoom") {
    return tmp_2;
  }
  return new MessageParsingError(`Could not parse ${value} as 'precomputed' | 'n5' | 'deepzoom'`);
}
export function parse_as_None(value: JsonValue): undefined | MessageParsingError {
  return ensureJsonUndefined(value);
}
export function parse_as_Union_of_Literal_of__quote_precomputed_quote_0_quote_n5_quote_0_quote_deepzoom_quote__endof_0None_endof_(
  value: JsonValue,
): "precomputed" | "n5" | "deepzoom" | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_Literal_of__quote_precomputed_quote_0_quote_n5_quote_0_quote_deepzoom_quote__endof_(
    value,
  );
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(
    `Could not parse ${JSON.stringify(value)} into 'precomputed' | 'n5' | 'deepzoom' | undefined`,
  );
}
export function parse_as_Literal_of__quote_http_quote_0_quote_https_quote_0_quote_file_quote_0_quote_memory_quote__endof_(
  value: JsonValue,
): "http" | "https" | "file" | "memory" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "http") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "https") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "file") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof MessageParsingError) && tmp_3 === "memory") {
    return tmp_3;
  }
  return new MessageParsingError(`Could not parse ${value} as 'http' | 'https' | 'file' | 'memory'`);
}
export function parse_as_Union_of_int0None_endof_(value: JsonValue): number | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_int(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into number | undefined`);
}
export function parse_as_Mapping_of_str0str_endof_(value: JsonValue): { [key: string]: string } | MessageParsingError {
  const valueObj = ensureJsonObject(value);
  if (valueObj instanceof MessageParsingError) {
    return valueObj;
  }
  const out: { [key: string]: string } = {};
  for (let key in valueObj) {
    const parsed_key = parse_as_str(key);
    if (parsed_key instanceof MessageParsingError) {
      return parsed_key;
    }
    const val = valueObj[key];
    const parsed_val = parse_as_str(val);
    if (parsed_val instanceof MessageParsingError) {
      return parsed_val;
    }
    out[parsed_key] = parsed_val;
  }
  return out;
}
export function parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(
  value: JsonValue,
): { [key: string]: string } | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_Mapping_of_str0str_endof_(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into { [key: string]: string } | undefined`);
}
export function parse_as_Union_of_str0None_endof_(value: JsonValue): string | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_str(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into string | undefined`);
}
export function parse_as_UrlDto(value: JsonValue): UrlDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "UrlDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a UrlDto`);
  }
  const temp_datascheme =
    parse_as_Union_of_Literal_of__quote_precomputed_quote_0_quote_n5_quote_0_quote_deepzoom_quote__endof_0None_endof_(
      valueObject.datascheme,
    );
  if (temp_datascheme instanceof MessageParsingError) return temp_datascheme;
  const temp_protocol =
    parse_as_Literal_of__quote_http_quote_0_quote_https_quote_0_quote_file_quote_0_quote_memory_quote__endof_(
      valueObject.protocol,
    );
  if (temp_protocol instanceof MessageParsingError) return temp_protocol;
  const temp_hostname = parse_as_str(valueObject.hostname);
  if (temp_hostname instanceof MessageParsingError) return temp_hostname;
  const temp_port = parse_as_Union_of_int0None_endof_(valueObject.port);
  if (temp_port instanceof MessageParsingError) return temp_port;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_search = parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(valueObject.search);
  if (temp_search instanceof MessageParsingError) return temp_search;
  const temp_fragment = parse_as_Union_of_str0None_endof_(valueObject.fragment);
  if (temp_fragment instanceof MessageParsingError) return temp_fragment;
  return new UrlDto({
    datascheme: temp_datascheme,
    protocol: temp_protocol,
    hostname: temp_hostname,
    port: temp_port,
    path: temp_path,
    search: temp_search,
    fragment: temp_fragment,
  });
}
// Automatically generated via DataTransferObject for UrlDto
// Do not edit!
export class UrlDto {
  public datascheme: "precomputed" | "n5" | "deepzoom" | undefined;
  public protocol: "http" | "https" | "file" | "memory";
  public hostname: string;
  public port: number | undefined;
  public path: string;
  public search: { [key: string]: string } | undefined;
  public fragment: string | undefined;
  constructor(_params: {
    datascheme: "precomputed" | "n5" | "deepzoom" | undefined;
    protocol: "http" | "https" | "file" | "memory";
    hostname: string;
    port: number | undefined;
    path: string;
    search: { [key: string]: string } | undefined;
    fragment: string | undefined;
  }) {
    this.datascheme = _params.datascheme;
    this.protocol = _params.protocol;
    this.hostname = _params.hostname;
    this.port = _params.port;
    this.path = _params.path;
    this.search = _params.search;
    this.fragment = _params.fragment;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "UrlDto",
      datascheme: toJsonValue(this.datascheme),
      protocol: this.protocol,
      hostname: this.hostname,
      port: toJsonValue(this.port),
      path: this.path,
      search: toJsonValue(this.search),
      fragment: toJsonValue(this.fragment),
    };
  }
  public static fromJsonValue(value: JsonValue): UrlDto | MessageParsingError {
    return parse_as_UrlDto(value);
  }
}

export function parse_as_Point5DDto(value: JsonValue): Point5DDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "Point5DDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a Point5DDto`);
  }
  const temp_x = parse_as_int(valueObject.x);
  if (temp_x instanceof MessageParsingError) return temp_x;
  const temp_y = parse_as_int(valueObject.y);
  if (temp_y instanceof MessageParsingError) return temp_y;
  const temp_z = parse_as_int(valueObject.z);
  if (temp_z instanceof MessageParsingError) return temp_z;
  const temp_t = parse_as_int(valueObject.t);
  if (temp_t instanceof MessageParsingError) return temp_t;
  const temp_c = parse_as_int(valueObject.c);
  if (temp_c instanceof MessageParsingError) return temp_c;
  return new Point5DDto({
    x: temp_x,
    y: temp_y,
    z: temp_z,
    t: temp_t,
    c: temp_c,
  });
}
// Automatically generated via DataTransferObject for Point5DDto
// Do not edit!
export class Point5DDto {
  public x: number;
  public y: number;
  public z: number;
  public t: number;
  public c: number;
  constructor(_params: {
    x: number;
    y: number;
    z: number;
    t: number;
    c: number;
  }) {
    this.x = _params.x;
    this.y = _params.y;
    this.z = _params.z;
    this.t = _params.t;
    this.c = _params.c;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "Point5DDto",
      x: this.x,
      y: this.y,
      z: this.z,
      t: this.t,
      c: this.c,
    };
  }
  public static fromJsonValue(value: JsonValue): Point5DDto | MessageParsingError {
    return parse_as_Point5DDto(value);
  }
}

export function parse_as_Shape5DDto(value: JsonValue): Shape5DDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "Shape5DDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a Shape5DDto`);
  }
  const temp_x = parse_as_int(valueObject.x);
  if (temp_x instanceof MessageParsingError) return temp_x;
  const temp_y = parse_as_int(valueObject.y);
  if (temp_y instanceof MessageParsingError) return temp_y;
  const temp_z = parse_as_int(valueObject.z);
  if (temp_z instanceof MessageParsingError) return temp_z;
  const temp_t = parse_as_int(valueObject.t);
  if (temp_t instanceof MessageParsingError) return temp_t;
  const temp_c = parse_as_int(valueObject.c);
  if (temp_c instanceof MessageParsingError) return temp_c;
  return new Shape5DDto({
    x: temp_x,
    y: temp_y,
    z: temp_z,
    t: temp_t,
    c: temp_c,
  });
}
// Automatically generated via DataTransferObject for Shape5DDto
// Do not edit!
export class Shape5DDto {
  public x: number;
  public y: number;
  public z: number;
  public t: number;
  public c: number;
  constructor(_params: {
    x: number;
    y: number;
    z: number;
    t: number;
    c: number;
  }) {
    this.x = _params.x;
    this.y = _params.y;
    this.z = _params.z;
    this.t = _params.t;
    this.c = _params.c;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "Shape5DDto",
      x: this.x,
      y: this.y,
      z: this.z,
      t: this.t,
      c: this.c,
    };
  }
  public static fromJsonValue(value: JsonValue): Shape5DDto | MessageParsingError {
    return parse_as_Shape5DDto(value);
  }
}

export function parse_as_Interval5DDto(value: JsonValue): Interval5DDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "Interval5DDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a Interval5DDto`);
  }
  const temp_start = parse_as_Point5DDto(valueObject.start);
  if (temp_start instanceof MessageParsingError) return temp_start;
  const temp_stop = parse_as_Point5DDto(valueObject.stop);
  if (temp_stop instanceof MessageParsingError) return temp_stop;
  return new Interval5DDto({
    start: temp_start,
    stop: temp_stop,
  });
}
// Automatically generated via DataTransferObject for Interval5DDto
// Do not edit!
export class Interval5DDto {
  public start: Point5DDto;
  public stop: Point5DDto;
  constructor(_params: {
    start: Point5DDto;
    stop: Point5DDto;
  }) {
    this.start = _params.start;
    this.stop = _params.stop;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "Interval5DDto",
      start: this.start.toJsonValue(),
      stop: this.stop.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): Interval5DDto | MessageParsingError {
    return parse_as_Interval5DDto(value);
  }
}

export function parse_as_OsfsDto(value: JsonValue): OsfsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "OsfsDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a OsfsDto`);
  }
  return new OsfsDto({});
}
// Automatically generated via DataTransferObject for OsfsDto
// Do not edit!
export class OsfsDto {
  constructor(_params: {}) {
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "OsfsDto",
    };
  }
  public static fromJsonValue(value: JsonValue): OsfsDto | MessageParsingError {
    return parse_as_OsfsDto(value);
  }
}

export function parse_as_Literal_of__quote_http_quote_0_quote_https_quote__endof_(
  value: JsonValue,
): "http" | "https" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "http") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "https") {
    return tmp_1;
  }
  return new MessageParsingError(`Could not parse ${value} as 'http' | 'https'`);
}
export function parse_as_HttpFsDto(value: JsonValue): HttpFsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "HttpFsDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a HttpFsDto`);
  }
  const temp_protocol = parse_as_Literal_of__quote_http_quote_0_quote_https_quote__endof_(valueObject.protocol);
  if (temp_protocol instanceof MessageParsingError) return temp_protocol;
  const temp_hostname = parse_as_str(valueObject.hostname);
  if (temp_hostname instanceof MessageParsingError) return temp_hostname;
  const temp_port = parse_as_Union_of_int0None_endof_(valueObject.port);
  if (temp_port instanceof MessageParsingError) return temp_port;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_search = parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(valueObject.search);
  if (temp_search instanceof MessageParsingError) return temp_search;
  return new HttpFsDto({
    protocol: temp_protocol,
    hostname: temp_hostname,
    port: temp_port,
    path: temp_path,
    search: temp_search,
  });
}
// Automatically generated via DataTransferObject for HttpFsDto
// Do not edit!
export class HttpFsDto {
  public protocol: "http" | "https";
  public hostname: string;
  public port: number | undefined;
  public path: string;
  public search: { [key: string]: string } | undefined;
  constructor(_params: {
    protocol: "http" | "https";
    hostname: string;
    port: number | undefined;
    path: string;
    search: { [key: string]: string } | undefined;
  }) {
    this.protocol = _params.protocol;
    this.hostname = _params.hostname;
    this.port = _params.port;
    this.path = _params.path;
    this.search = _params.search;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "HttpFsDto",
      protocol: this.protocol,
      hostname: this.hostname,
      port: toJsonValue(this.port),
      path: this.path,
      search: toJsonValue(this.search),
    };
  }
  public static fromJsonValue(value: JsonValue): HttpFsDto | MessageParsingError {
    return parse_as_HttpFsDto(value);
  }
}

export function parse_as_BucketFSDto(value: JsonValue): BucketFSDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "BucketFSDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a BucketFSDto`);
  }
  const temp_bucket_name = parse_as_str(valueObject.bucket_name);
  if (temp_bucket_name instanceof MessageParsingError) return temp_bucket_name;
  return new BucketFSDto({
    bucket_name: temp_bucket_name,
  });
}
// Automatically generated via DataTransferObject for BucketFSDto
// Do not edit!
export class BucketFSDto {
  public bucket_name: string;
  constructor(_params: {
    bucket_name: string;
  }) {
    this.bucket_name = _params.bucket_name;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "BucketFSDto",
      bucket_name: this.bucket_name,
    };
  }
  public static fromJsonValue(value: JsonValue): BucketFSDto | MessageParsingError {
    return parse_as_BucketFSDto(value);
  }
}

export function parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
  value: JsonValue,
): OsfsDto | HttpFsDto | BucketFSDto | MessageParsingError {
  const parsed_option_0 = parse_as_OsfsDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_HttpFsDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_BucketFSDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into OsfsDto | HttpFsDto | BucketFSDto`);
}
export function parse_as_ZipFsDto(value: JsonValue): ZipFsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ZipFsDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ZipFsDto`);
  }
  const temp_zip_file_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.zip_file_fs);
  if (temp_zip_file_fs instanceof MessageParsingError) return temp_zip_file_fs;
  const temp_zip_file_path = parse_as_str(valueObject.zip_file_path);
  if (temp_zip_file_path instanceof MessageParsingError) return temp_zip_file_path;
  return new ZipFsDto({
    zip_file_fs: temp_zip_file_fs,
    zip_file_path: temp_zip_file_path,
  });
}
// Automatically generated via DataTransferObject for ZipFsDto
// Do not edit!
export class ZipFsDto {
  public zip_file_fs: OsfsDto | HttpFsDto | BucketFSDto;
  public zip_file_path: string;
  constructor(_params: {
    zip_file_fs: OsfsDto | HttpFsDto | BucketFSDto;
    zip_file_path: string;
  }) {
    this.zip_file_fs = _params.zip_file_fs;
    this.zip_file_path = _params.zip_file_path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ZipFsDto",
      zip_file_fs: toJsonValue(this.zip_file_fs),
      zip_file_path: this.zip_file_path,
    };
  }
  public static fromJsonValue(value: JsonValue): ZipFsDto | MessageParsingError {
    return parse_as_ZipFsDto(value);
  }
}

export function parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(
  value: JsonValue,
): OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto | MessageParsingError {
  const parsed_option_0 = parse_as_OsfsDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_HttpFsDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_BucketFSDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_ZipFsDto(value);
  if (!(parsed_option_3 instanceof MessageParsingError)) {
    return parsed_option_3;
  }
  return new MessageParsingError(
    `Could not parse ${JSON.stringify(value)} into OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto`,
  );
}
export function parse_as_Tuple_of_int0int0int_endof_(value: JsonValue): [number, number, number] | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const temp_0 = parse_as_int(arr[0]);
  if (temp_0 instanceof MessageParsingError) return temp_0;
  const temp_1 = parse_as_int(arr[1]);
  if (temp_1 instanceof MessageParsingError) return temp_1;
  const temp_2 = parse_as_int(arr[2]);
  if (temp_2 instanceof MessageParsingError) return temp_2;
  return [temp_0, temp_1, temp_2];
}
export function parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
  value: JsonValue,
): "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "uint8") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "uint16") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "uint32") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof MessageParsingError) && tmp_3 === "uint64") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof MessageParsingError) && tmp_4 === "int64") {
    return tmp_4;
  }
  const tmp_5 = parse_as_str(value);
  if (!(tmp_5 instanceof MessageParsingError) && tmp_5 === "float32") {
    return tmp_5;
  }
  return new MessageParsingError(
    `Could not parse ${value} as 'uint8' | 'uint16' | 'uint32' | 'uint64' | 'int64' | 'float32'`,
  );
}
export function parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(
  value: JsonValue,
): "raw" | "jpeg" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "raw") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "jpeg") {
    return tmp_1;
  }
  return new MessageParsingError(`Could not parse ${value} as 'raw' | 'jpeg'`);
}
export function parse_as_PrecomputedChunksDataSourceDto(
  value: JsonValue,
): PrecomputedChunksDataSourceDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PrecomputedChunksDataSourceDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a PrecomputedChunksDataSourceDto`,
    );
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof MessageParsingError) return temp_url;
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_scale_key = parse_as_str(valueObject.scale_key);
  if (temp_scale_key instanceof MessageParsingError) return temp_scale_key;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof MessageParsingError) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof MessageParsingError) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof MessageParsingError) return temp_spatial_resolution;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof MessageParsingError) return temp_dtype;
  const temp_encoder = parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(valueObject.encoder);
  if (temp_encoder instanceof MessageParsingError) return temp_encoder;
  return new PrecomputedChunksDataSourceDto({
    url: temp_url,
    filesystem: temp_filesystem,
    path: temp_path,
    scale_key: temp_scale_key,
    interval: temp_interval,
    tile_shape: temp_tile_shape,
    spatial_resolution: temp_spatial_resolution,
    dtype: temp_dtype,
    encoder: temp_encoder,
  });
}
// Automatically generated via DataTransferObject for PrecomputedChunksDataSourceDto
// Do not edit!
export class PrecomputedChunksDataSourceDto {
  public url: UrlDto;
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public path: string;
  public scale_key: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public encoder: "raw" | "jpeg";
  constructor(_params: {
    url: UrlDto;
    filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    path: string;
    scale_key: string;
    interval: Interval5DDto;
    tile_shape: Shape5DDto;
    spatial_resolution: [number, number, number];
    dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
    encoder: "raw" | "jpeg";
  }) {
    this.url = _params.url;
    this.filesystem = _params.filesystem;
    this.path = _params.path;
    this.scale_key = _params.scale_key;
    this.interval = _params.interval;
    this.tile_shape = _params.tile_shape;
    this.spatial_resolution = _params.spatial_resolution;
    this.dtype = _params.dtype;
    this.encoder = _params.encoder;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "PrecomputedChunksDataSourceDto",
      url: this.url.toJsonValue(),
      filesystem: toJsonValue(this.filesystem),
      path: this.path,
      scale_key: this.scale_key,
      interval: this.interval.toJsonValue(),
      tile_shape: this.tile_shape.toJsonValue(),
      spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
      dtype: this.dtype,
      encoder: this.encoder,
    };
  }
  public static fromJsonValue(value: JsonValue): PrecomputedChunksDataSourceDto | MessageParsingError {
    return parse_as_PrecomputedChunksDataSourceDto(value);
  }
}

export function parse_as_DziSizeElementDto(value: JsonValue): DziSizeElementDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziSizeElementDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a DziSizeElementDto`);
  }
  const temp_Width = parse_as_int(valueObject.Width);
  if (temp_Width instanceof MessageParsingError) return temp_Width;
  const temp_Height = parse_as_int(valueObject.Height);
  if (temp_Height instanceof MessageParsingError) return temp_Height;
  return new DziSizeElementDto({
    Width: temp_Width,
    Height: temp_Height,
  });
}
// Automatically generated via DataTransferObject for DziSizeElementDto
// Do not edit!
export class DziSizeElementDto {
  public Width: number;
  public Height: number;
  constructor(_params: {
    Width: number;
    Height: number;
  }) {
    this.Width = _params.Width;
    this.Height = _params.Height;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziSizeElementDto",
      Width: this.Width,
      Height: this.Height,
    };
  }
  public static fromJsonValue(value: JsonValue): DziSizeElementDto | MessageParsingError {
    return parse_as_DziSizeElementDto(value);
  }
}

export function parse_as_Literal_of__quote_jpeg_quote_0_quote_jpg_quote_0_quote_png_quote__endof_(
  value: JsonValue,
): "jpeg" | "jpg" | "png" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "jpeg") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "jpg") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "png") {
    return tmp_2;
  }
  return new MessageParsingError(`Could not parse ${value} as 'jpeg' | 'jpg' | 'png'`);
}
export function parse_as_DziImageElementDto(value: JsonValue): DziImageElementDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziImageElementDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a DziImageElementDto`);
  }
  const temp_Format = parse_as_Literal_of__quote_jpeg_quote_0_quote_jpg_quote_0_quote_png_quote__endof_(
    valueObject.Format,
  );
  if (temp_Format instanceof MessageParsingError) return temp_Format;
  const temp_Overlap = parse_as_int(valueObject.Overlap);
  if (temp_Overlap instanceof MessageParsingError) return temp_Overlap;
  const temp_TileSize = parse_as_int(valueObject.TileSize);
  if (temp_TileSize instanceof MessageParsingError) return temp_TileSize;
  const temp_Size = parse_as_DziSizeElementDto(valueObject.Size);
  if (temp_Size instanceof MessageParsingError) return temp_Size;
  return new DziImageElementDto({
    Format: temp_Format,
    Overlap: temp_Overlap,
    TileSize: temp_TileSize,
    Size: temp_Size,
  });
}
// Automatically generated via DataTransferObject for DziImageElementDto
// Do not edit!
export class DziImageElementDto {
  public Format: "jpeg" | "jpg" | "png";
  public Overlap: number;
  public TileSize: number;
  public Size: DziSizeElementDto;
  constructor(_params: {
    Format: "jpeg" | "jpg" | "png";
    Overlap: number;
    TileSize: number;
    Size: DziSizeElementDto;
  }) {
    this.Format = _params.Format;
    this.Overlap = _params.Overlap;
    this.TileSize = _params.TileSize;
    this.Size = _params.Size;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziImageElementDto",
      Format: this.Format,
      Overlap: this.Overlap,
      TileSize: this.TileSize,
      Size: this.Size.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): DziImageElementDto | MessageParsingError {
    return parse_as_DziImageElementDto(value);
  }
}

export function parse_as_Literal_of_103_endof_(value: JsonValue): 1 | 3 | MessageParsingError {
  const tmp_0 = parse_as_int(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === 1) {
    return tmp_0;
  }
  const tmp_1 = parse_as_int(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === 3) {
    return tmp_1;
  }
  return new MessageParsingError(`Could not parse ${value} as 1 | 3`);
}
export function parse_as_DziLevelSinkDto(value: JsonValue): DziLevelSinkDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziLevelSinkDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a DziLevelSinkDto`);
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_xml_path = parse_as_str(valueObject.xml_path);
  if (temp_xml_path instanceof MessageParsingError) return temp_xml_path;
  const temp_dzi_image = parse_as_DziImageElementDto(valueObject.dzi_image);
  if (temp_dzi_image instanceof MessageParsingError) return temp_dzi_image;
  const temp_num_channels = parse_as_Literal_of_103_endof_(valueObject.num_channels);
  if (temp_num_channels instanceof MessageParsingError) return temp_num_channels;
  const temp_level_index = parse_as_int(valueObject.level_index);
  if (temp_level_index instanceof MessageParsingError) return temp_level_index;
  return new DziLevelSinkDto({
    filesystem: temp_filesystem,
    xml_path: temp_xml_path,
    dzi_image: temp_dzi_image,
    num_channels: temp_num_channels,
    level_index: temp_level_index,
  });
}
// Automatically generated via DataTransferObject for DziLevelSinkDto
// Do not edit!
export class DziLevelSinkDto {
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public xml_path: string;
  public dzi_image: DziImageElementDto;
  public num_channels: 1 | 3;
  public level_index: number;
  constructor(_params: {
    filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    xml_path: string;
    dzi_image: DziImageElementDto;
    num_channels: 1 | 3;
    level_index: number;
  }) {
    this.filesystem = _params.filesystem;
    this.xml_path = _params.xml_path;
    this.dzi_image = _params.dzi_image;
    this.num_channels = _params.num_channels;
    this.level_index = _params.level_index;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziLevelSinkDto",
      filesystem: toJsonValue(this.filesystem),
      xml_path: this.xml_path,
      dzi_image: this.dzi_image.toJsonValue(),
      num_channels: this.num_channels,
      level_index: this.level_index,
    };
  }
  public static fromJsonValue(value: JsonValue): DziLevelSinkDto | MessageParsingError {
    return parse_as_DziLevelSinkDto(value);
  }
}

export function parse_as_DziLevelDataSourceDto(value: JsonValue): DziLevelDataSourceDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziLevelDataSourceDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a DziLevelDataSourceDto`);
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_xml_path = parse_as_str(valueObject.xml_path);
  if (temp_xml_path instanceof MessageParsingError) return temp_xml_path;
  const temp_dzi_image = parse_as_DziImageElementDto(valueObject.dzi_image);
  if (temp_dzi_image instanceof MessageParsingError) return temp_dzi_image;
  const temp_num_channels = parse_as_Literal_of_103_endof_(valueObject.num_channels);
  if (temp_num_channels instanceof MessageParsingError) return temp_num_channels;
  const temp_level_index = parse_as_int(valueObject.level_index);
  if (temp_level_index instanceof MessageParsingError) return temp_level_index;
  return new DziLevelDataSourceDto({
    filesystem: temp_filesystem,
    xml_path: temp_xml_path,
    dzi_image: temp_dzi_image,
    num_channels: temp_num_channels,
    level_index: temp_level_index,
  });
}
// Automatically generated via DataTransferObject for DziLevelDataSourceDto
// Do not edit!
export class DziLevelDataSourceDto {
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public xml_path: string;
  public dzi_image: DziImageElementDto;
  public num_channels: 1 | 3;
  public level_index: number;
  constructor(_params: {
    filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    xml_path: string;
    dzi_image: DziImageElementDto;
    num_channels: 1 | 3;
    level_index: number;
  }) {
    this.filesystem = _params.filesystem;
    this.xml_path = _params.xml_path;
    this.dzi_image = _params.dzi_image;
    this.num_channels = _params.num_channels;
    this.level_index = _params.level_index;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziLevelDataSourceDto",
      filesystem: toJsonValue(this.filesystem),
      xml_path: this.xml_path,
      dzi_image: this.dzi_image.toJsonValue(),
      num_channels: this.num_channels,
      level_index: this.level_index,
    };
  }
  public static fromJsonValue(value: JsonValue): DziLevelDataSourceDto | MessageParsingError {
    return parse_as_DziLevelDataSourceDto(value);
  }
}

export function parse_as_N5GzipCompressorDto(value: JsonValue): N5GzipCompressorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["type"] != "gzip") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a N5GzipCompressorDto`);
  }
  const temp_level = parse_as_int(valueObject.level);
  if (temp_level instanceof MessageParsingError) return temp_level;
  return new N5GzipCompressorDto({
    level: temp_level,
  });
}
// Automatically generated via DataTransferObject for N5GzipCompressorDto
// Do not edit!
export class N5GzipCompressorDto {
  public level: number;
  constructor(_params: {
    level: number;
  }) {
    this.level = _params.level;
  }
  public toJsonValue(): JsonObject {
    return {
      "type": "gzip",
      level: this.level,
    };
  }
  public static fromJsonValue(value: JsonValue): N5GzipCompressorDto | MessageParsingError {
    return parse_as_N5GzipCompressorDto(value);
  }
}

export function parse_as_N5Bzip2CompressorDto(value: JsonValue): N5Bzip2CompressorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["type"] != "bzip2") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a N5Bzip2CompressorDto`);
  }
  const temp_blockSize = parse_as_int(valueObject.blockSize);
  if (temp_blockSize instanceof MessageParsingError) return temp_blockSize;
  return new N5Bzip2CompressorDto({
    blockSize: temp_blockSize,
  });
}
// Automatically generated via DataTransferObject for N5Bzip2CompressorDto
// Do not edit!
export class N5Bzip2CompressorDto {
  public blockSize: number;
  constructor(_params: {
    blockSize: number;
  }) {
    this.blockSize = _params.blockSize;
  }
  public toJsonValue(): JsonObject {
    return {
      "type": "bzip2",
      blockSize: this.blockSize,
    };
  }
  public static fromJsonValue(value: JsonValue): N5Bzip2CompressorDto | MessageParsingError {
    return parse_as_N5Bzip2CompressorDto(value);
  }
}

export function parse_as_N5XzCompressorDto(value: JsonValue): N5XzCompressorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["type"] != "xz") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a N5XzCompressorDto`);
  }
  const temp_preset = parse_as_int(valueObject.preset);
  if (temp_preset instanceof MessageParsingError) return temp_preset;
  return new N5XzCompressorDto({
    preset: temp_preset,
  });
}
// Automatically generated via DataTransferObject for N5XzCompressorDto
// Do not edit!
export class N5XzCompressorDto {
  public preset: number;
  constructor(_params: {
    preset: number;
  }) {
    this.preset = _params.preset;
  }
  public toJsonValue(): JsonObject {
    return {
      "type": "xz",
      preset: this.preset,
    };
  }
  public static fromJsonValue(value: JsonValue): N5XzCompressorDto | MessageParsingError {
    return parse_as_N5XzCompressorDto(value);
  }
}

export function parse_as_N5RawCompressorDto(value: JsonValue): N5RawCompressorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["type"] != "raw") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a N5RawCompressorDto`);
  }
  return new N5RawCompressorDto({});
}
// Automatically generated via DataTransferObject for N5RawCompressorDto
// Do not edit!
export class N5RawCompressorDto {
  constructor(_params: {}) {
  }
  public toJsonValue(): JsonObject {
    return {
      "type": "raw",
    };
  }
  public static fromJsonValue(value: JsonValue): N5RawCompressorDto | MessageParsingError {
    return parse_as_N5RawCompressorDto(value);
  }
}

export function parse_as_Tuple_of_int0_varlen__endof_(value: JsonValue): Array<number> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<number> = [];
  for (let item of arr) {
    let parsed_item = parse_as_int(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Tuple_of_str0_varlen__endof_(value: JsonValue): Array<string> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<string> = [];
  for (let item of arr) {
    let parsed_item = parse_as_str(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Union_of_Tuple_of_str0_varlen__endof_0None_endof_(
  value: JsonValue,
): Array<string> | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_Tuple_of_str0_varlen__endof_(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into Array<string> | undefined`);
}
export function parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
  value: JsonValue,
): N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto | MessageParsingError {
  const parsed_option_0 = parse_as_N5GzipCompressorDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5Bzip2CompressorDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_N5XzCompressorDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_N5RawCompressorDto(value);
  if (!(parsed_option_3 instanceof MessageParsingError)) {
    return parsed_option_3;
  }
  return new MessageParsingError(
    `Could not parse ${
      JSON.stringify(value)
    } into N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto`,
  );
}
export function parse_as_N5DatasetAttributesDto(value: JsonValue): N5DatasetAttributesDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  const temp_dimensions = parse_as_Tuple_of_int0_varlen__endof_(valueObject.dimensions);
  if (temp_dimensions instanceof MessageParsingError) return temp_dimensions;
  const temp_blockSize = parse_as_Tuple_of_int0_varlen__endof_(valueObject.blockSize);
  if (temp_blockSize instanceof MessageParsingError) return temp_blockSize;
  const temp_axes = parse_as_Union_of_Tuple_of_str0_varlen__endof_0None_endof_(valueObject.axes);
  if (temp_axes instanceof MessageParsingError) return temp_axes;
  const temp_dataType =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dataType,
    );
  if (temp_dataType instanceof MessageParsingError) return temp_dataType;
  const temp_compression =
    parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
      valueObject.compression,
    );
  if (temp_compression instanceof MessageParsingError) return temp_compression;
  return new N5DatasetAttributesDto({
    dimensions: temp_dimensions,
    blockSize: temp_blockSize,
    axes: temp_axes,
    dataType: temp_dataType,
    compression: temp_compression,
  });
}
// Automatically generated via DataTransferObject for N5DatasetAttributesDto
// Do not edit!
export class N5DatasetAttributesDto {
  public dimensions: Array<number>;
  public blockSize: Array<number>;
  public axes: Array<string> | undefined;
  public dataType: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public compression: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  constructor(_params: {
    dimensions: Array<number>;
    blockSize: Array<number>;
    axes: Array<string> | undefined;
    dataType: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
    compression: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  }) {
    this.dimensions = _params.dimensions;
    this.blockSize = _params.blockSize;
    this.axes = _params.axes;
    this.dataType = _params.dataType;
    this.compression = _params.compression;
  }
  public toJsonValue(): JsonObject {
    return {
      dimensions: this.dimensions.map((item) => item),
      blockSize: this.blockSize.map((item) => item),
      axes: toJsonValue(this.axes),
      dataType: this.dataType,
      compression: toJsonValue(this.compression),
    };
  }
  public static fromJsonValue(value: JsonValue): N5DatasetAttributesDto | MessageParsingError {
    return parse_as_N5DatasetAttributesDto(value);
  }
}

export function parse_as_N5DataSourceDto(value: JsonValue): N5DataSourceDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "N5DataSourceDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a N5DataSourceDto`);
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof MessageParsingError) return temp_url;
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof MessageParsingError) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof MessageParsingError) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof MessageParsingError) return temp_spatial_resolution;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof MessageParsingError) return temp_dtype;
  const temp_compressor =
    parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
      valueObject.compressor,
    );
  if (temp_compressor instanceof MessageParsingError) return temp_compressor;
  const temp_c_axiskeys_on_disk = parse_as_str(valueObject.c_axiskeys_on_disk);
  if (temp_c_axiskeys_on_disk instanceof MessageParsingError) return temp_c_axiskeys_on_disk;
  return new N5DataSourceDto({
    url: temp_url,
    filesystem: temp_filesystem,
    path: temp_path,
    interval: temp_interval,
    tile_shape: temp_tile_shape,
    spatial_resolution: temp_spatial_resolution,
    dtype: temp_dtype,
    compressor: temp_compressor,
    c_axiskeys_on_disk: temp_c_axiskeys_on_disk,
  });
}
// Automatically generated via DataTransferObject for N5DataSourceDto
// Do not edit!
export class N5DataSourceDto {
  public url: UrlDto;
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public path: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public compressor: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  public c_axiskeys_on_disk: string;
  constructor(_params: {
    url: UrlDto;
    filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    path: string;
    interval: Interval5DDto;
    tile_shape: Shape5DDto;
    spatial_resolution: [number, number, number];
    dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
    compressor: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
    c_axiskeys_on_disk: string;
  }) {
    this.url = _params.url;
    this.filesystem = _params.filesystem;
    this.path = _params.path;
    this.interval = _params.interval;
    this.tile_shape = _params.tile_shape;
    this.spatial_resolution = _params.spatial_resolution;
    this.dtype = _params.dtype;
    this.compressor = _params.compressor;
    this.c_axiskeys_on_disk = _params.c_axiskeys_on_disk;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "N5DataSourceDto",
      url: this.url.toJsonValue(),
      filesystem: toJsonValue(this.filesystem),
      path: this.path,
      interval: this.interval.toJsonValue(),
      tile_shape: this.tile_shape.toJsonValue(),
      spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
      dtype: this.dtype,
      compressor: toJsonValue(this.compressor),
      c_axiskeys_on_disk: this.c_axiskeys_on_disk,
    };
  }
  public static fromJsonValue(value: JsonValue): N5DataSourceDto | MessageParsingError {
    return parse_as_N5DataSourceDto(value);
  }
}

export function parse_as_SkimageDataSourceDto(value: JsonValue): SkimageDataSourceDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SkimageDataSourceDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a SkimageDataSourceDto`);
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof MessageParsingError) return temp_url;
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof MessageParsingError) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof MessageParsingError) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof MessageParsingError) return temp_spatial_resolution;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof MessageParsingError) return temp_dtype;
  return new SkimageDataSourceDto({
    url: temp_url,
    filesystem: temp_filesystem,
    path: temp_path,
    interval: temp_interval,
    tile_shape: temp_tile_shape,
    spatial_resolution: temp_spatial_resolution,
    dtype: temp_dtype,
  });
}
// Automatically generated via DataTransferObject for SkimageDataSourceDto
// Do not edit!
export class SkimageDataSourceDto {
  public url: UrlDto;
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public path: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  constructor(_params: {
    url: UrlDto;
    filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    path: string;
    interval: Interval5DDto;
    tile_shape: Shape5DDto;
    spatial_resolution: [number, number, number];
    dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  }) {
    this.url = _params.url;
    this.filesystem = _params.filesystem;
    this.path = _params.path;
    this.interval = _params.interval;
    this.tile_shape = _params.tile_shape;
    this.spatial_resolution = _params.spatial_resolution;
    this.dtype = _params.dtype;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "SkimageDataSourceDto",
      url: this.url.toJsonValue(),
      filesystem: toJsonValue(this.filesystem),
      path: this.path,
      interval: this.interval.toJsonValue(),
      tile_shape: this.tile_shape.toJsonValue(),
      spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
      dtype: this.dtype,
    };
  }
  public static fromJsonValue(value: JsonValue): SkimageDataSourceDto | MessageParsingError {
    return parse_as_SkimageDataSourceDto(value);
  }
}

export function parse_as_PrecomputedChunksSinkDto(value: JsonValue): PrecomputedChunksSinkDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PrecomputedChunksSinkDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a PrecomputedChunksSinkDto`,
    );
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof MessageParsingError) return temp_tile_shape;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof MessageParsingError) return temp_interval;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof MessageParsingError) return temp_dtype;
  const temp_scale_key = parse_as_str(valueObject.scale_key);
  if (temp_scale_key instanceof MessageParsingError) return temp_scale_key;
  const temp_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.resolution);
  if (temp_resolution instanceof MessageParsingError) return temp_resolution;
  const temp_encoding = parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(valueObject.encoding);
  if (temp_encoding instanceof MessageParsingError) return temp_encoding;
  return new PrecomputedChunksSinkDto({
    filesystem: temp_filesystem,
    path: temp_path,
    tile_shape: temp_tile_shape,
    interval: temp_interval,
    dtype: temp_dtype,
    scale_key: temp_scale_key,
    resolution: temp_resolution,
    encoding: temp_encoding,
  });
}
// Automatically generated via DataTransferObject for PrecomputedChunksSinkDto
// Do not edit!
export class PrecomputedChunksSinkDto {
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto;
  public path: string;
  public tile_shape: Shape5DDto;
  public interval: Interval5DDto;
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public scale_key: string;
  public resolution: [number, number, number];
  public encoding: "raw" | "jpeg";
  constructor(_params: {
    filesystem: OsfsDto | HttpFsDto | BucketFSDto;
    path: string;
    tile_shape: Shape5DDto;
    interval: Interval5DDto;
    dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
    scale_key: string;
    resolution: [number, number, number];
    encoding: "raw" | "jpeg";
  }) {
    this.filesystem = _params.filesystem;
    this.path = _params.path;
    this.tile_shape = _params.tile_shape;
    this.interval = _params.interval;
    this.dtype = _params.dtype;
    this.scale_key = _params.scale_key;
    this.resolution = _params.resolution;
    this.encoding = _params.encoding;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "PrecomputedChunksSinkDto",
      filesystem: toJsonValue(this.filesystem),
      path: this.path,
      tile_shape: this.tile_shape.toJsonValue(),
      interval: this.interval.toJsonValue(),
      dtype: this.dtype,
      scale_key: this.scale_key,
      resolution: [this.resolution[0], this.resolution[1], this.resolution[2]],
      encoding: this.encoding,
    };
  }
  public static fromJsonValue(value: JsonValue): PrecomputedChunksSinkDto | MessageParsingError {
    return parse_as_PrecomputedChunksSinkDto(value);
  }
}

export function parse_as_N5DataSinkDto(value: JsonValue): N5DataSinkDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "N5DataSinkDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a N5DataSinkDto`);
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof MessageParsingError) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof MessageParsingError) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof MessageParsingError) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof MessageParsingError) return temp_spatial_resolution;
  const temp_c_axiskeys = parse_as_str(valueObject.c_axiskeys);
  if (temp_c_axiskeys instanceof MessageParsingError) return temp_c_axiskeys;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof MessageParsingError) return temp_dtype;
  const temp_compressor =
    parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
      valueObject.compressor,
    );
  if (temp_compressor instanceof MessageParsingError) return temp_compressor;
  return new N5DataSinkDto({
    filesystem: temp_filesystem,
    path: temp_path,
    interval: temp_interval,
    tile_shape: temp_tile_shape,
    spatial_resolution: temp_spatial_resolution,
    c_axiskeys: temp_c_axiskeys,
    dtype: temp_dtype,
    compressor: temp_compressor,
  });
}
// Automatically generated via DataTransferObject for N5DataSinkDto
// Do not edit!
export class N5DataSinkDto {
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public path: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public c_axiskeys: string;
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public compressor: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  constructor(_params: {
    filesystem: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    path: string;
    interval: Interval5DDto;
    tile_shape: Shape5DDto;
    spatial_resolution: [number, number, number];
    c_axiskeys: string;
    dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
    compressor: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  }) {
    this.filesystem = _params.filesystem;
    this.path = _params.path;
    this.interval = _params.interval;
    this.tile_shape = _params.tile_shape;
    this.spatial_resolution = _params.spatial_resolution;
    this.c_axiskeys = _params.c_axiskeys;
    this.dtype = _params.dtype;
    this.compressor = _params.compressor;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "N5DataSinkDto",
      filesystem: toJsonValue(this.filesystem),
      path: this.path,
      interval: this.interval.toJsonValue(),
      tile_shape: this.tile_shape.toJsonValue(),
      spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
      c_axiskeys: this.c_axiskeys,
      dtype: this.dtype,
      compressor: toJsonValue(this.compressor),
    };
  }
  public static fromJsonValue(value: JsonValue): N5DataSinkDto | MessageParsingError {
    return parse_as_N5DataSinkDto(value);
  }
}

export function parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
  value: JsonValue,
):
  | PrecomputedChunksDataSourceDto
  | N5DataSourceDto
  | SkimageDataSourceDto
  | DziLevelDataSourceDto
  | MessageParsingError {
  const parsed_option_0 = parse_as_PrecomputedChunksDataSourceDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5DataSourceDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_SkimageDataSourceDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_DziLevelDataSourceDto(value);
  if (!(parsed_option_3 instanceof MessageParsingError)) {
    return parsed_option_3;
  }
  return new MessageParsingError(
    `Could not parse ${
      JSON.stringify(value)
    } into PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto`,
  );
}
export function parse_as_Tuple_of_Tuple_of_int0int0int_endof_0_varlen__endof_(
  value: JsonValue,
): Array<[number, number, number]> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<[number, number, number]> = [];
  for (let item of arr) {
    let parsed_item = parse_as_Tuple_of_int0int0int_endof_(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_PixelAnnotationDto(value: JsonValue): PixelAnnotationDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PixelAnnotationDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a PixelAnnotationDto`);
  }
  const temp_raw_data =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.raw_data,
    );
  if (temp_raw_data instanceof MessageParsingError) return temp_raw_data;
  const temp_points = parse_as_Tuple_of_Tuple_of_int0int0int_endof_0_varlen__endof_(valueObject.points);
  if (temp_points instanceof MessageParsingError) return temp_points;
  return new PixelAnnotationDto({
    raw_data: temp_raw_data,
    points: temp_points,
  });
}
// Automatically generated via DataTransferObject for PixelAnnotationDto
// Do not edit!
export class PixelAnnotationDto {
  public raw_data: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
  public points: Array<[number, number, number]>;
  constructor(_params: {
    raw_data: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
    points: Array<[number, number, number]>;
  }) {
    this.raw_data = _params.raw_data;
    this.points = _params.points;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "PixelAnnotationDto",
      raw_data: toJsonValue(this.raw_data),
      points: this.points.map((item) => [item[0], item[1], item[2]]),
    };
  }
  public static fromJsonValue(value: JsonValue): PixelAnnotationDto | MessageParsingError {
    return parse_as_PixelAnnotationDto(value);
  }
}

export function parse_as_RpcErrorDto(value: JsonValue): RpcErrorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RpcErrorDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a RpcErrorDto`);
  }
  const temp_error = parse_as_str(valueObject.error);
  if (temp_error instanceof MessageParsingError) return temp_error;
  return new RpcErrorDto({
    error: temp_error,
  });
}
// Automatically generated via DataTransferObject for RpcErrorDto
// Do not edit!
export class RpcErrorDto {
  public error: string;
  constructor(_params: {
    error: string;
  }) {
    this.error = _params.error;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RpcErrorDto",
      error: this.error,
    };
  }
  public static fromJsonValue(value: JsonValue): RpcErrorDto | MessageParsingError {
    return parse_as_RpcErrorDto(value);
  }
}

export function parse_as_bool(value: JsonValue): boolean | MessageParsingError {
  return ensureJsonBoolean(value);
}
export function parse_as_SetLiveUpdateParams(value: JsonValue): SetLiveUpdateParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SetLiveUpdateParams") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a SetLiveUpdateParams`);
  }
  const temp_live_update = parse_as_bool(valueObject.live_update);
  if (temp_live_update instanceof MessageParsingError) return temp_live_update;
  return new SetLiveUpdateParams({
    live_update: temp_live_update,
  });
}
// Automatically generated via DataTransferObject for SetLiveUpdateParams
// Do not edit!
export class SetLiveUpdateParams {
  public live_update: boolean;
  constructor(_params: {
    live_update: boolean;
  }) {
    this.live_update = _params.live_update;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "SetLiveUpdateParams",
      live_update: this.live_update,
    };
  }
  public static fromJsonValue(value: JsonValue): SetLiveUpdateParams | MessageParsingError {
    return parse_as_SetLiveUpdateParams(value);
  }
}

export function parse_as_RecolorLabelParams(value: JsonValue): RecolorLabelParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RecolorLabelParams") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a RecolorLabelParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof MessageParsingError) return temp_label_name;
  const temp_new_color = parse_as_ColorDto(valueObject.new_color);
  if (temp_new_color instanceof MessageParsingError) return temp_new_color;
  return new RecolorLabelParams({
    label_name: temp_label_name,
    new_color: temp_new_color,
  });
}
// Automatically generated via DataTransferObject for RecolorLabelParams
// Do not edit!
export class RecolorLabelParams {
  public label_name: string;
  public new_color: ColorDto;
  constructor(_params: {
    label_name: string;
    new_color: ColorDto;
  }) {
    this.label_name = _params.label_name;
    this.new_color = _params.new_color;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RecolorLabelParams",
      label_name: this.label_name,
      new_color: this.new_color.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): RecolorLabelParams | MessageParsingError {
    return parse_as_RecolorLabelParams(value);
  }
}

export function parse_as_RenameLabelParams(value: JsonValue): RenameLabelParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RenameLabelParams") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a RenameLabelParams`);
  }
  const temp_old_name = parse_as_str(valueObject.old_name);
  if (temp_old_name instanceof MessageParsingError) return temp_old_name;
  const temp_new_name = parse_as_str(valueObject.new_name);
  if (temp_new_name instanceof MessageParsingError) return temp_new_name;
  return new RenameLabelParams({
    old_name: temp_old_name,
    new_name: temp_new_name,
  });
}
// Automatically generated via DataTransferObject for RenameLabelParams
// Do not edit!
export class RenameLabelParams {
  public old_name: string;
  public new_name: string;
  constructor(_params: {
    old_name: string;
    new_name: string;
  }) {
    this.old_name = _params.old_name;
    this.new_name = _params.new_name;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RenameLabelParams",
      old_name: this.old_name,
      new_name: this.new_name,
    };
  }
  public static fromJsonValue(value: JsonValue): RenameLabelParams | MessageParsingError {
    return parse_as_RenameLabelParams(value);
  }
}

export function parse_as_CreateLabelParams(value: JsonValue): CreateLabelParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CreateLabelParams") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a CreateLabelParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof MessageParsingError) return temp_label_name;
  const temp_color = parse_as_ColorDto(valueObject.color);
  if (temp_color instanceof MessageParsingError) return temp_color;
  return new CreateLabelParams({
    label_name: temp_label_name,
    color: temp_color,
  });
}
// Automatically generated via DataTransferObject for CreateLabelParams
// Do not edit!
export class CreateLabelParams {
  public label_name: string;
  public color: ColorDto;
  constructor(_params: {
    label_name: string;
    color: ColorDto;
  }) {
    this.label_name = _params.label_name;
    this.color = _params.color;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CreateLabelParams",
      label_name: this.label_name,
      color: this.color.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): CreateLabelParams | MessageParsingError {
    return parse_as_CreateLabelParams(value);
  }
}

export function parse_as_RemoveLabelParams(value: JsonValue): RemoveLabelParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RemoveLabelParams") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a RemoveLabelParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof MessageParsingError) return temp_label_name;
  return new RemoveLabelParams({
    label_name: temp_label_name,
  });
}
// Automatically generated via DataTransferObject for RemoveLabelParams
// Do not edit!
export class RemoveLabelParams {
  public label_name: string;
  constructor(_params: {
    label_name: string;
  }) {
    this.label_name = _params.label_name;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RemoveLabelParams",
      label_name: this.label_name,
    };
  }
  public static fromJsonValue(value: JsonValue): RemoveLabelParams | MessageParsingError {
    return parse_as_RemoveLabelParams(value);
  }
}

export function parse_as_AddPixelAnnotationParams(value: JsonValue): AddPixelAnnotationParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "AddPixelAnnotationParams") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a AddPixelAnnotationParams`,
    );
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof MessageParsingError) return temp_label_name;
  const temp_pixel_annotation = parse_as_PixelAnnotationDto(valueObject.pixel_annotation);
  if (temp_pixel_annotation instanceof MessageParsingError) return temp_pixel_annotation;
  return new AddPixelAnnotationParams({
    label_name: temp_label_name,
    pixel_annotation: temp_pixel_annotation,
  });
}
// Automatically generated via DataTransferObject for AddPixelAnnotationParams
// Do not edit!
export class AddPixelAnnotationParams {
  public label_name: string;
  public pixel_annotation: PixelAnnotationDto;
  constructor(_params: {
    label_name: string;
    pixel_annotation: PixelAnnotationDto;
  }) {
    this.label_name = _params.label_name;
    this.pixel_annotation = _params.pixel_annotation;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "AddPixelAnnotationParams",
      label_name: this.label_name,
      pixel_annotation: this.pixel_annotation.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): AddPixelAnnotationParams | MessageParsingError {
    return parse_as_AddPixelAnnotationParams(value);
  }
}

export function parse_as_RemovePixelAnnotationParams(
  value: JsonValue,
): RemovePixelAnnotationParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RemovePixelAnnotationParams") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a RemovePixelAnnotationParams`,
    );
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof MessageParsingError) return temp_label_name;
  const temp_pixel_annotation = parse_as_PixelAnnotationDto(valueObject.pixel_annotation);
  if (temp_pixel_annotation instanceof MessageParsingError) return temp_pixel_annotation;
  return new RemovePixelAnnotationParams({
    label_name: temp_label_name,
    pixel_annotation: temp_pixel_annotation,
  });
}
// Automatically generated via DataTransferObject for RemovePixelAnnotationParams
// Do not edit!
export class RemovePixelAnnotationParams {
  public label_name: string;
  public pixel_annotation: PixelAnnotationDto;
  constructor(_params: {
    label_name: string;
    pixel_annotation: PixelAnnotationDto;
  }) {
    this.label_name = _params.label_name;
    this.pixel_annotation = _params.pixel_annotation;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RemovePixelAnnotationParams",
      label_name: this.label_name,
      pixel_annotation: this.pixel_annotation.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): RemovePixelAnnotationParams | MessageParsingError {
    return parse_as_RemovePixelAnnotationParams(value);
  }
}

export function parse_as_Tuple_of_PixelAnnotationDto0_varlen__endof_(
  value: JsonValue,
): Array<PixelAnnotationDto> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<PixelAnnotationDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_PixelAnnotationDto(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_LabelDto(value: JsonValue): LabelDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LabelDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a LabelDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_color = parse_as_ColorDto(valueObject.color);
  if (temp_color instanceof MessageParsingError) return temp_color;
  const temp_annotations = parse_as_Tuple_of_PixelAnnotationDto0_varlen__endof_(valueObject.annotations);
  if (temp_annotations instanceof MessageParsingError) return temp_annotations;
  return new LabelDto({
    name: temp_name,
    color: temp_color,
    annotations: temp_annotations,
  });
}
// Automatically generated via DataTransferObject for LabelDto
// Do not edit!
export class LabelDto {
  public name: string;
  public color: ColorDto;
  public annotations: Array<PixelAnnotationDto>;
  constructor(_params: {
    name: string;
    color: ColorDto;
    annotations: Array<PixelAnnotationDto>;
  }) {
    this.name = _params.name;
    this.color = _params.color;
    this.annotations = _params.annotations;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "LabelDto",
      name: this.name,
      color: this.color.toJsonValue(),
      annotations: this.annotations.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): LabelDto | MessageParsingError {
    return parse_as_LabelDto(value);
  }
}

export function parse_as_Tuple_of_LabelDto0_varlen__endof_(value: JsonValue): Array<LabelDto> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<LabelDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_LabelDto(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_BrushingAppletStateDto(value: JsonValue): BrushingAppletStateDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "BrushingAppletStateDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a BrushingAppletStateDto`);
  }
  const temp_labels = parse_as_Tuple_of_LabelDto0_varlen__endof_(valueObject.labels);
  if (temp_labels instanceof MessageParsingError) return temp_labels;
  return new BrushingAppletStateDto({
    labels: temp_labels,
  });
}
// Automatically generated via DataTransferObject for BrushingAppletStateDto
// Do not edit!
export class BrushingAppletStateDto {
  public labels: Array<LabelDto>;
  constructor(_params: {
    labels: Array<LabelDto>;
  }) {
    this.labels = _params.labels;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "BrushingAppletStateDto",
      labels: this.labels.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): BrushingAppletStateDto | MessageParsingError {
    return parse_as_BrushingAppletStateDto(value);
  }
}

export function parse_as_JobFinishedDto(value: JsonValue): JobFinishedDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "JobFinishedDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a JobFinishedDto`);
  }
  const temp_error_message = parse_as_Union_of_str0None_endof_(valueObject.error_message);
  if (temp_error_message instanceof MessageParsingError) return temp_error_message;
  return new JobFinishedDto({
    error_message: temp_error_message,
  });
}
// Automatically generated via DataTransferObject for JobFinishedDto
// Do not edit!
export class JobFinishedDto {
  public error_message: string | undefined;
  constructor(_params: {
    error_message: string | undefined;
  }) {
    this.error_message = _params.error_message;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "JobFinishedDto",
      error_message: toJsonValue(this.error_message),
    };
  }
  public static fromJsonValue(value: JsonValue): JobFinishedDto | MessageParsingError {
    return parse_as_JobFinishedDto(value);
  }
}

export function parse_as_JobIsPendingDto(value: JsonValue): JobIsPendingDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "JobIsPendingDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a JobIsPendingDto`);
  }
  return new JobIsPendingDto({});
}
// Automatically generated via DataTransferObject for JobIsPendingDto
// Do not edit!
export class JobIsPendingDto {
  constructor(_params: {}) {
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "JobIsPendingDto",
    };
  }
  public static fromJsonValue(value: JsonValue): JobIsPendingDto | MessageParsingError {
    return parse_as_JobIsPendingDto(value);
  }
}

export function parse_as_JobIsRunningDto(value: JsonValue): JobIsRunningDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "JobIsRunningDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a JobIsRunningDto`);
  }
  const temp_num_completed_steps = parse_as_int(valueObject.num_completed_steps);
  if (temp_num_completed_steps instanceof MessageParsingError) return temp_num_completed_steps;
  const temp_num_dispatched_steps = parse_as_int(valueObject.num_dispatched_steps);
  if (temp_num_dispatched_steps instanceof MessageParsingError) return temp_num_dispatched_steps;
  return new JobIsRunningDto({
    num_completed_steps: temp_num_completed_steps,
    num_dispatched_steps: temp_num_dispatched_steps,
  });
}
// Automatically generated via DataTransferObject for JobIsRunningDto
// Do not edit!
export class JobIsRunningDto {
  public num_completed_steps: number;
  public num_dispatched_steps: number;
  constructor(_params: {
    num_completed_steps: number;
    num_dispatched_steps: number;
  }) {
    this.num_completed_steps = _params.num_completed_steps;
    this.num_dispatched_steps = _params.num_dispatched_steps;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "JobIsRunningDto",
      num_completed_steps: this.num_completed_steps,
      num_dispatched_steps: this.num_dispatched_steps,
    };
  }
  public static fromJsonValue(value: JsonValue): JobIsRunningDto | MessageParsingError {
    return parse_as_JobIsRunningDto(value);
  }
}

export function parse_as_JobCanceledDto(value: JsonValue): JobCanceledDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "JobCanceledDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a JobCanceledDto`);
  }
  const temp_message = parse_as_str(valueObject.message);
  if (temp_message instanceof MessageParsingError) return temp_message;
  return new JobCanceledDto({
    message: temp_message,
  });
}
// Automatically generated via DataTransferObject for JobCanceledDto
// Do not edit!
export class JobCanceledDto {
  public message: string;
  constructor(_params: {
    message: string;
  }) {
    this.message = _params.message;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "JobCanceledDto",
      message: this.message,
    };
  }
  public static fromJsonValue(value: JsonValue): JobCanceledDto | MessageParsingError {
    return parse_as_JobCanceledDto(value);
  }
}

export function parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
  value: JsonValue,
): JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto | MessageParsingError {
  const parsed_option_0 = parse_as_JobFinishedDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_JobIsPendingDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_JobIsRunningDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_JobCanceledDto(value);
  if (!(parsed_option_3 instanceof MessageParsingError)) {
    return parsed_option_3;
  }
  return new MessageParsingError(
    `Could not parse ${JSON.stringify(value)} into JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto`,
  );
}
export function parse_as_JobDto(value: JsonValue): JobDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "JobDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a JobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof MessageParsingError) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof MessageParsingError) return temp_uuid;
  const temp_status = parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
    valueObject.status,
  );
  if (temp_status instanceof MessageParsingError) return temp_status;
  return new JobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
  });
}
// Automatically generated via DataTransferObject for JobDto
// Do not edit!
export class JobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "JobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: toJsonValue(this.status),
    };
  }
  public static fromJsonValue(value: JsonValue): JobDto | MessageParsingError {
    return parse_as_JobDto(value);
  }
}

export function parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
  value: JsonValue,
): PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto | MessageParsingError {
  const parsed_option_0 = parse_as_PrecomputedChunksSinkDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5DataSinkDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_DziLevelSinkDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  return new MessageParsingError(
    `Could not parse ${JSON.stringify(value)} into PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto`,
  );
}
export function parse_as_ExportJobDto(value: JsonValue): ExportJobDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ExportJobDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ExportJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof MessageParsingError) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof MessageParsingError) return temp_uuid;
  const temp_status = parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
    valueObject.status,
  );
  if (temp_status instanceof MessageParsingError) return temp_status;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof MessageParsingError) return temp_datasink;
  return new ExportJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    datasink: temp_datasink,
  });
}
// Automatically generated via DataTransferObject for ExportJobDto
// Do not edit!
export class ExportJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  public datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
    datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.datasink = _params.datasink;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ExportJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: toJsonValue(this.status),
      datasink: toJsonValue(this.datasink),
    };
  }
  public static fromJsonValue(value: JsonValue): ExportJobDto | MessageParsingError {
    return parse_as_ExportJobDto(value);
  }
}

export function parse_as_OpenDatasinkJobDto(value: JsonValue): OpenDatasinkJobDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "OpenDatasinkJobDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a OpenDatasinkJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof MessageParsingError) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof MessageParsingError) return temp_uuid;
  const temp_status = parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
    valueObject.status,
  );
  if (temp_status instanceof MessageParsingError) return temp_status;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof MessageParsingError) return temp_datasink;
  return new OpenDatasinkJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    datasink: temp_datasink,
  });
}
// Automatically generated via DataTransferObject for OpenDatasinkJobDto
// Do not edit!
export class OpenDatasinkJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  public datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
    datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.datasink = _params.datasink;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "OpenDatasinkJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: toJsonValue(this.status),
      datasink: toJsonValue(this.datasink),
    };
  }
  public static fromJsonValue(value: JsonValue): OpenDatasinkJobDto | MessageParsingError {
    return parse_as_OpenDatasinkJobDto(value);
  }
}

export function parse_as_CreateDziPyramidJobDto(value: JsonValue): CreateDziPyramidJobDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CreateDziPyramidJobDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a CreateDziPyramidJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof MessageParsingError) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof MessageParsingError) return temp_uuid;
  const temp_status = parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
    valueObject.status,
  );
  if (temp_status instanceof MessageParsingError) return temp_status;
  return new CreateDziPyramidJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
  });
}
// Automatically generated via DataTransferObject for CreateDziPyramidJobDto
// Do not edit!
export class CreateDziPyramidJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CreateDziPyramidJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: toJsonValue(this.status),
    };
  }
  public static fromJsonValue(value: JsonValue): CreateDziPyramidJobDto | MessageParsingError {
    return parse_as_CreateDziPyramidJobDto(value);
  }
}

export function parse_as_ZipDirectoryJobDto(value: JsonValue): ZipDirectoryJobDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ZipDirectoryJobDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ZipDirectoryJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof MessageParsingError) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof MessageParsingError) return temp_uuid;
  const temp_status = parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
    valueObject.status,
  );
  if (temp_status instanceof MessageParsingError) return temp_status;
  const temp_output_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.output_fs);
  if (temp_output_fs instanceof MessageParsingError) return temp_output_fs;
  const temp_output_path = parse_as_str(valueObject.output_path);
  if (temp_output_path instanceof MessageParsingError) return temp_output_path;
  return new ZipDirectoryJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    output_fs: temp_output_fs,
    output_path: temp_output_path,
  });
}
// Automatically generated via DataTransferObject for ZipDirectoryJobDto
// Do not edit!
export class ZipDirectoryJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  public output_fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public output_path: string;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
    output_fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    output_path: string;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.output_fs = _params.output_fs;
    this.output_path = _params.output_path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ZipDirectoryJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: toJsonValue(this.status),
      output_fs: toJsonValue(this.output_fs),
      output_path: this.output_path,
    };
  }
  public static fromJsonValue(value: JsonValue): ZipDirectoryJobDto | MessageParsingError {
    return parse_as_ZipDirectoryJobDto(value);
  }
}

export function parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto0None_endof_(
  value: JsonValue,
): PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_PrecomputedChunksSinkDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5DataSinkDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_DziLevelSinkDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_None(value);
  if (!(parsed_option_3 instanceof MessageParsingError)) {
    return parsed_option_3;
  }
  return new MessageParsingError(
    `Could not parse ${
      JSON.stringify(value)
    } into PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto | undefined`,
  );
}
export function parse_as_TransferFileJobDto(value: JsonValue): TransferFileJobDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "TransferFileJobDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a TransferFileJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof MessageParsingError) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof MessageParsingError) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof MessageParsingError) return temp_uuid;
  const temp_status = parse_as_Union_of_JobFinishedDto0JobIsPendingDto0JobIsRunningDto0JobCanceledDto_endof_(
    valueObject.status,
  );
  if (temp_status instanceof MessageParsingError) return temp_status;
  const temp_target_url = parse_as_UrlDto(valueObject.target_url);
  if (temp_target_url instanceof MessageParsingError) return temp_target_url;
  const temp_result_sink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto0None_endof_(
    valueObject.result_sink,
  );
  if (temp_result_sink instanceof MessageParsingError) return temp_result_sink;
  return new TransferFileJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    target_url: temp_target_url,
    result_sink: temp_result_sink,
  });
}
// Automatically generated via DataTransferObject for TransferFileJobDto
// Do not edit!
export class TransferFileJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
  public target_url: UrlDto;
  public result_sink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto | undefined;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: JobFinishedDto | JobIsPendingDto | JobIsRunningDto | JobCanceledDto;
    target_url: UrlDto;
    result_sink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto | undefined;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.target_url = _params.target_url;
    this.result_sink = _params.result_sink;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "TransferFileJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: toJsonValue(this.status),
      target_url: this.target_url.toJsonValue(),
      result_sink: toJsonValue(this.result_sink),
    };
  }
  public static fromJsonValue(value: JsonValue): TransferFileJobDto | MessageParsingError {
    return parse_as_TransferFileJobDto(value);
  }
}

export function parse_as_Union_of_ExportJobDto0OpenDatasinkJobDto0CreateDziPyramidJobDto0ZipDirectoryJobDto0TransferFileJobDto0JobDto_endof_(
  value: JsonValue,
):
  | ExportJobDto
  | OpenDatasinkJobDto
  | CreateDziPyramidJobDto
  | ZipDirectoryJobDto
  | TransferFileJobDto
  | JobDto
  | MessageParsingError {
  const parsed_option_0 = parse_as_ExportJobDto(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_OpenDatasinkJobDto(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_CreateDziPyramidJobDto(value);
  if (!(parsed_option_2 instanceof MessageParsingError)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_ZipDirectoryJobDto(value);
  if (!(parsed_option_3 instanceof MessageParsingError)) {
    return parsed_option_3;
  }
  const parsed_option_4 = parse_as_TransferFileJobDto(value);
  if (!(parsed_option_4 instanceof MessageParsingError)) {
    return parsed_option_4;
  }
  const parsed_option_5 = parse_as_JobDto(value);
  if (!(parsed_option_5 instanceof MessageParsingError)) {
    return parsed_option_5;
  }
  return new MessageParsingError(
    `Could not parse ${
      JSON.stringify(value)
    } into ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipDirectoryJobDto | TransferFileJobDto | JobDto`,
  );
}
export function parse_as_Tuple_of_Union_of_ExportJobDto0OpenDatasinkJobDto0CreateDziPyramidJobDto0ZipDirectoryJobDto0TransferFileJobDto0JobDto_endof_0_varlen__endof_(
  value: JsonValue,
):
  | Array<ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipDirectoryJobDto | TransferFileJobDto | JobDto>
  | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<
    ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipDirectoryJobDto | TransferFileJobDto | JobDto
  > = [];
  for (let item of arr) {
    let parsed_item =
      parse_as_Union_of_ExportJobDto0OpenDatasinkJobDto0CreateDziPyramidJobDto0ZipDirectoryJobDto0TransferFileJobDto0JobDto_endof_(
        item,
      );
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Tuple_of_LabelHeaderDto0_varlen__endof_(
  value: JsonValue,
): Array<LabelHeaderDto> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<LabelHeaderDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_LabelHeaderDto(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Union_of_Tuple_of_LabelHeaderDto0_varlen__endof_0None_endof_(
  value: JsonValue,
): Array<LabelHeaderDto> | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_Tuple_of_LabelHeaderDto0_varlen__endof_(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into Array<LabelHeaderDto> | undefined`);
}
export function parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
  value: JsonValue,
):
  | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
  | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto> =
    [];
  for (let item of arr) {
    let parsed_item =
      parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
        item,
      );
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Union_of_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_0None_endof_(
  value: JsonValue,
):
  | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
  | undefined
  | MessageParsingError {
  const parsed_option_0 =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      value,
    );
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(
    `Could not parse ${
      JSON.stringify(value)
    } into Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto> | undefined`,
  );
}
export function parse_as_PixelClassificationExportAppletStateDto(
  value: JsonValue,
): PixelClassificationExportAppletStateDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PixelClassificationExportAppletStateDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a PixelClassificationExportAppletStateDto`,
    );
  }
  const temp_jobs =
    parse_as_Tuple_of_Union_of_ExportJobDto0OpenDatasinkJobDto0CreateDziPyramidJobDto0ZipDirectoryJobDto0TransferFileJobDto0JobDto_endof_0_varlen__endof_(
      valueObject.jobs,
    );
  if (temp_jobs instanceof MessageParsingError) return temp_jobs;
  const temp_populated_labels = parse_as_Union_of_Tuple_of_LabelHeaderDto0_varlen__endof_0None_endof_(
    valueObject.populated_labels,
  );
  if (temp_populated_labels instanceof MessageParsingError) return temp_populated_labels;
  const temp_datasource_suggestions =
    parse_as_Union_of_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_0None_endof_(
      valueObject.datasource_suggestions,
    );
  if (temp_datasource_suggestions instanceof MessageParsingError) return temp_datasource_suggestions;
  const temp_upstream_ready = parse_as_bool(valueObject.upstream_ready);
  if (temp_upstream_ready instanceof MessageParsingError) return temp_upstream_ready;
  return new PixelClassificationExportAppletStateDto({
    jobs: temp_jobs,
    populated_labels: temp_populated_labels,
    datasource_suggestions: temp_datasource_suggestions,
    upstream_ready: temp_upstream_ready,
  });
}
// Automatically generated via DataTransferObject for PixelClassificationExportAppletStateDto
// Do not edit!
export class PixelClassificationExportAppletStateDto {
  public jobs: Array<
    ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipDirectoryJobDto | TransferFileJobDto | JobDto
  >;
  public populated_labels: Array<LabelHeaderDto> | undefined;
  public datasource_suggestions:
    | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
    | undefined;
  public upstream_ready: boolean;
  constructor(_params: {
    jobs: Array<
      ExportJobDto | OpenDatasinkJobDto | CreateDziPyramidJobDto | ZipDirectoryJobDto | TransferFileJobDto | JobDto
    >;
    populated_labels: Array<LabelHeaderDto> | undefined;
    datasource_suggestions:
      | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
      | undefined;
    upstream_ready: boolean;
  }) {
    this.jobs = _params.jobs;
    this.populated_labels = _params.populated_labels;
    this.datasource_suggestions = _params.datasource_suggestions;
    this.upstream_ready = _params.upstream_ready;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "PixelClassificationExportAppletStateDto",
      jobs: this.jobs.map((item) => toJsonValue(item)),
      populated_labels: toJsonValue(this.populated_labels),
      datasource_suggestions: toJsonValue(this.datasource_suggestions),
      upstream_ready: this.upstream_ready,
    };
  }
  public static fromJsonValue(value: JsonValue): PixelClassificationExportAppletStateDto | MessageParsingError {
    return parse_as_PixelClassificationExportAppletStateDto(value);
  }
}

export function parse_as_float(value: JsonValue): number | MessageParsingError {
  return ensureJsonNumber(value);
}
export function parse_as_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_(
  value: JsonValue,
): "x" | "y" | "z" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "x") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "y") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "z") {
    return tmp_2;
  }
  return new MessageParsingError(`Could not parse ${value} as 'x' | 'y' | 'z'`);
}
export function parse_as_Union_of_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_0None_endof_(
  value: JsonValue,
): "x" | "y" | "z" | undefined | MessageParsingError {
  const parsed_option_0 = parse_as_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_(value);
  if (!(parsed_option_0 instanceof MessageParsingError)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof MessageParsingError)) {
    return parsed_option_1;
  }
  return new MessageParsingError(`Could not parse ${JSON.stringify(value)} into 'x' | 'y' | 'z' | undefined`);
}
export function parse_as_Literal_of__quote_GaussianSmoothing_quote_0_quote_LaplacianofGaussian_quote_0_quote_GaussianGradientMagnitude_quote_0_quote_DifferenceofGaussians_quote_0_quote_StructureTensorEigenvalues_quote_0_quote_HessianofGaussianEigenvalues_quote__endof_(
  value: JsonValue,
):
  | "Gaussian Smoothing"
  | "Laplacian of Gaussian"
  | "Gaussian Gradient Magnitude"
  | "Difference of Gaussians"
  | "Structure Tensor Eigenvalues"
  | "Hessian of Gaussian Eigenvalues"
  | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "Gaussian Smoothing") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "Laplacian of Gaussian") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "Gaussian Gradient Magnitude") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof MessageParsingError) && tmp_3 === "Difference of Gaussians") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof MessageParsingError) && tmp_4 === "Structure Tensor Eigenvalues") {
    return tmp_4;
  }
  const tmp_5 = parse_as_str(value);
  if (!(tmp_5 instanceof MessageParsingError) && tmp_5 === "Hessian of Gaussian Eigenvalues") {
    return tmp_5;
  }
  return new MessageParsingError(
    `Could not parse ${value} as 'Gaussian Smoothing' | 'Laplacian of Gaussian' | 'Gaussian Gradient Magnitude' | 'Difference of Gaussians' | 'Structure Tensor Eigenvalues' | 'Hessian of Gaussian Eigenvalues'`,
  );
}
export function parse_as_IlpFeatureExtractorDto(value: JsonValue): IlpFeatureExtractorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "IlpFeatureExtractorDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a IlpFeatureExtractorDto`);
  }
  const temp_ilp_scale = parse_as_float(valueObject.ilp_scale);
  if (temp_ilp_scale instanceof MessageParsingError) return temp_ilp_scale;
  const temp_axis_2d = parse_as_Union_of_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_0None_endof_(
    valueObject.axis_2d,
  );
  if (temp_axis_2d instanceof MessageParsingError) return temp_axis_2d;
  const temp_class_name =
    parse_as_Literal_of__quote_GaussianSmoothing_quote_0_quote_LaplacianofGaussian_quote_0_quote_GaussianGradientMagnitude_quote_0_quote_DifferenceofGaussians_quote_0_quote_StructureTensorEigenvalues_quote_0_quote_HessianofGaussianEigenvalues_quote__endof_(
      valueObject.class_name,
    );
  if (temp_class_name instanceof MessageParsingError) return temp_class_name;
  return new IlpFeatureExtractorDto({
    ilp_scale: temp_ilp_scale,
    axis_2d: temp_axis_2d,
    class_name: temp_class_name,
  });
}
// Automatically generated via DataTransferObject for IlpFeatureExtractorDto
// Do not edit!
export class IlpFeatureExtractorDto {
  public ilp_scale: number;
  public axis_2d: "x" | "y" | "z" | undefined;
  public class_name:
    | "Gaussian Smoothing"
    | "Laplacian of Gaussian"
    | "Gaussian Gradient Magnitude"
    | "Difference of Gaussians"
    | "Structure Tensor Eigenvalues"
    | "Hessian of Gaussian Eigenvalues";
  constructor(_params: {
    ilp_scale: number;
    axis_2d: "x" | "y" | "z" | undefined;
    class_name:
      | "Gaussian Smoothing"
      | "Laplacian of Gaussian"
      | "Gaussian Gradient Magnitude"
      | "Difference of Gaussians"
      | "Structure Tensor Eigenvalues"
      | "Hessian of Gaussian Eigenvalues";
  }) {
    this.ilp_scale = _params.ilp_scale;
    this.axis_2d = _params.axis_2d;
    this.class_name = _params.class_name;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "IlpFeatureExtractorDto",
      ilp_scale: this.ilp_scale,
      axis_2d: toJsonValue(this.axis_2d),
      class_name: this.class_name,
    };
  }
  public static fromJsonValue(value: JsonValue): IlpFeatureExtractorDto | MessageParsingError {
    return parse_as_IlpFeatureExtractorDto(value);
  }
}

export function parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
  value: JsonValue,
): Array<IlpFeatureExtractorDto> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<IlpFeatureExtractorDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_IlpFeatureExtractorDto(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_FeatureSelectionAppletStateDto(
  value: JsonValue,
): FeatureSelectionAppletStateDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "FeatureSelectionAppletStateDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a FeatureSelectionAppletStateDto`,
    );
  }
  const temp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
    valueObject.feature_extractors,
  );
  if (temp_feature_extractors instanceof MessageParsingError) return temp_feature_extractors;
  return new FeatureSelectionAppletStateDto({
    feature_extractors: temp_feature_extractors,
  });
}
// Automatically generated via DataTransferObject for FeatureSelectionAppletStateDto
// Do not edit!
export class FeatureSelectionAppletStateDto {
  public feature_extractors: Array<IlpFeatureExtractorDto>;
  constructor(_params: {
    feature_extractors: Array<IlpFeatureExtractorDto>;
  }) {
    this.feature_extractors = _params.feature_extractors;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "FeatureSelectionAppletStateDto",
      feature_extractors: this.feature_extractors.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): FeatureSelectionAppletStateDto | MessageParsingError {
    return parse_as_FeatureSelectionAppletStateDto(value);
  }
}

export function parse_as_SetFeatureExtractorsParamsDto(
  value: JsonValue,
): SetFeatureExtractorsParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SetFeatureExtractorsParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a SetFeatureExtractorsParamsDto`,
    );
  }
  const temp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
    valueObject.feature_extractors,
  );
  if (temp_feature_extractors instanceof MessageParsingError) return temp_feature_extractors;
  return new SetFeatureExtractorsParamsDto({
    feature_extractors: temp_feature_extractors,
  });
}
// Automatically generated via DataTransferObject for SetFeatureExtractorsParamsDto
// Do not edit!
export class SetFeatureExtractorsParamsDto {
  public feature_extractors: Array<IlpFeatureExtractorDto>;
  constructor(_params: {
    feature_extractors: Array<IlpFeatureExtractorDto>;
  }) {
    this.feature_extractors = _params.feature_extractors;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "SetFeatureExtractorsParamsDto",
      feature_extractors: this.feature_extractors.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): SetFeatureExtractorsParamsDto | MessageParsingError {
    return parse_as_SetFeatureExtractorsParamsDto(value);
  }
}

export function parse_as_Literal_of__quote_BOOT_FAIL_quote_0_quote_CANCELLED_quote_0_quote_COMPLETED_quote_0_quote_CONFIGURING_quote_0_quote_COMPLETING_quote_0_quote_DEADLINE_quote_0_quote_FAILED_quote_0_quote_NODE_FAIL_quote_0_quote_OUT_OF_MEMORY_quote_0_quote_PENDING_quote_0_quote_PREEMPTED_quote_0_quote_RUNNING_quote_0_quote_RESV_DEL_HOLD_quote_0_quote_REQUEUE_FED_quote_0_quote_REQUEUE_HOLD_quote_0_quote_REQUEUED_quote_0_quote_RESIZING_quote_0_quote_REVOKED_quote_0_quote_SIGNALING_quote_0_quote_SPECIAL_EXIT_quote_0_quote_STAGE_OUT_quote_0_quote_STOPPED_quote_0_quote_SUSPENDED_quote_0_quote_TIMEOUT_quote__endof_(
  value: JsonValue,
):
  | "BOOT_FAIL"
  | "CANCELLED"
  | "COMPLETED"
  | "CONFIGURING"
  | "COMPLETING"
  | "DEADLINE"
  | "FAILED"
  | "NODE_FAIL"
  | "OUT_OF_MEMORY"
  | "PENDING"
  | "PREEMPTED"
  | "RUNNING"
  | "RESV_DEL_HOLD"
  | "REQUEUE_FED"
  | "REQUEUE_HOLD"
  | "REQUEUED"
  | "RESIZING"
  | "REVOKED"
  | "SIGNALING"
  | "SPECIAL_EXIT"
  | "STAGE_OUT"
  | "STOPPED"
  | "SUSPENDED"
  | "TIMEOUT"
  | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "BOOT_FAIL") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "CANCELLED") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "COMPLETED") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof MessageParsingError) && tmp_3 === "CONFIGURING") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof MessageParsingError) && tmp_4 === "COMPLETING") {
    return tmp_4;
  }
  const tmp_5 = parse_as_str(value);
  if (!(tmp_5 instanceof MessageParsingError) && tmp_5 === "DEADLINE") {
    return tmp_5;
  }
  const tmp_6 = parse_as_str(value);
  if (!(tmp_6 instanceof MessageParsingError) && tmp_6 === "FAILED") {
    return tmp_6;
  }
  const tmp_7 = parse_as_str(value);
  if (!(tmp_7 instanceof MessageParsingError) && tmp_7 === "NODE_FAIL") {
    return tmp_7;
  }
  const tmp_8 = parse_as_str(value);
  if (!(tmp_8 instanceof MessageParsingError) && tmp_8 === "OUT_OF_MEMORY") {
    return tmp_8;
  }
  const tmp_9 = parse_as_str(value);
  if (!(tmp_9 instanceof MessageParsingError) && tmp_9 === "PENDING") {
    return tmp_9;
  }
  const tmp_10 = parse_as_str(value);
  if (!(tmp_10 instanceof MessageParsingError) && tmp_10 === "PREEMPTED") {
    return tmp_10;
  }
  const tmp_11 = parse_as_str(value);
  if (!(tmp_11 instanceof MessageParsingError) && tmp_11 === "RUNNING") {
    return tmp_11;
  }
  const tmp_12 = parse_as_str(value);
  if (!(tmp_12 instanceof MessageParsingError) && tmp_12 === "RESV_DEL_HOLD") {
    return tmp_12;
  }
  const tmp_13 = parse_as_str(value);
  if (!(tmp_13 instanceof MessageParsingError) && tmp_13 === "REQUEUE_FED") {
    return tmp_13;
  }
  const tmp_14 = parse_as_str(value);
  if (!(tmp_14 instanceof MessageParsingError) && tmp_14 === "REQUEUE_HOLD") {
    return tmp_14;
  }
  const tmp_15 = parse_as_str(value);
  if (!(tmp_15 instanceof MessageParsingError) && tmp_15 === "REQUEUED") {
    return tmp_15;
  }
  const tmp_16 = parse_as_str(value);
  if (!(tmp_16 instanceof MessageParsingError) && tmp_16 === "RESIZING") {
    return tmp_16;
  }
  const tmp_17 = parse_as_str(value);
  if (!(tmp_17 instanceof MessageParsingError) && tmp_17 === "REVOKED") {
    return tmp_17;
  }
  const tmp_18 = parse_as_str(value);
  if (!(tmp_18 instanceof MessageParsingError) && tmp_18 === "SIGNALING") {
    return tmp_18;
  }
  const tmp_19 = parse_as_str(value);
  if (!(tmp_19 instanceof MessageParsingError) && tmp_19 === "SPECIAL_EXIT") {
    return tmp_19;
  }
  const tmp_20 = parse_as_str(value);
  if (!(tmp_20 instanceof MessageParsingError) && tmp_20 === "STAGE_OUT") {
    return tmp_20;
  }
  const tmp_21 = parse_as_str(value);
  if (!(tmp_21 instanceof MessageParsingError) && tmp_21 === "STOPPED") {
    return tmp_21;
  }
  const tmp_22 = parse_as_str(value);
  if (!(tmp_22 instanceof MessageParsingError) && tmp_22 === "SUSPENDED") {
    return tmp_22;
  }
  const tmp_23 = parse_as_str(value);
  if (!(tmp_23 instanceof MessageParsingError) && tmp_23 === "TIMEOUT") {
    return tmp_23;
  }
  return new MessageParsingError(
    `Could not parse ${value} as 'BOOT_FAIL' | 'CANCELLED' | 'COMPLETED' | 'CONFIGURING' | 'COMPLETING' | 'DEADLINE' | 'FAILED' | 'NODE_FAIL' | 'OUT_OF_MEMORY' | 'PENDING' | 'PREEMPTED' | 'RUNNING' | 'RESV_DEL_HOLD' | 'REQUEUE_FED' | 'REQUEUE_HOLD' | 'REQUEUED' | 'RESIZING' | 'REVOKED' | 'SIGNALING' | 'SPECIAL_EXIT' | 'STAGE_OUT' | 'STOPPED' | 'SUSPENDED' | 'TIMEOUT'`,
  );
}
export function parse_as_ComputeSessionDto(value: JsonValue): ComputeSessionDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ComputeSessionDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ComputeSessionDto`);
  }
  const temp_start_time_utc_sec = parse_as_Union_of_int0None_endof_(valueObject.start_time_utc_sec);
  if (temp_start_time_utc_sec instanceof MessageParsingError) return temp_start_time_utc_sec;
  const temp_time_elapsed_sec = parse_as_int(valueObject.time_elapsed_sec);
  if (temp_time_elapsed_sec instanceof MessageParsingError) return temp_time_elapsed_sec;
  const temp_time_limit_minutes = parse_as_int(valueObject.time_limit_minutes);
  if (temp_time_limit_minutes instanceof MessageParsingError) return temp_time_limit_minutes;
  const temp_num_nodes = parse_as_int(valueObject.num_nodes);
  if (temp_num_nodes instanceof MessageParsingError) return temp_num_nodes;
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof MessageParsingError) return temp_compute_session_id;
  const temp_state =
    parse_as_Literal_of__quote_BOOT_FAIL_quote_0_quote_CANCELLED_quote_0_quote_COMPLETED_quote_0_quote_CONFIGURING_quote_0_quote_COMPLETING_quote_0_quote_DEADLINE_quote_0_quote_FAILED_quote_0_quote_NODE_FAIL_quote_0_quote_OUT_OF_MEMORY_quote_0_quote_PENDING_quote_0_quote_PREEMPTED_quote_0_quote_RUNNING_quote_0_quote_RESV_DEL_HOLD_quote_0_quote_REQUEUE_FED_quote_0_quote_REQUEUE_HOLD_quote_0_quote_REQUEUED_quote_0_quote_RESIZING_quote_0_quote_REVOKED_quote_0_quote_SIGNALING_quote_0_quote_SPECIAL_EXIT_quote_0_quote_STAGE_OUT_quote_0_quote_STOPPED_quote_0_quote_SUSPENDED_quote_0_quote_TIMEOUT_quote__endof_(
      valueObject.state,
    );
  if (temp_state instanceof MessageParsingError) return temp_state;
  return new ComputeSessionDto({
    start_time_utc_sec: temp_start_time_utc_sec,
    time_elapsed_sec: temp_time_elapsed_sec,
    time_limit_minutes: temp_time_limit_minutes,
    num_nodes: temp_num_nodes,
    compute_session_id: temp_compute_session_id,
    state: temp_state,
  });
}
// Automatically generated via DataTransferObject for ComputeSessionDto
// Do not edit!
export class ComputeSessionDto {
  public start_time_utc_sec: number | undefined;
  public time_elapsed_sec: number;
  public time_limit_minutes: number;
  public num_nodes: number;
  public compute_session_id: string;
  public state:
    | "BOOT_FAIL"
    | "CANCELLED"
    | "COMPLETED"
    | "CONFIGURING"
    | "COMPLETING"
    | "DEADLINE"
    | "FAILED"
    | "NODE_FAIL"
    | "OUT_OF_MEMORY"
    | "PENDING"
    | "PREEMPTED"
    | "RUNNING"
    | "RESV_DEL_HOLD"
    | "REQUEUE_FED"
    | "REQUEUE_HOLD"
    | "REQUEUED"
    | "RESIZING"
    | "REVOKED"
    | "SIGNALING"
    | "SPECIAL_EXIT"
    | "STAGE_OUT"
    | "STOPPED"
    | "SUSPENDED"
    | "TIMEOUT";
  constructor(_params: {
    start_time_utc_sec: number | undefined;
    time_elapsed_sec: number;
    time_limit_minutes: number;
    num_nodes: number;
    compute_session_id: string;
    state:
      | "BOOT_FAIL"
      | "CANCELLED"
      | "COMPLETED"
      | "CONFIGURING"
      | "COMPLETING"
      | "DEADLINE"
      | "FAILED"
      | "NODE_FAIL"
      | "OUT_OF_MEMORY"
      | "PENDING"
      | "PREEMPTED"
      | "RUNNING"
      | "RESV_DEL_HOLD"
      | "REQUEUE_FED"
      | "REQUEUE_HOLD"
      | "REQUEUED"
      | "RESIZING"
      | "REVOKED"
      | "SIGNALING"
      | "SPECIAL_EXIT"
      | "STAGE_OUT"
      | "STOPPED"
      | "SUSPENDED"
      | "TIMEOUT";
  }) {
    this.start_time_utc_sec = _params.start_time_utc_sec;
    this.time_elapsed_sec = _params.time_elapsed_sec;
    this.time_limit_minutes = _params.time_limit_minutes;
    this.num_nodes = _params.num_nodes;
    this.compute_session_id = _params.compute_session_id;
    this.state = _params.state;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ComputeSessionDto",
      start_time_utc_sec: toJsonValue(this.start_time_utc_sec),
      time_elapsed_sec: this.time_elapsed_sec,
      time_limit_minutes: this.time_limit_minutes,
      num_nodes: this.num_nodes,
      compute_session_id: this.compute_session_id,
      state: this.state,
    };
  }
  public static fromJsonValue(value: JsonValue): ComputeSessionDto | MessageParsingError {
    return parse_as_ComputeSessionDto(value);
  }
}

export function parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
  value: JsonValue,
): "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "LOCAL_DASK") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof MessageParsingError) && tmp_1 === "LOCAL_PROCESS_POOL") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof MessageParsingError) && tmp_2 === "CSCS") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof MessageParsingError) && tmp_3 === "JUSUF") {
    return tmp_3;
  }
  return new MessageParsingError(`Could not parse ${value} as 'LOCAL_DASK' | 'LOCAL_PROCESS_POOL' | 'CSCS' | 'JUSUF'`);
}
export function parse_as_ComputeSessionStatusDto(value: JsonValue): ComputeSessionStatusDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ComputeSessionStatusDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ComputeSessionStatusDto`);
  }
  const temp_compute_session = parse_as_ComputeSessionDto(valueObject.compute_session);
  if (temp_compute_session instanceof MessageParsingError) return temp_compute_session;
  const temp_hpc_site =
    parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
      valueObject.hpc_site,
    );
  if (temp_hpc_site instanceof MessageParsingError) return temp_hpc_site;
  const temp_session_url = parse_as_UrlDto(valueObject.session_url);
  if (temp_session_url instanceof MessageParsingError) return temp_session_url;
  const temp_connected = parse_as_bool(valueObject.connected);
  if (temp_connected instanceof MessageParsingError) return temp_connected;
  return new ComputeSessionStatusDto({
    compute_session: temp_compute_session,
    hpc_site: temp_hpc_site,
    session_url: temp_session_url,
    connected: temp_connected,
  });
}
// Automatically generated via DataTransferObject for ComputeSessionStatusDto
// Do not edit!
export class ComputeSessionStatusDto {
  public compute_session: ComputeSessionDto;
  public hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  public session_url: UrlDto;
  public connected: boolean;
  constructor(_params: {
    compute_session: ComputeSessionDto;
    hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
    session_url: UrlDto;
    connected: boolean;
  }) {
    this.compute_session = _params.compute_session;
    this.hpc_site = _params.hpc_site;
    this.session_url = _params.session_url;
    this.connected = _params.connected;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ComputeSessionStatusDto",
      compute_session: this.compute_session.toJsonValue(),
      hpc_site: this.hpc_site,
      session_url: this.session_url.toJsonValue(),
      connected: this.connected,
    };
  }
  public static fromJsonValue(value: JsonValue): ComputeSessionStatusDto | MessageParsingError {
    return parse_as_ComputeSessionStatusDto(value);
  }
}

export function parse_as_CreateComputeSessionParamsDto(
  value: JsonValue,
): CreateComputeSessionParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CreateComputeSessionParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a CreateComputeSessionParamsDto`,
    );
  }
  const temp_session_duration_minutes = parse_as_int(valueObject.session_duration_minutes);
  if (temp_session_duration_minutes instanceof MessageParsingError) return temp_session_duration_minutes;
  const temp_hpc_site =
    parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
      valueObject.hpc_site,
    );
  if (temp_hpc_site instanceof MessageParsingError) return temp_hpc_site;
  return new CreateComputeSessionParamsDto({
    session_duration_minutes: temp_session_duration_minutes,
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for CreateComputeSessionParamsDto
// Do not edit!
export class CreateComputeSessionParamsDto {
  public session_duration_minutes: number;
  public hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  constructor(_params: {
    session_duration_minutes: number;
    hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  }) {
    this.session_duration_minutes = _params.session_duration_minutes;
    this.hpc_site = _params.hpc_site;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CreateComputeSessionParamsDto",
      session_duration_minutes: this.session_duration_minutes,
      hpc_site: this.hpc_site,
    };
  }
  public static fromJsonValue(value: JsonValue): CreateComputeSessionParamsDto | MessageParsingError {
    return parse_as_CreateComputeSessionParamsDto(value);
  }
}

export function parse_as_GetComputeSessionStatusParamsDto(
  value: JsonValue,
): GetComputeSessionStatusParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetComputeSessionStatusParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a GetComputeSessionStatusParamsDto`,
    );
  }
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof MessageParsingError) return temp_compute_session_id;
  const temp_hpc_site =
    parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
      valueObject.hpc_site,
    );
  if (temp_hpc_site instanceof MessageParsingError) return temp_hpc_site;
  return new GetComputeSessionStatusParamsDto({
    compute_session_id: temp_compute_session_id,
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for GetComputeSessionStatusParamsDto
// Do not edit!
export class GetComputeSessionStatusParamsDto {
  public compute_session_id: string;
  public hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  constructor(_params: {
    compute_session_id: string;
    hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  }) {
    this.compute_session_id = _params.compute_session_id;
    this.hpc_site = _params.hpc_site;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetComputeSessionStatusParamsDto",
      compute_session_id: this.compute_session_id,
      hpc_site: this.hpc_site,
    };
  }
  public static fromJsonValue(value: JsonValue): GetComputeSessionStatusParamsDto | MessageParsingError {
    return parse_as_GetComputeSessionStatusParamsDto(value);
  }
}

export function parse_as_CloseComputeSessionParamsDto(
  value: JsonValue,
): CloseComputeSessionParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CloseComputeSessionParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a CloseComputeSessionParamsDto`,
    );
  }
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof MessageParsingError) return temp_compute_session_id;
  const temp_hpc_site =
    parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
      valueObject.hpc_site,
    );
  if (temp_hpc_site instanceof MessageParsingError) return temp_hpc_site;
  return new CloseComputeSessionParamsDto({
    compute_session_id: temp_compute_session_id,
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for CloseComputeSessionParamsDto
// Do not edit!
export class CloseComputeSessionParamsDto {
  public compute_session_id: string;
  public hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  constructor(_params: {
    compute_session_id: string;
    hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  }) {
    this.compute_session_id = _params.compute_session_id;
    this.hpc_site = _params.hpc_site;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CloseComputeSessionParamsDto",
      compute_session_id: this.compute_session_id,
      hpc_site: this.hpc_site,
    };
  }
  public static fromJsonValue(value: JsonValue): CloseComputeSessionParamsDto | MessageParsingError {
    return parse_as_CloseComputeSessionParamsDto(value);
  }
}

export function parse_as_CloseComputeSessionResponseDto(
  value: JsonValue,
): CloseComputeSessionResponseDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CloseComputeSessionResponseDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a CloseComputeSessionResponseDto`,
    );
  }
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof MessageParsingError) return temp_compute_session_id;
  return new CloseComputeSessionResponseDto({
    compute_session_id: temp_compute_session_id,
  });
}
// Automatically generated via DataTransferObject for CloseComputeSessionResponseDto
// Do not edit!
export class CloseComputeSessionResponseDto {
  public compute_session_id: string;
  constructor(_params: {
    compute_session_id: string;
  }) {
    this.compute_session_id = _params.compute_session_id;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CloseComputeSessionResponseDto",
      compute_session_id: this.compute_session_id,
    };
  }
  public static fromJsonValue(value: JsonValue): CloseComputeSessionResponseDto | MessageParsingError {
    return parse_as_CloseComputeSessionResponseDto(value);
  }
}

export function parse_as_ListComputeSessionsParamsDto(
  value: JsonValue,
): ListComputeSessionsParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListComputeSessionsParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a ListComputeSessionsParamsDto`,
    );
  }
  const temp_hpc_site =
    parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
      valueObject.hpc_site,
    );
  if (temp_hpc_site instanceof MessageParsingError) return temp_hpc_site;
  return new ListComputeSessionsParamsDto({
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for ListComputeSessionsParamsDto
// Do not edit!
export class ListComputeSessionsParamsDto {
  public hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  constructor(_params: {
    hpc_site: "LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF";
  }) {
    this.hpc_site = _params.hpc_site;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ListComputeSessionsParamsDto",
      hpc_site: this.hpc_site,
    };
  }
  public static fromJsonValue(value: JsonValue): ListComputeSessionsParamsDto | MessageParsingError {
    return parse_as_ListComputeSessionsParamsDto(value);
  }
}

export function parse_as_Tuple_of_ComputeSessionStatusDto0_varlen__endof_(
  value: JsonValue,
): Array<ComputeSessionStatusDto> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<ComputeSessionStatusDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_ComputeSessionStatusDto(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_ListComputeSessionsResponseDto(
  value: JsonValue,
): ListComputeSessionsResponseDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListComputeSessionsResponseDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a ListComputeSessionsResponseDto`,
    );
  }
  const temp_compute_sessions_stati = parse_as_Tuple_of_ComputeSessionStatusDto0_varlen__endof_(
    valueObject.compute_sessions_stati,
  );
  if (temp_compute_sessions_stati instanceof MessageParsingError) return temp_compute_sessions_stati;
  return new ListComputeSessionsResponseDto({
    compute_sessions_stati: temp_compute_sessions_stati,
  });
}
// Automatically generated via DataTransferObject for ListComputeSessionsResponseDto
// Do not edit!
export class ListComputeSessionsResponseDto {
  public compute_sessions_stati: Array<ComputeSessionStatusDto>;
  constructor(_params: {
    compute_sessions_stati: Array<ComputeSessionStatusDto>;
  }) {
    this.compute_sessions_stati = _params.compute_sessions_stati;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ListComputeSessionsResponseDto",
      compute_sessions_stati: this.compute_sessions_stati.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): ListComputeSessionsResponseDto | MessageParsingError {
    return parse_as_ListComputeSessionsResponseDto(value);
  }
}

export function parse_as_Tuple_of_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_0_varlen__endof_(
  value: JsonValue,
): Array<"LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF"> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<"LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF"> = [];
  for (let item of arr) {
    let parsed_item =
      parse_as_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
        item,
      );
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_GetAvailableHpcSitesResponseDto(
  value: JsonValue,
): GetAvailableHpcSitesResponseDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetAvailableHpcSitesResponseDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a GetAvailableHpcSitesResponseDto`,
    );
  }
  const temp_available_sites =
    parse_as_Tuple_of_Literal_of__quote_LOCAL_DASK_quote_0_quote_LOCAL_PROCESS_POOL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_0_varlen__endof_(
      valueObject.available_sites,
    );
  if (temp_available_sites instanceof MessageParsingError) return temp_available_sites;
  return new GetAvailableHpcSitesResponseDto({
    available_sites: temp_available_sites,
  });
}
// Automatically generated via DataTransferObject for GetAvailableHpcSitesResponseDto
// Do not edit!
export class GetAvailableHpcSitesResponseDto {
  public available_sites: Array<"LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF">;
  constructor(_params: {
    available_sites: Array<"LOCAL_DASK" | "LOCAL_PROCESS_POOL" | "CSCS" | "JUSUF">;
  }) {
    this.available_sites = _params.available_sites;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetAvailableHpcSitesResponseDto",
      available_sites: this.available_sites.map((item) => item),
    };
  }
  public static fromJsonValue(value: JsonValue): GetAvailableHpcSitesResponseDto | MessageParsingError {
    return parse_as_GetAvailableHpcSitesResponseDto(value);
  }
}

export function parse_as_CheckLoginResultDto(value: JsonValue): CheckLoginResultDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CheckLoginResultDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a CheckLoginResultDto`);
  }
  const temp_logged_in = parse_as_bool(valueObject.logged_in);
  if (temp_logged_in instanceof MessageParsingError) return temp_logged_in;
  return new CheckLoginResultDto({
    logged_in: temp_logged_in,
  });
}
// Automatically generated via DataTransferObject for CheckLoginResultDto
// Do not edit!
export class CheckLoginResultDto {
  public logged_in: boolean;
  constructor(_params: {
    logged_in: boolean;
  }) {
    this.logged_in = _params.logged_in;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CheckLoginResultDto",
      logged_in: this.logged_in,
    };
  }
  public static fromJsonValue(value: JsonValue): CheckLoginResultDto | MessageParsingError {
    return parse_as_CheckLoginResultDto(value);
  }
}

export function parse_as_StartPixelProbabilitiesExportJobParamsDto(
  value: JsonValue,
): StartPixelProbabilitiesExportJobParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "StartPixelProbabilitiesExportJobParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a StartPixelProbabilitiesExportJobParamsDto`,
    );
  }
  const temp_datasource =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.datasource,
    );
  if (temp_datasource instanceof MessageParsingError) return temp_datasource;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof MessageParsingError) return temp_datasink;
  return new StartPixelProbabilitiesExportJobParamsDto({
    datasource: temp_datasource,
    datasink: temp_datasink,
  });
}
// Automatically generated via DataTransferObject for StartPixelProbabilitiesExportJobParamsDto
// Do not edit!
export class StartPixelProbabilitiesExportJobParamsDto {
  public datasource: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
  public datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  constructor(_params: {
    datasource: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
    datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  }) {
    this.datasource = _params.datasource;
    this.datasink = _params.datasink;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "StartPixelProbabilitiesExportJobParamsDto",
      datasource: toJsonValue(this.datasource),
      datasink: toJsonValue(this.datasink),
    };
  }
  public static fromJsonValue(value: JsonValue): StartPixelProbabilitiesExportJobParamsDto | MessageParsingError {
    return parse_as_StartPixelProbabilitiesExportJobParamsDto(value);
  }
}

export function parse_as_StartSimpleSegmentationExportJobParamsDto(
  value: JsonValue,
): StartSimpleSegmentationExportJobParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "StartSimpleSegmentationExportJobParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a StartSimpleSegmentationExportJobParamsDto`,
    );
  }
  const temp_datasource =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.datasource,
    );
  if (temp_datasource instanceof MessageParsingError) return temp_datasource;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof MessageParsingError) return temp_datasink;
  const temp_label_header = parse_as_LabelHeaderDto(valueObject.label_header);
  if (temp_label_header instanceof MessageParsingError) return temp_label_header;
  return new StartSimpleSegmentationExportJobParamsDto({
    datasource: temp_datasource,
    datasink: temp_datasink,
    label_header: temp_label_header,
  });
}
// Automatically generated via DataTransferObject for StartSimpleSegmentationExportJobParamsDto
// Do not edit!
export class StartSimpleSegmentationExportJobParamsDto {
  public datasource: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
  public datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  public label_header: LabelHeaderDto;
  constructor(_params: {
    datasource: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
    datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
    label_header: LabelHeaderDto;
  }) {
    this.datasource = _params.datasource;
    this.datasink = _params.datasink;
    this.label_header = _params.label_header;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "StartSimpleSegmentationExportJobParamsDto",
      datasource: toJsonValue(this.datasource),
      datasink: toJsonValue(this.datasink),
      label_header: this.label_header.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): StartSimpleSegmentationExportJobParamsDto | MessageParsingError {
    return parse_as_StartSimpleSegmentationExportJobParamsDto(value);
  }
}

export function parse_as_LoadProjectParamsDto(value: JsonValue): LoadProjectParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LoadProjectParamsDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a LoadProjectParamsDto`);
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.fs);
  if (temp_fs instanceof MessageParsingError) return temp_fs;
  const temp_project_file_path = parse_as_str(valueObject.project_file_path);
  if (temp_project_file_path instanceof MessageParsingError) return temp_project_file_path;
  return new LoadProjectParamsDto({
    fs: temp_fs,
    project_file_path: temp_project_file_path,
  });
}
// Automatically generated via DataTransferObject for LoadProjectParamsDto
// Do not edit!
export class LoadProjectParamsDto {
  public fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public project_file_path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    project_file_path: string;
  }) {
    this.fs = _params.fs;
    this.project_file_path = _params.project_file_path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "LoadProjectParamsDto",
      fs: toJsonValue(this.fs),
      project_file_path: this.project_file_path,
    };
  }
  public static fromJsonValue(value: JsonValue): LoadProjectParamsDto | MessageParsingError {
    return parse_as_LoadProjectParamsDto(value);
  }
}

export function parse_as_SaveProjectParamsDto(value: JsonValue): SaveProjectParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SaveProjectParamsDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a SaveProjectParamsDto`);
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.fs);
  if (temp_fs instanceof MessageParsingError) return temp_fs;
  const temp_project_file_path = parse_as_str(valueObject.project_file_path);
  if (temp_project_file_path instanceof MessageParsingError) return temp_project_file_path;
  return new SaveProjectParamsDto({
    fs: temp_fs,
    project_file_path: temp_project_file_path,
  });
}
// Automatically generated via DataTransferObject for SaveProjectParamsDto
// Do not edit!
export class SaveProjectParamsDto {
  public fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public project_file_path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    project_file_path: string;
  }) {
    this.fs = _params.fs;
    this.project_file_path = _params.project_file_path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "SaveProjectParamsDto",
      fs: toJsonValue(this.fs),
      project_file_path: this.project_file_path,
    };
  }
  public static fromJsonValue(value: JsonValue): SaveProjectParamsDto | MessageParsingError {
    return parse_as_SaveProjectParamsDto(value);
  }
}

export function parse_as_GetDatasourcesFromUrlParamsDto(
  value: JsonValue,
): GetDatasourcesFromUrlParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetDatasourcesFromUrlParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a GetDatasourcesFromUrlParamsDto`,
    );
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof MessageParsingError) return temp_url;
  return new GetDatasourcesFromUrlParamsDto({
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for GetDatasourcesFromUrlParamsDto
// Do not edit!
export class GetDatasourcesFromUrlParamsDto {
  public url: UrlDto;
  constructor(_params: {
    url: UrlDto;
  }) {
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetDatasourcesFromUrlParamsDto",
      url: this.url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): GetDatasourcesFromUrlParamsDto | MessageParsingError {
    return parse_as_GetDatasourcesFromUrlParamsDto(value);
  }
}

export function parse_as_GetDatasourcesFromUrlResponseDto(
  value: JsonValue,
): GetDatasourcesFromUrlResponseDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetDatasourcesFromUrlResponseDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a GetDatasourcesFromUrlResponseDto`,
    );
  }
  const temp_datasources =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      valueObject.datasources,
    );
  if (temp_datasources instanceof MessageParsingError) return temp_datasources;
  return new GetDatasourcesFromUrlResponseDto({
    datasources: temp_datasources,
  });
}
// Automatically generated via DataTransferObject for GetDatasourcesFromUrlResponseDto
// Do not edit!
export class GetDatasourcesFromUrlResponseDto {
  public datasources: Array<
    PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto
  >;
  constructor(_params: {
    datasources: Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>;
  }) {
    this.datasources = _params.datasources;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetDatasourcesFromUrlResponseDto",
      datasources: this.datasources.map((item) => toJsonValue(item)),
    };
  }
  public static fromJsonValue(value: JsonValue): GetDatasourcesFromUrlResponseDto | MessageParsingError {
    return parse_as_GetDatasourcesFromUrlResponseDto(value);
  }
}

export function parse_as_GetFileSystemAndPathFromUrlParamsDto(
  value: JsonValue,
): GetFileSystemAndPathFromUrlParamsDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetFileSystemAndPathFromUrlParamsDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a GetFileSystemAndPathFromUrlParamsDto`,
    );
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof MessageParsingError) return temp_url;
  return new GetFileSystemAndPathFromUrlParamsDto({
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for GetFileSystemAndPathFromUrlParamsDto
// Do not edit!
export class GetFileSystemAndPathFromUrlParamsDto {
  public url: UrlDto;
  constructor(_params: {
    url: UrlDto;
  }) {
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetFileSystemAndPathFromUrlParamsDto",
      url: this.url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): GetFileSystemAndPathFromUrlParamsDto | MessageParsingError {
    return parse_as_GetFileSystemAndPathFromUrlParamsDto(value);
  }
}

export function parse_as_GetFileSystemAndPathFromUrlResponseDto(
  value: JsonValue,
): GetFileSystemAndPathFromUrlResponseDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetFileSystemAndPathFromUrlResponseDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a GetFileSystemAndPathFromUrlResponseDto`,
    );
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.fs);
  if (temp_fs instanceof MessageParsingError) return temp_fs;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  return new GetFileSystemAndPathFromUrlResponseDto({
    fs: temp_fs,
    path: temp_path,
  });
}
// Automatically generated via DataTransferObject for GetFileSystemAndPathFromUrlResponseDto
// Do not edit!
export class GetFileSystemAndPathFromUrlResponseDto {
  public fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    path: string;
  }) {
    this.fs = _params.fs;
    this.path = _params.path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetFileSystemAndPathFromUrlResponseDto",
      fs: toJsonValue(this.fs),
      path: this.path,
    };
  }
  public static fromJsonValue(value: JsonValue): GetFileSystemAndPathFromUrlResponseDto | MessageParsingError {
    return parse_as_GetFileSystemAndPathFromUrlResponseDto(value);
  }
}

export function parse_as_CheckDatasourceCompatibilityParams(
  value: JsonValue,
): CheckDatasourceCompatibilityParams | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CheckDatasourceCompatibilityParams") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a CheckDatasourceCompatibilityParams`,
    );
  }
  const temp_datasources =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      valueObject.datasources,
    );
  if (temp_datasources instanceof MessageParsingError) return temp_datasources;
  return new CheckDatasourceCompatibilityParams({
    datasources: temp_datasources,
  });
}
// Automatically generated via DataTransferObject for CheckDatasourceCompatibilityParams
// Do not edit!
export class CheckDatasourceCompatibilityParams {
  public datasources: Array<
    PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto
  >;
  constructor(_params: {
    datasources: Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>;
  }) {
    this.datasources = _params.datasources;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CheckDatasourceCompatibilityParams",
      datasources: this.datasources.map((item) => toJsonValue(item)),
    };
  }
  public static fromJsonValue(value: JsonValue): CheckDatasourceCompatibilityParams | MessageParsingError {
    return parse_as_CheckDatasourceCompatibilityParams(value);
  }
}

export function parse_as_Tuple_of_bool0_varlen__endof_(value: JsonValue): Array<boolean> | MessageParsingError {
  const arr = ensureJsonArray(value);
  if (arr instanceof MessageParsingError) return arr;
  const out: Array<boolean> = [];
  for (let item of arr) {
    let parsed_item = parse_as_bool(item);
    if (parsed_item instanceof MessageParsingError) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_CheckDatasourceCompatibilityResponse(
  value: JsonValue,
): CheckDatasourceCompatibilityResponse | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CheckDatasourceCompatibilityResponse") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a CheckDatasourceCompatibilityResponse`,
    );
  }
  const temp_compatible = parse_as_Tuple_of_bool0_varlen__endof_(valueObject.compatible);
  if (temp_compatible instanceof MessageParsingError) return temp_compatible;
  return new CheckDatasourceCompatibilityResponse({
    compatible: temp_compatible,
  });
}
// Automatically generated via DataTransferObject for CheckDatasourceCompatibilityResponse
// Do not edit!
export class CheckDatasourceCompatibilityResponse {
  public compatible: Array<boolean>;
  constructor(_params: {
    compatible: Array<boolean>;
  }) {
    this.compatible = _params.compatible;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "CheckDatasourceCompatibilityResponse",
      compatible: this.compatible.map((item) => item),
    };
  }
  public static fromJsonValue(value: JsonValue): CheckDatasourceCompatibilityResponse | MessageParsingError {
    return parse_as_CheckDatasourceCompatibilityResponse(value);
  }
}

export function parse_as_ListFsDirRequest(value: JsonValue): ListFsDirRequest | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListFsDirRequest") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ListFsDirRequest`);
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto0ZipFsDto_endof_(valueObject.fs);
  if (temp_fs instanceof MessageParsingError) return temp_fs;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof MessageParsingError) return temp_path;
  return new ListFsDirRequest({
    fs: temp_fs,
    path: temp_path,
  });
}
// Automatically generated via DataTransferObject for ListFsDirRequest
// Do not edit!
export class ListFsDirRequest {
  public fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
  public path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto | ZipFsDto;
    path: string;
  }) {
    this.fs = _params.fs;
    this.path = _params.path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ListFsDirRequest",
      fs: toJsonValue(this.fs),
      path: this.path,
    };
  }
  public static fromJsonValue(value: JsonValue): ListFsDirRequest | MessageParsingError {
    return parse_as_ListFsDirRequest(value);
  }
}

export function parse_as_ListFsDirResponse(value: JsonValue): ListFsDirResponse | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListFsDirResponse") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a ListFsDirResponse`);
  }
  const temp_files = parse_as_Tuple_of_str0_varlen__endof_(valueObject.files);
  if (temp_files instanceof MessageParsingError) return temp_files;
  const temp_directories = parse_as_Tuple_of_str0_varlen__endof_(valueObject.directories);
  if (temp_directories instanceof MessageParsingError) return temp_directories;
  return new ListFsDirResponse({
    files: temp_files,
    directories: temp_directories,
  });
}
// Automatically generated via DataTransferObject for ListFsDirResponse
// Do not edit!
export class ListFsDirResponse {
  public files: Array<string>;
  public directories: Array<string>;
  constructor(_params: {
    files: Array<string>;
    directories: Array<string>;
  }) {
    this.files = _params.files;
    this.directories = _params.directories;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ListFsDirResponse",
      files: this.files.map((item) => item),
      directories: this.directories.map((item) => item),
    };
  }
  public static fromJsonValue(value: JsonValue): ListFsDirResponse | MessageParsingError {
    return parse_as_ListFsDirResponse(value);
  }
}

export function parse_as_Literal_of__quote_hbp_quote__endof_(value: JsonValue): "hbp" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "hbp") {
    return tmp_0;
  }
  return new MessageParsingError(`Could not parse ${value} as 'hbp'`);
}
export function parse_as_HbpIamPublicKeyDto(value: JsonValue): HbpIamPublicKeyDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  const temp_realm = parse_as_Literal_of__quote_hbp_quote__endof_(valueObject.realm);
  if (temp_realm instanceof MessageParsingError) return temp_realm;
  const temp_public_key = parse_as_str(valueObject.public_key);
  if (temp_public_key instanceof MessageParsingError) return temp_public_key;
  return new HbpIamPublicKeyDto({
    realm: temp_realm,
    public_key: temp_public_key,
  });
}
// Automatically generated via DataTransferObject for HbpIamPublicKeyDto
// Do not edit!
export class HbpIamPublicKeyDto {
  public realm: "hbp";
  public public_key: string;
  constructor(_params: {
    realm: "hbp";
    public_key: string;
  }) {
    this.realm = _params.realm;
    this.public_key = _params.public_key;
  }
  public toJsonValue(): JsonObject {
    return {
      realm: this.realm,
      public_key: this.public_key,
    };
  }
  public static fromJsonValue(value: JsonValue): HbpIamPublicKeyDto | MessageParsingError {
    return parse_as_HbpIamPublicKeyDto(value);
  }
}

export function parse_as_Literal_of__quote_RS256_quote__endof_(value: JsonValue): "RS256" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "RS256") {
    return tmp_0;
  }
  return new MessageParsingError(`Could not parse ${value} as 'RS256'`);
}
export function parse_as_Literal_of__quote_JWT_quote__endof_(value: JsonValue): "JWT" | MessageParsingError {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof MessageParsingError) && tmp_0 === "JWT") {
    return tmp_0;
  }
  return new MessageParsingError(`Could not parse ${value} as 'JWT'`);
}
export function parse_as_EbrainsAccessTokenHeaderDto(
  value: JsonValue,
): EbrainsAccessTokenHeaderDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  const temp_alg = parse_as_Literal_of__quote_RS256_quote__endof_(valueObject.alg);
  if (temp_alg instanceof MessageParsingError) return temp_alg;
  const temp_typ = parse_as_Literal_of__quote_JWT_quote__endof_(valueObject.typ);
  if (temp_typ instanceof MessageParsingError) return temp_typ;
  const temp_kid = parse_as_str(valueObject.kid);
  if (temp_kid instanceof MessageParsingError) return temp_kid;
  return new EbrainsAccessTokenHeaderDto({
    alg: temp_alg,
    typ: temp_typ,
    kid: temp_kid,
  });
}
// Automatically generated via DataTransferObject for EbrainsAccessTokenHeaderDto
// Do not edit!
export class EbrainsAccessTokenHeaderDto {
  public alg: "RS256";
  public typ: "JWT";
  public kid: string;
  constructor(_params: {
    alg: "RS256";
    typ: "JWT";
    kid: string;
  }) {
    this.alg = _params.alg;
    this.typ = _params.typ;
    this.kid = _params.kid;
  }
  public toJsonValue(): JsonObject {
    return {
      alg: this.alg,
      typ: this.typ,
      kid: this.kid,
    };
  }
  public static fromJsonValue(value: JsonValue): EbrainsAccessTokenHeaderDto | MessageParsingError {
    return parse_as_EbrainsAccessTokenHeaderDto(value);
  }
}

export function parse_as_EbrainsAccessTokenPayloadDto(
  value: JsonValue,
): EbrainsAccessTokenPayloadDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  const temp_exp = parse_as_int(valueObject.exp);
  if (temp_exp instanceof MessageParsingError) return temp_exp;
  const temp_auth_time = parse_as_int(valueObject.auth_time);
  if (temp_auth_time instanceof MessageParsingError) return temp_auth_time;
  const temp_sub = parse_as_str(valueObject.sub);
  if (temp_sub instanceof MessageParsingError) return temp_sub;
  return new EbrainsAccessTokenPayloadDto({
    exp: temp_exp,
    auth_time: temp_auth_time,
    sub: temp_sub,
  });
}
// Automatically generated via DataTransferObject for EbrainsAccessTokenPayloadDto
// Do not edit!
export class EbrainsAccessTokenPayloadDto {
  public exp: number;
  public auth_time: number;
  public sub: string;
  constructor(_params: {
    exp: number;
    auth_time: number;
    sub: string;
  }) {
    this.exp = _params.exp;
    this.auth_time = _params.auth_time;
    this.sub = _params.sub;
  }
  public toJsonValue(): JsonObject {
    return {
      exp: this.exp,
      auth_time: this.auth_time,
      sub: this.sub,
    };
  }
  public static fromJsonValue(value: JsonValue): EbrainsAccessTokenPayloadDto | MessageParsingError {
    return parse_as_EbrainsAccessTokenPayloadDto(value);
  }
}

export function parse_as_EbrainsAccessTokenDto(value: JsonValue): EbrainsAccessTokenDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  const temp_access_token = parse_as_str(valueObject.access_token);
  if (temp_access_token instanceof MessageParsingError) return temp_access_token;
  const temp_refresh_token = parse_as_str(valueObject.refresh_token);
  if (temp_refresh_token instanceof MessageParsingError) return temp_refresh_token;
  return new EbrainsAccessTokenDto({
    access_token: temp_access_token,
    refresh_token: temp_refresh_token,
  });
}
// Automatically generated via DataTransferObject for EbrainsAccessTokenDto
// Do not edit!
export class EbrainsAccessTokenDto {
  public access_token: string;
  public refresh_token: string;
  constructor(_params: {
    access_token: string;
    refresh_token: string;
  }) {
    this.access_token = _params.access_token;
    this.refresh_token = _params.refresh_token;
  }
  public toJsonValue(): JsonObject {
    return {
      access_token: this.access_token,
      refresh_token: this.refresh_token,
    };
  }
  public static fromJsonValue(value: JsonValue): EbrainsAccessTokenDto | MessageParsingError {
    return parse_as_EbrainsAccessTokenDto(value);
  }
}

export function parse_as_DataProxyObjectUrlResponse(
  value: JsonValue,
): DataProxyObjectUrlResponse | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  const temp_url = parse_as_str(valueObject.url);
  if (temp_url instanceof MessageParsingError) return temp_url;
  return new DataProxyObjectUrlResponse({
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for DataProxyObjectUrlResponse
// Do not edit!
export class DataProxyObjectUrlResponse {
  public url: string;
  constructor(_params: {
    url: string;
  }) {
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      url: this.url,
    };
  }
  public static fromJsonValue(value: JsonValue): DataProxyObjectUrlResponse | MessageParsingError {
    return parse_as_DataProxyObjectUrlResponse(value);
  }
}

export function parse_as_LoginRequiredErrorDto(value: JsonValue): LoginRequiredErrorDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LoginRequiredErrorDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a LoginRequiredErrorDto`);
  }
  return new LoginRequiredErrorDto({});
}
// Automatically generated via DataTransferObject for LoginRequiredErrorDto
// Do not edit!
export class LoginRequiredErrorDto {
  constructor(_params: {}) {
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "LoginRequiredErrorDto",
    };
  }
  public static fromJsonValue(value: JsonValue): LoginRequiredErrorDto | MessageParsingError {
    return parse_as_LoginRequiredErrorDto(value);
  }
}

export function parse_as_EbrainsOidcClientDto(value: JsonValue): EbrainsOidcClientDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "EbrainsOidcClientDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a EbrainsOidcClientDto`);
  }
  const temp_client_id = parse_as_str(valueObject.client_id);
  if (temp_client_id instanceof MessageParsingError) return temp_client_id;
  const temp_client_secret = parse_as_str(valueObject.client_secret);
  if (temp_client_secret instanceof MessageParsingError) return temp_client_secret;
  return new EbrainsOidcClientDto({
    client_id: temp_client_id,
    client_secret: temp_client_secret,
  });
}
// Automatically generated via DataTransferObject for EbrainsOidcClientDto
// Do not edit!
export class EbrainsOidcClientDto {
  public client_id: string;
  public client_secret: string;
  constructor(_params: {
    client_id: string;
    client_secret: string;
  }) {
    this.client_id = _params.client_id;
    this.client_secret = _params.client_secret;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "EbrainsOidcClientDto",
      client_id: this.client_id,
      client_secret: this.client_secret,
    };
  }
  public static fromJsonValue(value: JsonValue): EbrainsOidcClientDto | MessageParsingError {
    return parse_as_EbrainsOidcClientDto(value);
  }
}

export function parse_as_SessionAllocatorServerConfigDto(
  value: JsonValue,
): SessionAllocatorServerConfigDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SessionAllocatorServerConfigDto") {
    return new MessageParsingError(
      `Could not deserialize ${JSON.stringify(valueObject)} as a SessionAllocatorServerConfigDto`,
    );
  }
  const temp_ebrains_oidc_client = parse_as_EbrainsOidcClientDto(valueObject.ebrains_oidc_client);
  if (temp_ebrains_oidc_client instanceof MessageParsingError) return temp_ebrains_oidc_client;
  const temp_allow_local_compute_sessions = parse_as_bool(valueObject.allow_local_compute_sessions);
  if (temp_allow_local_compute_sessions instanceof MessageParsingError) return temp_allow_local_compute_sessions;
  const temp_b64_fernet_key = parse_as_str(valueObject.b64_fernet_key);
  if (temp_b64_fernet_key instanceof MessageParsingError) return temp_b64_fernet_key;
  const temp_external_url = parse_as_UrlDto(valueObject.external_url);
  if (temp_external_url instanceof MessageParsingError) return temp_external_url;
  return new SessionAllocatorServerConfigDto({
    ebrains_oidc_client: temp_ebrains_oidc_client,
    allow_local_compute_sessions: temp_allow_local_compute_sessions,
    b64_fernet_key: temp_b64_fernet_key,
    external_url: temp_external_url,
  });
}
// Automatically generated via DataTransferObject for SessionAllocatorServerConfigDto
// Do not edit!
export class SessionAllocatorServerConfigDto {
  public ebrains_oidc_client: EbrainsOidcClientDto;
  public allow_local_compute_sessions: boolean;
  public b64_fernet_key: string;
  public external_url: UrlDto;
  constructor(_params: {
    ebrains_oidc_client: EbrainsOidcClientDto;
    allow_local_compute_sessions: boolean;
    b64_fernet_key: string;
    external_url: UrlDto;
  }) {
    this.ebrains_oidc_client = _params.ebrains_oidc_client;
    this.allow_local_compute_sessions = _params.allow_local_compute_sessions;
    this.b64_fernet_key = _params.b64_fernet_key;
    this.external_url = _params.external_url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "SessionAllocatorServerConfigDto",
      ebrains_oidc_client: this.ebrains_oidc_client.toJsonValue(),
      allow_local_compute_sessions: this.allow_local_compute_sessions,
      b64_fernet_key: this.b64_fernet_key,
      external_url: this.external_url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): SessionAllocatorServerConfigDto | MessageParsingError {
    return parse_as_SessionAllocatorServerConfigDto(value);
  }
}

export function parse_as_WorkflowConfigDto(value: JsonValue): WorkflowConfigDto | MessageParsingError {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof MessageParsingError) {
    return valueObject;
  }
  if (valueObject["__class__"] != "WorkflowConfigDto") {
    return new MessageParsingError(`Could not deserialize ${JSON.stringify(valueObject)} as a WorkflowConfigDto`);
  }
  const temp_allow_local_fs = parse_as_bool(valueObject.allow_local_fs);
  if (temp_allow_local_fs instanceof MessageParsingError) return temp_allow_local_fs;
  const temp_scratch_dir = parse_as_str(valueObject.scratch_dir);
  if (temp_scratch_dir instanceof MessageParsingError) return temp_scratch_dir;
  const temp_ebrains_user_token = parse_as_EbrainsAccessTokenDto(valueObject.ebrains_user_token);
  if (temp_ebrains_user_token instanceof MessageParsingError) return temp_ebrains_user_token;
  const temp_max_duration_minutes = parse_as_int(valueObject.max_duration_minutes);
  if (temp_max_duration_minutes instanceof MessageParsingError) return temp_max_duration_minutes;
  const temp_listen_socket = parse_as_str(valueObject.listen_socket);
  if (temp_listen_socket instanceof MessageParsingError) return temp_listen_socket;
  const temp_session_url = parse_as_UrlDto(valueObject.session_url);
  if (temp_session_url instanceof MessageParsingError) return temp_session_url;
  const temp_session_allocator_host = parse_as_str(valueObject.session_allocator_host);
  if (temp_session_allocator_host instanceof MessageParsingError) return temp_session_allocator_host;
  const temp_session_allocator_username = parse_as_str(valueObject.session_allocator_username);
  if (temp_session_allocator_username instanceof MessageParsingError) return temp_session_allocator_username;
  const temp_session_allocator_socket_path = parse_as_str(valueObject.session_allocator_socket_path);
  if (temp_session_allocator_socket_path instanceof MessageParsingError) return temp_session_allocator_socket_path;
  return new WorkflowConfigDto({
    allow_local_fs: temp_allow_local_fs,
    scratch_dir: temp_scratch_dir,
    ebrains_user_token: temp_ebrains_user_token,
    max_duration_minutes: temp_max_duration_minutes,
    listen_socket: temp_listen_socket,
    session_url: temp_session_url,
    session_allocator_host: temp_session_allocator_host,
    session_allocator_username: temp_session_allocator_username,
    session_allocator_socket_path: temp_session_allocator_socket_path,
  });
}
// Automatically generated via DataTransferObject for WorkflowConfigDto
// Do not edit!
export class WorkflowConfigDto {
  public allow_local_fs: boolean;
  public scratch_dir: string;
  public ebrains_user_token: EbrainsAccessTokenDto;
  public max_duration_minutes: number;
  public listen_socket: string;
  public session_url: UrlDto;
  public session_allocator_host: string;
  public session_allocator_username: string;
  public session_allocator_socket_path: string;
  constructor(_params: {
    allow_local_fs: boolean;
    scratch_dir: string;
    ebrains_user_token: EbrainsAccessTokenDto;
    max_duration_minutes: number;
    listen_socket: string;
    session_url: UrlDto;
    session_allocator_host: string;
    session_allocator_username: string;
    session_allocator_socket_path: string;
  }) {
    this.allow_local_fs = _params.allow_local_fs;
    this.scratch_dir = _params.scratch_dir;
    this.ebrains_user_token = _params.ebrains_user_token;
    this.max_duration_minutes = _params.max_duration_minutes;
    this.listen_socket = _params.listen_socket;
    this.session_url = _params.session_url;
    this.session_allocator_host = _params.session_allocator_host;
    this.session_allocator_username = _params.session_allocator_username;
    this.session_allocator_socket_path = _params.session_allocator_socket_path;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "WorkflowConfigDto",
      allow_local_fs: this.allow_local_fs,
      scratch_dir: this.scratch_dir,
      ebrains_user_token: this.ebrains_user_token.toJsonValue(),
      max_duration_minutes: this.max_duration_minutes,
      listen_socket: this.listen_socket,
      session_url: this.session_url.toJsonValue(),
      session_allocator_host: this.session_allocator_host,
      session_allocator_username: this.session_allocator_username,
      session_allocator_socket_path: this.session_allocator_socket_path,
    };
  }
  public static fromJsonValue(value: JsonValue): WorkflowConfigDto | MessageParsingError {
    return parse_as_WorkflowConfigDto(value);
  }
}
