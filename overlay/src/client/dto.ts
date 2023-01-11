import {
  ensureJsonArray,
  ensureJsonBoolean,
  ensureJsonNumber,
  ensureJsonObject,
  ensureJsonString,
  ensureJsonUndefined,
} from "../util/safe_serialization";
import { JsonObject, JsonValue, toJsonValue } from "../util/serialization";

export function parse_as_int(value: JsonValue): number | Error {
  return ensureJsonNumber(value);
}
export function parse_as_ColorDto(value: JsonValue): ColorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ColorDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ColorDto`);
  }
  const temp_r = parse_as_int(valueObject.r);
  if (temp_r instanceof Error) return temp_r;
  const temp_g = parse_as_int(valueObject.g);
  if (temp_g instanceof Error) return temp_g;
  const temp_b = parse_as_int(valueObject.b);
  if (temp_b instanceof Error) return temp_b;
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
  public static fromJsonValue(value: JsonValue): ColorDto | Error {
    return parse_as_ColorDto(value);
  }
}

export function parse_as_str(value: JsonValue): string | Error {
  return ensureJsonString(value);
}
export function parse_as_LabelHeaderDto(value: JsonValue): LabelHeaderDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LabelHeaderDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a LabelHeaderDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_color = parse_as_ColorDto(valueObject.color);
  if (temp_color instanceof Error) return temp_color;
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
  public static fromJsonValue(value: JsonValue): LabelHeaderDto | Error {
    return parse_as_LabelHeaderDto(value);
  }
}

export function parse_as_Literal_of__quote_precomputed_quote_0_quote_n5_quote__endof_(
  value: JsonValue,
): "precomputed" | "n5" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "precomputed") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "n5") {
    return tmp_1;
  }
  return Error(`Could not parse ${value} as 'precomputed' | 'n5'`);
}
export function parse_as_None(value: JsonValue): undefined | Error {
  return ensureJsonUndefined(value);
}
export function parse_as_Union_of_Literal_of__quote_precomputed_quote_0_quote_n5_quote__endof_0None_endof_(
  value: JsonValue,
): "precomputed" | "n5" | undefined | Error {
  const parsed_option_0 = parse_as_Literal_of__quote_precomputed_quote_0_quote_n5_quote__endof_(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into 'precomputed' | 'n5' | undefined`);
}
export function parse_as_Literal_of__quote_http_quote_0_quote_https_quote_0_quote_file_quote_0_quote_memory_quote__endof_(
  value: JsonValue,
): "http" | "https" | "file" | "memory" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "http") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "https") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "file") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof Error) && tmp_3 === "memory") {
    return tmp_3;
  }
  return Error(`Could not parse ${value} as 'http' | 'https' | 'file' | 'memory'`);
}
export function parse_as_Union_of_int0None_endof_(value: JsonValue): number | undefined | Error {
  const parsed_option_0 = parse_as_int(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into number | undefined`);
}
export function parse_as_Mapping_of_str0str_endof_(value: JsonValue): { [key: string]: string } | Error {
  const valueObj = ensureJsonObject(value);
  if (valueObj instanceof Error) {
    return valueObj;
  }
  const out: { [key: string]: string } = {};
  for (let key in valueObj) {
    const parsed_key = parse_as_str(key);
    if (parsed_key instanceof Error) {
      return parsed_key;
    }
    const val = valueObj[key];
    const parsed_val = parse_as_str(val);
    if (parsed_val instanceof Error) {
      return parsed_val;
    }
    out[parsed_key] = parsed_val;
  }
  return out;
}
export function parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(
  value: JsonValue,
): { [key: string]: string } | undefined | Error {
  const parsed_option_0 = parse_as_Mapping_of_str0str_endof_(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into { [key: string]: string } | undefined`);
}
export function parse_as_Union_of_str0None_endof_(value: JsonValue): string | undefined | Error {
  const parsed_option_0 = parse_as_str(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into string | undefined`);
}
export function parse_as_UrlDto(value: JsonValue): UrlDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "UrlDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a UrlDto`);
  }
  const temp_datascheme = parse_as_Union_of_Literal_of__quote_precomputed_quote_0_quote_n5_quote__endof_0None_endof_(
    valueObject.datascheme,
  );
  if (temp_datascheme instanceof Error) return temp_datascheme;
  const temp_protocol =
    parse_as_Literal_of__quote_http_quote_0_quote_https_quote_0_quote_file_quote_0_quote_memory_quote__endof_(
      valueObject.protocol,
    );
  if (temp_protocol instanceof Error) return temp_protocol;
  const temp_hostname = parse_as_str(valueObject.hostname);
  if (temp_hostname instanceof Error) return temp_hostname;
  const temp_port = parse_as_Union_of_int0None_endof_(valueObject.port);
  if (temp_port instanceof Error) return temp_port;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_search = parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(valueObject.search);
  if (temp_search instanceof Error) return temp_search;
  const temp_fragment = parse_as_Union_of_str0None_endof_(valueObject.fragment);
  if (temp_fragment instanceof Error) return temp_fragment;
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
  public datascheme: "precomputed" | "n5" | undefined;
  public protocol: "http" | "https" | "file" | "memory";
  public hostname: string;
  public port: number | undefined;
  public path: string;
  public search: { [key: string]: string } | undefined;
  public fragment: string | undefined;
  constructor(_params: {
    datascheme: "precomputed" | "n5" | undefined;
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
  public static fromJsonValue(value: JsonValue): UrlDto | Error {
    return parse_as_UrlDto(value);
  }
}

export function parse_as_Point5DDto(value: JsonValue): Point5DDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "Point5DDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a Point5DDto`);
  }
  const temp_x = parse_as_int(valueObject.x);
  if (temp_x instanceof Error) return temp_x;
  const temp_y = parse_as_int(valueObject.y);
  if (temp_y instanceof Error) return temp_y;
  const temp_z = parse_as_int(valueObject.z);
  if (temp_z instanceof Error) return temp_z;
  const temp_t = parse_as_int(valueObject.t);
  if (temp_t instanceof Error) return temp_t;
  const temp_c = parse_as_int(valueObject.c);
  if (temp_c instanceof Error) return temp_c;
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
  public static fromJsonValue(value: JsonValue): Point5DDto | Error {
    return parse_as_Point5DDto(value);
  }
}

export function parse_as_Shape5DDto(value: JsonValue): Shape5DDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "Shape5DDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a Shape5DDto`);
  }
  const temp_x = parse_as_int(valueObject.x);
  if (temp_x instanceof Error) return temp_x;
  const temp_y = parse_as_int(valueObject.y);
  if (temp_y instanceof Error) return temp_y;
  const temp_z = parse_as_int(valueObject.z);
  if (temp_z instanceof Error) return temp_z;
  const temp_t = parse_as_int(valueObject.t);
  if (temp_t instanceof Error) return temp_t;
  const temp_c = parse_as_int(valueObject.c);
  if (temp_c instanceof Error) return temp_c;
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
  public static fromJsonValue(value: JsonValue): Shape5DDto | Error {
    return parse_as_Shape5DDto(value);
  }
}

export function parse_as_Interval5DDto(value: JsonValue): Interval5DDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "Interval5DDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a Interval5DDto`);
  }
  const temp_start = parse_as_Point5DDto(valueObject.start);
  if (temp_start instanceof Error) return temp_start;
  const temp_stop = parse_as_Point5DDto(valueObject.stop);
  if (temp_stop instanceof Error) return temp_stop;
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
  public static fromJsonValue(value: JsonValue): Interval5DDto | Error {
    return parse_as_Interval5DDto(value);
  }
}

export function parse_as_OsfsDto(value: JsonValue): OsfsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "OsfsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a OsfsDto`);
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
  public static fromJsonValue(value: JsonValue): OsfsDto | Error {
    return parse_as_OsfsDto(value);
  }
}

export function parse_as_Literal_of__quote_http_quote_0_quote_https_quote__endof_(
  value: JsonValue,
): "http" | "https" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "http") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "https") {
    return tmp_1;
  }
  return Error(`Could not parse ${value} as 'http' | 'https'`);
}
export function parse_as_HttpFsDto(value: JsonValue): HttpFsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "HttpFsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a HttpFsDto`);
  }
  const temp_protocol = parse_as_Literal_of__quote_http_quote_0_quote_https_quote__endof_(valueObject.protocol);
  if (temp_protocol instanceof Error) return temp_protocol;
  const temp_hostname = parse_as_str(valueObject.hostname);
  if (temp_hostname instanceof Error) return temp_hostname;
  const temp_port = parse_as_Union_of_int0None_endof_(valueObject.port);
  if (temp_port instanceof Error) return temp_port;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_search = parse_as_Union_of_Mapping_of_str0str_endof_0None_endof_(valueObject.search);
  if (temp_search instanceof Error) return temp_search;
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
  public static fromJsonValue(value: JsonValue): HttpFsDto | Error {
    return parse_as_HttpFsDto(value);
  }
}

export function parse_as_BucketFSDto(value: JsonValue): BucketFSDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "BucketFSDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a BucketFSDto`);
  }
  const temp_bucket_name = parse_as_str(valueObject.bucket_name);
  if (temp_bucket_name instanceof Error) return temp_bucket_name;
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
  public static fromJsonValue(value: JsonValue): BucketFSDto | Error {
    return parse_as_BucketFSDto(value);
  }
}

export function parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(
  value: JsonValue,
): OsfsDto | HttpFsDto | BucketFSDto | Error {
  const parsed_option_0 = parse_as_OsfsDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_HttpFsDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_BucketFSDto(value);
  if (!(parsed_option_2 instanceof Error)) {
    return parsed_option_2;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into OsfsDto | HttpFsDto | BucketFSDto`);
}
export function parse_as_Tuple_of_int0int0int_endof_(value: JsonValue): [number, number, number] | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const temp_0 = parse_as_int(arr[0]);
  if (temp_0 instanceof Error) return temp_0;
  const temp_1 = parse_as_int(arr[1]);
  if (temp_1 instanceof Error) return temp_1;
  const temp_2 = parse_as_int(arr[2]);
  if (temp_2 instanceof Error) return temp_2;
  return [temp_0, temp_1, temp_2];
}
export function parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
  value: JsonValue,
): "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "uint8") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "uint16") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "uint32") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof Error) && tmp_3 === "uint64") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof Error) && tmp_4 === "int64") {
    return tmp_4;
  }
  const tmp_5 = parse_as_str(value);
  if (!(tmp_5 instanceof Error) && tmp_5 === "float32") {
    return tmp_5;
  }
  return Error(`Could not parse ${value} as 'uint8' | 'uint16' | 'uint32' | 'uint64' | 'int64' | 'float32'`);
}
export function parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(
  value: JsonValue,
): "raw" | "jpeg" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "raw") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "jpeg") {
    return tmp_1;
  }
  return Error(`Could not parse ${value} as 'raw' | 'jpeg'`);
}
export function parse_as_PrecomputedChunksDataSourceDto(value: JsonValue): PrecomputedChunksDataSourceDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PrecomputedChunksDataSourceDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a PrecomputedChunksDataSourceDto`);
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof Error) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_scale_key = parse_as_str(valueObject.scale_key);
  if (temp_scale_key instanceof Error) return temp_scale_key;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof Error) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof Error) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof Error) return temp_spatial_resolution;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof Error) return temp_dtype;
  const temp_encoder = parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(valueObject.encoder);
  if (temp_encoder instanceof Error) return temp_encoder;
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
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto;
  public path: string;
  public scale_key: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public encoder: "raw" | "jpeg";
  constructor(_params: {
    url: UrlDto;
    filesystem: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): PrecomputedChunksDataSourceDto | Error {
    return parse_as_PrecomputedChunksDataSourceDto(value);
  }
}

export function parse_as_Literal_of__quote_jpeg_quote_0_quote_jpg_quote_0_quote_png_quote__endof_(
  value: JsonValue,
): "jpeg" | "jpg" | "png" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "jpeg") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "jpg") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "png") {
    return tmp_2;
  }
  return Error(`Could not parse ${value} as 'jpeg' | 'jpg' | 'png'`);
}
export function parse_as_DziLevelDto(value: JsonValue): DziLevelDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziLevelDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a DziLevelDto`);
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof Error) return temp_filesystem;
  const temp_level_path = parse_as_str(valueObject.level_path);
  if (temp_level_path instanceof Error) return temp_level_path;
  const temp_level_index = parse_as_int(valueObject.level_index);
  if (temp_level_index instanceof Error) return temp_level_index;
  const temp_overlap = parse_as_int(valueObject.overlap);
  if (temp_overlap instanceof Error) return temp_overlap;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof Error) return temp_tile_shape;
  const temp_shape = parse_as_Shape5DDto(valueObject.shape);
  if (temp_shape instanceof Error) return temp_shape;
  const temp_full_shape = parse_as_Shape5DDto(valueObject.full_shape);
  if (temp_full_shape instanceof Error) return temp_full_shape;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof Error) return temp_dtype;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof Error) return temp_spatial_resolution;
  const temp_image_format = parse_as_Literal_of__quote_jpeg_quote_0_quote_jpg_quote_0_quote_png_quote__endof_(
    valueObject.image_format,
  );
  if (temp_image_format instanceof Error) return temp_image_format;
  return new DziLevelDto({
    filesystem: temp_filesystem,
    level_path: temp_level_path,
    level_index: temp_level_index,
    overlap: temp_overlap,
    tile_shape: temp_tile_shape,
    shape: temp_shape,
    full_shape: temp_full_shape,
    dtype: temp_dtype,
    spatial_resolution: temp_spatial_resolution,
    image_format: temp_image_format,
  });
}
// Automatically generated via DataTransferObject for DziLevelDto
// Do not edit!
export class DziLevelDto {
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto;
  public level_path: string;
  public level_index: number;
  public overlap: number;
  public tile_shape: Shape5DDto;
  public shape: Shape5DDto;
  public full_shape: Shape5DDto;
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public spatial_resolution: [number, number, number];
  public image_format: "jpeg" | "jpg" | "png";
  constructor(_params: {
    filesystem: OsfsDto | HttpFsDto | BucketFSDto;
    level_path: string;
    level_index: number;
    overlap: number;
    tile_shape: Shape5DDto;
    shape: Shape5DDto;
    full_shape: Shape5DDto;
    dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
    spatial_resolution: [number, number, number];
    image_format: "jpeg" | "jpg" | "png";
  }) {
    this.filesystem = _params.filesystem;
    this.level_path = _params.level_path;
    this.level_index = _params.level_index;
    this.overlap = _params.overlap;
    this.tile_shape = _params.tile_shape;
    this.shape = _params.shape;
    this.full_shape = _params.full_shape;
    this.dtype = _params.dtype;
    this.spatial_resolution = _params.spatial_resolution;
    this.image_format = _params.image_format;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziLevelDto",
      filesystem: toJsonValue(this.filesystem),
      level_path: this.level_path,
      level_index: this.level_index,
      overlap: this.overlap,
      tile_shape: this.tile_shape.toJsonValue(),
      shape: this.shape.toJsonValue(),
      full_shape: this.full_shape.toJsonValue(),
      dtype: this.dtype,
      spatial_resolution: [this.spatial_resolution[0], this.spatial_resolution[1], this.spatial_resolution[2]],
      image_format: this.image_format,
    };
  }
  public static fromJsonValue(value: JsonValue): DziLevelDto | Error {
    return parse_as_DziLevelDto(value);
  }
}

export function parse_as_DziLevelDataSourceDto(value: JsonValue): DziLevelDataSourceDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziLevelDataSourceDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a DziLevelDataSourceDto`);
  }
  const temp_level = parse_as_DziLevelDto(valueObject.level);
  if (temp_level instanceof Error) return temp_level;
  return new DziLevelDataSourceDto({
    level: temp_level,
  });
}
// Automatically generated via DataTransferObject for DziLevelDataSourceDto
// Do not edit!
export class DziLevelDataSourceDto {
  public level: DziLevelDto;
  constructor(_params: {
    level: DziLevelDto;
  }) {
    this.level = _params.level;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziLevelDataSourceDto",
      level: this.level.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): DziLevelDataSourceDto | Error {
    return parse_as_DziLevelDataSourceDto(value);
  }
}

export function parse_as_N5GzipCompressorDto(value: JsonValue): N5GzipCompressorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["type"] != "gzip") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a N5GzipCompressorDto`);
  }
  const temp_level = parse_as_int(valueObject.level);
  if (temp_level instanceof Error) return temp_level;
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
  public static fromJsonValue(value: JsonValue): N5GzipCompressorDto | Error {
    return parse_as_N5GzipCompressorDto(value);
  }
}

export function parse_as_N5Bzip2CompressorDto(value: JsonValue): N5Bzip2CompressorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["type"] != "bzip2") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a N5Bzip2CompressorDto`);
  }
  const temp_blockSize = parse_as_int(valueObject.blockSize);
  if (temp_blockSize instanceof Error) return temp_blockSize;
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
  public static fromJsonValue(value: JsonValue): N5Bzip2CompressorDto | Error {
    return parse_as_N5Bzip2CompressorDto(value);
  }
}

export function parse_as_N5XzCompressorDto(value: JsonValue): N5XzCompressorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["type"] != "xz") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a N5XzCompressorDto`);
  }
  const temp_preset = parse_as_int(valueObject.preset);
  if (temp_preset instanceof Error) return temp_preset;
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
  public static fromJsonValue(value: JsonValue): N5XzCompressorDto | Error {
    return parse_as_N5XzCompressorDto(value);
  }
}

export function parse_as_N5RawCompressorDto(value: JsonValue): N5RawCompressorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["type"] != "raw") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a N5RawCompressorDto`);
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
  public static fromJsonValue(value: JsonValue): N5RawCompressorDto | Error {
    return parse_as_N5RawCompressorDto(value);
  }
}

export function parse_as_Tuple_of_int0_varlen__endof_(value: JsonValue): Array<number> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<number> = [];
  for (let item of arr) {
    let parsed_item = parse_as_int(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Tuple_of_str0_varlen__endof_(value: JsonValue): Array<string> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<string> = [];
  for (let item of arr) {
    let parsed_item = parse_as_str(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Union_of_Tuple_of_str0_varlen__endof_0None_endof_(
  value: JsonValue,
): Array<string> | undefined | Error {
  const parsed_option_0 = parse_as_Tuple_of_str0_varlen__endof_(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into Array<string> | undefined`);
}
export function parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
  value: JsonValue,
): N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto | Error {
  const parsed_option_0 = parse_as_N5GzipCompressorDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5Bzip2CompressorDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_N5XzCompressorDto(value);
  if (!(parsed_option_2 instanceof Error)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_N5RawCompressorDto(value);
  if (!(parsed_option_3 instanceof Error)) {
    return parsed_option_3;
  }
  return Error(
    `Could not parse ${
      JSON.stringify(value)
    } into N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto`,
  );
}
export function parse_as_N5DatasetAttributesDto(value: JsonValue): N5DatasetAttributesDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  const temp_dimensions = parse_as_Tuple_of_int0_varlen__endof_(valueObject.dimensions);
  if (temp_dimensions instanceof Error) return temp_dimensions;
  const temp_blockSize = parse_as_Tuple_of_int0_varlen__endof_(valueObject.blockSize);
  if (temp_blockSize instanceof Error) return temp_blockSize;
  const temp_axes = parse_as_Union_of_Tuple_of_str0_varlen__endof_0None_endof_(valueObject.axes);
  if (temp_axes instanceof Error) return temp_axes;
  const temp_dataType =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dataType,
    );
  if (temp_dataType instanceof Error) return temp_dataType;
  const temp_compression =
    parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
      valueObject.compression,
    );
  if (temp_compression instanceof Error) return temp_compression;
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
  public static fromJsonValue(value: JsonValue): N5DatasetAttributesDto | Error {
    return parse_as_N5DatasetAttributesDto(value);
  }
}

export function parse_as_N5DataSourceDto(value: JsonValue): N5DataSourceDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "N5DataSourceDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a N5DataSourceDto`);
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof Error) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof Error) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof Error) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof Error) return temp_spatial_resolution;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof Error) return temp_dtype;
  const temp_compressor =
    parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
      valueObject.compressor,
    );
  if (temp_compressor instanceof Error) return temp_compressor;
  const temp_c_axiskeys_on_disk = parse_as_str(valueObject.c_axiskeys_on_disk);
  if (temp_c_axiskeys_on_disk instanceof Error) return temp_c_axiskeys_on_disk;
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
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto;
  public path: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public compressor: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  public c_axiskeys_on_disk: string;
  constructor(_params: {
    url: UrlDto;
    filesystem: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): N5DataSourceDto | Error {
    return parse_as_N5DataSourceDto(value);
  }
}

export function parse_as_SkimageDataSourceDto(value: JsonValue): SkimageDataSourceDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SkimageDataSourceDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a SkimageDataSourceDto`);
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof Error) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof Error) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof Error) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof Error) return temp_spatial_resolution;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof Error) return temp_dtype;
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
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto;
  public path: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  constructor(_params: {
    url: UrlDto;
    filesystem: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): SkimageDataSourceDto | Error {
    return parse_as_SkimageDataSourceDto(value);
  }
}

export function parse_as_PrecomputedChunksSinkDto(value: JsonValue): PrecomputedChunksSinkDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PrecomputedChunksSinkDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a PrecomputedChunksSinkDto`);
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof Error) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof Error) return temp_tile_shape;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof Error) return temp_interval;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof Error) return temp_dtype;
  const temp_scale_key = parse_as_str(valueObject.scale_key);
  if (temp_scale_key instanceof Error) return temp_scale_key;
  const temp_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.resolution);
  if (temp_resolution instanceof Error) return temp_resolution;
  const temp_encoding = parse_as_Literal_of__quote_raw_quote_0_quote_jpeg_quote__endof_(valueObject.encoding);
  if (temp_encoding instanceof Error) return temp_encoding;
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
  public static fromJsonValue(value: JsonValue): PrecomputedChunksSinkDto | Error {
    return parse_as_PrecomputedChunksSinkDto(value);
  }
}

export function parse_as_DziLevelSinkDto(value: JsonValue): DziLevelSinkDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DziLevelSinkDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a DziLevelSinkDto`);
  }
  const temp_level = parse_as_DziLevelDto(valueObject.level);
  if (temp_level instanceof Error) return temp_level;
  return new DziLevelSinkDto({
    level: temp_level,
  });
}
// Automatically generated via DataTransferObject for DziLevelSinkDto
// Do not edit!
export class DziLevelSinkDto {
  public level: DziLevelDto;
  constructor(_params: {
    level: DziLevelDto;
  }) {
    this.level = _params.level;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DziLevelSinkDto",
      level: this.level.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): DziLevelSinkDto | Error {
    return parse_as_DziLevelSinkDto(value);
  }
}

export function parse_as_N5DataSinkDto(value: JsonValue): N5DataSinkDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "N5DataSinkDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a N5DataSinkDto`);
  }
  const temp_filesystem = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.filesystem);
  if (temp_filesystem instanceof Error) return temp_filesystem;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  const temp_interval = parse_as_Interval5DDto(valueObject.interval);
  if (temp_interval instanceof Error) return temp_interval;
  const temp_tile_shape = parse_as_Shape5DDto(valueObject.tile_shape);
  if (temp_tile_shape instanceof Error) return temp_tile_shape;
  const temp_spatial_resolution = parse_as_Tuple_of_int0int0int_endof_(valueObject.spatial_resolution);
  if (temp_spatial_resolution instanceof Error) return temp_spatial_resolution;
  const temp_c_axiskeys = parse_as_str(valueObject.c_axiskeys);
  if (temp_c_axiskeys instanceof Error) return temp_c_axiskeys;
  const temp_dtype =
    parse_as_Literal_of__quote_uint8_quote_0_quote_uint16_quote_0_quote_uint32_quote_0_quote_uint64_quote_0_quote_int64_quote_0_quote_float32_quote__endof_(
      valueObject.dtype,
    );
  if (temp_dtype instanceof Error) return temp_dtype;
  const temp_compressor =
    parse_as_Union_of_N5GzipCompressorDto0N5Bzip2CompressorDto0N5XzCompressorDto0N5RawCompressorDto_endof_(
      valueObject.compressor,
    );
  if (temp_compressor instanceof Error) return temp_compressor;
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
  public filesystem: OsfsDto | HttpFsDto | BucketFSDto;
  public path: string;
  public interval: Interval5DDto;
  public tile_shape: Shape5DDto;
  public spatial_resolution: [number, number, number];
  public c_axiskeys: string;
  public dtype: "uint8" | "uint16" | "uint32" | "uint64" | "int64" | "float32";
  public compressor: N5GzipCompressorDto | N5Bzip2CompressorDto | N5XzCompressorDto | N5RawCompressorDto;
  constructor(_params: {
    filesystem: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): N5DataSinkDto | Error {
    return parse_as_N5DataSinkDto(value);
  }
}

export function parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
  value: JsonValue,
): PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto | Error {
  const parsed_option_0 = parse_as_PrecomputedChunksDataSourceDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5DataSourceDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_SkimageDataSourceDto(value);
  if (!(parsed_option_2 instanceof Error)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_DziLevelDataSourceDto(value);
  if (!(parsed_option_3 instanceof Error)) {
    return parsed_option_3;
  }
  return Error(
    `Could not parse ${
      JSON.stringify(value)
    } into PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto`,
  );
}
export function parse_as_Tuple_of_Tuple_of_int0int0int_endof_0_varlen__endof_(
  value: JsonValue,
): Array<[number, number, number]> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<[number, number, number]> = [];
  for (let item of arr) {
    let parsed_item = parse_as_Tuple_of_int0int0int_endof_(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_PixelAnnotationDto(value: JsonValue): PixelAnnotationDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PixelAnnotationDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a PixelAnnotationDto`);
  }
  const temp_raw_data =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.raw_data,
    );
  if (temp_raw_data instanceof Error) return temp_raw_data;
  const temp_points = parse_as_Tuple_of_Tuple_of_int0int0int_endof_0_varlen__endof_(valueObject.points);
  if (temp_points instanceof Error) return temp_points;
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
  public static fromJsonValue(value: JsonValue): PixelAnnotationDto | Error {
    return parse_as_PixelAnnotationDto(value);
  }
}

export function parse_as_RpcErrorDto(value: JsonValue): RpcErrorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RpcErrorDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RpcErrorDto`);
  }
  const temp_error = parse_as_str(valueObject.error);
  if (temp_error instanceof Error) return temp_error;
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
  public static fromJsonValue(value: JsonValue): RpcErrorDto | Error {
    return parse_as_RpcErrorDto(value);
  }
}

export function parse_as_RecolorLabelParams(value: JsonValue): RecolorLabelParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RecolorLabelParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RecolorLabelParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof Error) return temp_label_name;
  const temp_new_color = parse_as_ColorDto(valueObject.new_color);
  if (temp_new_color instanceof Error) return temp_new_color;
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
  public static fromJsonValue(value: JsonValue): RecolorLabelParams | Error {
    return parse_as_RecolorLabelParams(value);
  }
}

export function parse_as_RenameLabelParams(value: JsonValue): RenameLabelParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RenameLabelParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RenameLabelParams`);
  }
  const temp_old_name = parse_as_str(valueObject.old_name);
  if (temp_old_name instanceof Error) return temp_old_name;
  const temp_new_name = parse_as_str(valueObject.new_name);
  if (temp_new_name instanceof Error) return temp_new_name;
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
  public static fromJsonValue(value: JsonValue): RenameLabelParams | Error {
    return parse_as_RenameLabelParams(value);
  }
}

export function parse_as_CreateLabelParams(value: JsonValue): CreateLabelParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CreateLabelParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CreateLabelParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof Error) return temp_label_name;
  const temp_color = parse_as_ColorDto(valueObject.color);
  if (temp_color instanceof Error) return temp_color;
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
  public static fromJsonValue(value: JsonValue): CreateLabelParams | Error {
    return parse_as_CreateLabelParams(value);
  }
}

export function parse_as_RemoveLabelParams(value: JsonValue): RemoveLabelParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RemoveLabelParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RemoveLabelParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof Error) return temp_label_name;
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
  public static fromJsonValue(value: JsonValue): RemoveLabelParams | Error {
    return parse_as_RemoveLabelParams(value);
  }
}

export function parse_as_AddPixelAnnotationParams(value: JsonValue): AddPixelAnnotationParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "AddPixelAnnotationParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a AddPixelAnnotationParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof Error) return temp_label_name;
  const temp_pixel_annotation = parse_as_PixelAnnotationDto(valueObject.pixel_annotation);
  if (temp_pixel_annotation instanceof Error) return temp_pixel_annotation;
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
  public static fromJsonValue(value: JsonValue): AddPixelAnnotationParams | Error {
    return parse_as_AddPixelAnnotationParams(value);
  }
}

export function parse_as_RemovePixelAnnotationParams(value: JsonValue): RemovePixelAnnotationParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RemovePixelAnnotationParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RemovePixelAnnotationParams`);
  }
  const temp_label_name = parse_as_str(valueObject.label_name);
  if (temp_label_name instanceof Error) return temp_label_name;
  const temp_pixel_annotation = parse_as_PixelAnnotationDto(valueObject.pixel_annotation);
  if (temp_pixel_annotation instanceof Error) return temp_pixel_annotation;
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
  public static fromJsonValue(value: JsonValue): RemovePixelAnnotationParams | Error {
    return parse_as_RemovePixelAnnotationParams(value);
  }
}

export function parse_as_Tuple_of_PixelAnnotationDto0_varlen__endof_(
  value: JsonValue,
): Array<PixelAnnotationDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<PixelAnnotationDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_PixelAnnotationDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_LabelDto(value: JsonValue): LabelDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LabelDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a LabelDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_color = parse_as_ColorDto(valueObject.color);
  if (temp_color instanceof Error) return temp_color;
  const temp_annotations = parse_as_Tuple_of_PixelAnnotationDto0_varlen__endof_(valueObject.annotations);
  if (temp_annotations instanceof Error) return temp_annotations;
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
  public static fromJsonValue(value: JsonValue): LabelDto | Error {
    return parse_as_LabelDto(value);
  }
}

export function parse_as_Tuple_of_LabelDto0_varlen__endof_(value: JsonValue): Array<LabelDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<LabelDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_LabelDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_BrushingAppletStateDto(value: JsonValue): BrushingAppletStateDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "BrushingAppletStateDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a BrushingAppletStateDto`);
  }
  const temp_labels = parse_as_Tuple_of_LabelDto0_varlen__endof_(valueObject.labels);
  if (temp_labels instanceof Error) return temp_labels;
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
  public static fromJsonValue(value: JsonValue): BrushingAppletStateDto | Error {
    return parse_as_BrushingAppletStateDto(value);
  }
}

export function parse_as_ViewDto(value: JsonValue): ViewDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ViewDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ViewDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  return new ViewDto({
    name: temp_name,
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for ViewDto
// Do not edit!
export class ViewDto {
  public name: string;
  public url: UrlDto;
  constructor(_params: {
    name: string;
    url: UrlDto;
  }) {
    this.name = _params.name;
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ViewDto",
      name: this.name,
      url: this.url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): ViewDto | Error {
    return parse_as_ViewDto(value);
  }
}

export function parse_as_DataView(value: JsonValue): DataView | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "DataView") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a DataView`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  return new DataView({
    name: temp_name,
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for DataView
// Do not edit!
export class DataView {
  public name: string;
  public url: UrlDto;
  constructor(_params: {
    name: string;
    url: UrlDto;
  }) {
    this.name = _params.name;
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "DataView",
      name: this.name,
      url: this.url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): DataView | Error {
    return parse_as_DataView(value);
  }
}

export function parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
  value: JsonValue,
): Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto> =
    [];
  for (let item of arr) {
    let parsed_item =
      parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
        item,
      );
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_RawDataViewDto(value: JsonValue): RawDataViewDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RawDataViewDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RawDataViewDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_datasources =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      valueObject.datasources,
    );
  if (temp_datasources instanceof Error) return temp_datasources;
  return new RawDataViewDto({
    name: temp_name,
    url: temp_url,
    datasources: temp_datasources,
  });
}
// Automatically generated via DataTransferObject for RawDataViewDto
// Do not edit!
export class RawDataViewDto {
  public name: string;
  public url: UrlDto;
  public datasources: Array<
    PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto
  >;
  constructor(_params: {
    name: string;
    url: UrlDto;
    datasources: Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>;
  }) {
    this.name = _params.name;
    this.url = _params.url;
    this.datasources = _params.datasources;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RawDataViewDto",
      name: this.name,
      url: this.url.toJsonValue(),
      datasources: this.datasources.map((item) => toJsonValue(item)),
    };
  }
  public static fromJsonValue(value: JsonValue): RawDataViewDto | Error {
    return parse_as_RawDataViewDto(value);
  }
}

export function parse_as_StrippedPrecomputedViewDto(value: JsonValue): StrippedPrecomputedViewDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "StrippedPrecomputedViewDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a StrippedPrecomputedViewDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_datasource =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.datasource,
    );
  if (temp_datasource instanceof Error) return temp_datasource;
  return new StrippedPrecomputedViewDto({
    name: temp_name,
    url: temp_url,
    datasource: temp_datasource,
  });
}
// Automatically generated via DataTransferObject for StrippedPrecomputedViewDto
// Do not edit!
export class StrippedPrecomputedViewDto {
  public name: string;
  public url: UrlDto;
  public datasource: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
  constructor(_params: {
    name: string;
    url: UrlDto;
    datasource: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
  }) {
    this.name = _params.name;
    this.url = _params.url;
    this.datasource = _params.datasource;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "StrippedPrecomputedViewDto",
      name: this.name,
      url: this.url.toJsonValue(),
      datasource: toJsonValue(this.datasource),
    };
  }
  public static fromJsonValue(value: JsonValue): StrippedPrecomputedViewDto | Error {
    return parse_as_StrippedPrecomputedViewDto(value);
  }
}

export function parse_as_PredictionsViewDto(value: JsonValue): PredictionsViewDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PredictionsViewDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a PredictionsViewDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_raw_data =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.raw_data,
    );
  if (temp_raw_data instanceof Error) return temp_raw_data;
  const temp_classifier_generation = parse_as_int(valueObject.classifier_generation);
  if (temp_classifier_generation instanceof Error) return temp_classifier_generation;
  return new PredictionsViewDto({
    name: temp_name,
    url: temp_url,
    raw_data: temp_raw_data,
    classifier_generation: temp_classifier_generation,
  });
}
// Automatically generated via DataTransferObject for PredictionsViewDto
// Do not edit!
export class PredictionsViewDto {
  public name: string;
  public url: UrlDto;
  public raw_data: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
  public classifier_generation: number;
  constructor(_params: {
    name: string;
    url: UrlDto;
    raw_data: PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto;
    classifier_generation: number;
  }) {
    this.name = _params.name;
    this.url = _params.url;
    this.raw_data = _params.raw_data;
    this.classifier_generation = _params.classifier_generation;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "PredictionsViewDto",
      name: this.name,
      url: this.url.toJsonValue(),
      raw_data: toJsonValue(this.raw_data),
      classifier_generation: this.classifier_generation,
    };
  }
  public static fromJsonValue(value: JsonValue): PredictionsViewDto | Error {
    return parse_as_PredictionsViewDto(value);
  }
}

export function parse_as_FailedViewDto(value: JsonValue): FailedViewDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "FailedViewDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a FailedViewDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  const temp_error_message = parse_as_str(valueObject.error_message);
  if (temp_error_message instanceof Error) return temp_error_message;
  return new FailedViewDto({
    name: temp_name,
    url: temp_url,
    error_message: temp_error_message,
  });
}
// Automatically generated via DataTransferObject for FailedViewDto
// Do not edit!
export class FailedViewDto {
  public name: string;
  public url: UrlDto;
  public error_message: string;
  constructor(_params: {
    name: string;
    url: UrlDto;
    error_message: string;
  }) {
    this.name = _params.name;
    this.url = _params.url;
    this.error_message = _params.error_message;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "FailedViewDto",
      name: this.name,
      url: this.url.toJsonValue(),
      error_message: this.error_message,
    };
  }
  public static fromJsonValue(value: JsonValue): FailedViewDto | Error {
    return parse_as_FailedViewDto(value);
  }
}

export function parse_as_UnsupportedDatasetViewDto(value: JsonValue): UnsupportedDatasetViewDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "UnsupportedDatasetViewDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a UnsupportedDatasetViewDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  return new UnsupportedDatasetViewDto({
    name: temp_name,
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for UnsupportedDatasetViewDto
// Do not edit!
export class UnsupportedDatasetViewDto {
  public name: string;
  public url: UrlDto;
  constructor(_params: {
    name: string;
    url: UrlDto;
  }) {
    this.name = _params.name;
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "UnsupportedDatasetViewDto",
      name: this.name,
      url: this.url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): UnsupportedDatasetViewDto | Error {
    return parse_as_UnsupportedDatasetViewDto(value);
  }
}

export function parse_as_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_(
  value: JsonValue,
): RawDataViewDto | StrippedPrecomputedViewDto | FailedViewDto | UnsupportedDatasetViewDto | Error {
  const parsed_option_0 = parse_as_RawDataViewDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_StrippedPrecomputedViewDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_FailedViewDto(value);
  if (!(parsed_option_2 instanceof Error)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_UnsupportedDatasetViewDto(value);
  if (!(parsed_option_3 instanceof Error)) {
    return parsed_option_3;
  }
  return Error(
    `Could not parse ${
      JSON.stringify(value)
    } into RawDataViewDto | StrippedPrecomputedViewDto | FailedViewDto | UnsupportedDatasetViewDto`,
  );
}
export function parse_as_Tuple_of_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_0_varlen__endof_(
  value: JsonValue,
): Array<RawDataViewDto | StrippedPrecomputedViewDto | FailedViewDto | UnsupportedDatasetViewDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<RawDataViewDto | StrippedPrecomputedViewDto | FailedViewDto | UnsupportedDatasetViewDto> = [];
  for (let item of arr) {
    let parsed_item =
      parse_as_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Tuple_of_PredictionsViewDto0_varlen__endof_(
  value: JsonValue,
): Array<PredictionsViewDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<PredictionsViewDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_PredictionsViewDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Tuple_of_ColorDto0_varlen__endof_(value: JsonValue): Array<ColorDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<ColorDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_ColorDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_ViewerAppletStateDto(value: JsonValue): ViewerAppletStateDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ViewerAppletStateDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ViewerAppletStateDto`);
  }
  const temp_frontend_timestamp = parse_as_int(valueObject.frontend_timestamp);
  if (temp_frontend_timestamp instanceof Error) return temp_frontend_timestamp;
  const temp_data_views =
    parse_as_Tuple_of_Union_of_RawDataViewDto0StrippedPrecomputedViewDto0FailedViewDto0UnsupportedDatasetViewDto_endof_0_varlen__endof_(
      valueObject.data_views,
    );
  if (temp_data_views instanceof Error) return temp_data_views;
  const temp_prediction_views = parse_as_Tuple_of_PredictionsViewDto0_varlen__endof_(valueObject.prediction_views);
  if (temp_prediction_views instanceof Error) return temp_prediction_views;
  const temp_label_colors = parse_as_Tuple_of_ColorDto0_varlen__endof_(valueObject.label_colors);
  if (temp_label_colors instanceof Error) return temp_label_colors;
  return new ViewerAppletStateDto({
    frontend_timestamp: temp_frontend_timestamp,
    data_views: temp_data_views,
    prediction_views: temp_prediction_views,
    label_colors: temp_label_colors,
  });
}
// Automatically generated via DataTransferObject for ViewerAppletStateDto
// Do not edit!
export class ViewerAppletStateDto {
  public frontend_timestamp: number;
  public data_views: Array<RawDataViewDto | StrippedPrecomputedViewDto | FailedViewDto | UnsupportedDatasetViewDto>;
  public prediction_views: Array<PredictionsViewDto>;
  public label_colors: Array<ColorDto>;
  constructor(_params: {
    frontend_timestamp: number;
    data_views: Array<RawDataViewDto | StrippedPrecomputedViewDto | FailedViewDto | UnsupportedDatasetViewDto>;
    prediction_views: Array<PredictionsViewDto>;
    label_colors: Array<ColorDto>;
  }) {
    this.frontend_timestamp = _params.frontend_timestamp;
    this.data_views = _params.data_views;
    this.prediction_views = _params.prediction_views;
    this.label_colors = _params.label_colors;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ViewerAppletStateDto",
      frontend_timestamp: this.frontend_timestamp,
      data_views: this.data_views.map((item) => toJsonValue(item)),
      prediction_views: this.prediction_views.map((item) => item.toJsonValue()),
      label_colors: this.label_colors.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): ViewerAppletStateDto | Error {
    return parse_as_ViewerAppletStateDto(value);
  }
}

export function parse_as_MakeDataViewParams(value: JsonValue): MakeDataViewParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "MakeDataViewParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a MakeDataViewParams`);
  }
  const temp_view_name = parse_as_str(valueObject.view_name);
  if (temp_view_name instanceof Error) return temp_view_name;
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
  return new MakeDataViewParams({
    view_name: temp_view_name,
    url: temp_url,
  });
}
// Automatically generated via DataTransferObject for MakeDataViewParams
// Do not edit!
export class MakeDataViewParams {
  public view_name: string;
  public url: UrlDto;
  constructor(_params: {
    view_name: string;
    url: UrlDto;
  }) {
    this.view_name = _params.view_name;
    this.url = _params.url;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "MakeDataViewParams",
      view_name: this.view_name,
      url: this.url.toJsonValue(),
    };
  }
  public static fromJsonValue(value: JsonValue): MakeDataViewParams | Error {
    return parse_as_MakeDataViewParams(value);
  }
}

export function parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
  value: JsonValue,
): "pending" | "running" | "cancelled" | "failed" | "succeeded" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "pending") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "running") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "cancelled") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof Error) && tmp_3 === "failed") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof Error) && tmp_4 === "succeeded") {
    return tmp_4;
  }
  return Error(`Could not parse ${value} as 'pending' | 'running' | 'cancelled' | 'failed' | 'succeeded'`);
}
export function parse_as_JobDto(value: JsonValue): JobDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "JobDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a JobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof Error) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof Error) return temp_uuid;
  const temp_status =
    parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
      valueObject.status,
    );
  if (temp_status instanceof Error) return temp_status;
  const temp_num_completed_steps = parse_as_int(valueObject.num_completed_steps);
  if (temp_num_completed_steps instanceof Error) return temp_num_completed_steps;
  const temp_error_message = parse_as_Union_of_str0None_endof_(valueObject.error_message);
  if (temp_error_message instanceof Error) return temp_error_message;
  return new JobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    num_completed_steps: temp_num_completed_steps,
    error_message: temp_error_message,
  });
}
// Automatically generated via DataTransferObject for JobDto
// Do not edit!
export class JobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: "pending" | "running" | "cancelled" | "failed" | "succeeded";
  public num_completed_steps: number;
  public error_message: string | undefined;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: "pending" | "running" | "cancelled" | "failed" | "succeeded";
    num_completed_steps: number;
    error_message: string | undefined;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.num_completed_steps = _params.num_completed_steps;
    this.error_message = _params.error_message;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "JobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: this.status,
      num_completed_steps: this.num_completed_steps,
      error_message: toJsonValue(this.error_message),
    };
  }
  public static fromJsonValue(value: JsonValue): JobDto | Error {
    return parse_as_JobDto(value);
  }
}

export function parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
  value: JsonValue,
): PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto | Error {
  const parsed_option_0 = parse_as_PrecomputedChunksSinkDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5DataSinkDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_DziLevelSinkDto(value);
  if (!(parsed_option_2 instanceof Error)) {
    return parsed_option_2;
  }
  return Error(
    `Could not parse ${JSON.stringify(value)} into PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto`,
  );
}
export function parse_as_ExportJobDto(value: JsonValue): ExportJobDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ExportJobDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ExportJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof Error) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof Error) return temp_uuid;
  const temp_status =
    parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
      valueObject.status,
    );
  if (temp_status instanceof Error) return temp_status;
  const temp_num_completed_steps = parse_as_int(valueObject.num_completed_steps);
  if (temp_num_completed_steps instanceof Error) return temp_num_completed_steps;
  const temp_error_message = parse_as_Union_of_str0None_endof_(valueObject.error_message);
  if (temp_error_message instanceof Error) return temp_error_message;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof Error) return temp_datasink;
  return new ExportJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    num_completed_steps: temp_num_completed_steps,
    error_message: temp_error_message,
    datasink: temp_datasink,
  });
}
// Automatically generated via DataTransferObject for ExportJobDto
// Do not edit!
export class ExportJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: "pending" | "running" | "cancelled" | "failed" | "succeeded";
  public num_completed_steps: number;
  public error_message: string | undefined;
  public datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: "pending" | "running" | "cancelled" | "failed" | "succeeded";
    num_completed_steps: number;
    error_message: string | undefined;
    datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.num_completed_steps = _params.num_completed_steps;
    this.error_message = _params.error_message;
    this.datasink = _params.datasink;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ExportJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: this.status,
      num_completed_steps: this.num_completed_steps,
      error_message: toJsonValue(this.error_message),
      datasink: toJsonValue(this.datasink),
    };
  }
  public static fromJsonValue(value: JsonValue): ExportJobDto | Error {
    return parse_as_ExportJobDto(value);
  }
}

export function parse_as_OpenDatasinkJobDto(value: JsonValue): OpenDatasinkJobDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "OpenDatasinkJobDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a OpenDatasinkJobDto`);
  }
  const temp_name = parse_as_str(valueObject.name);
  if (temp_name instanceof Error) return temp_name;
  const temp_num_args = parse_as_Union_of_int0None_endof_(valueObject.num_args);
  if (temp_num_args instanceof Error) return temp_num_args;
  const temp_uuid = parse_as_str(valueObject.uuid);
  if (temp_uuid instanceof Error) return temp_uuid;
  const temp_status =
    parse_as_Literal_of__quote_pending_quote_0_quote_running_quote_0_quote_cancelled_quote_0_quote_failed_quote_0_quote_succeeded_quote__endof_(
      valueObject.status,
    );
  if (temp_status instanceof Error) return temp_status;
  const temp_num_completed_steps = parse_as_int(valueObject.num_completed_steps);
  if (temp_num_completed_steps instanceof Error) return temp_num_completed_steps;
  const temp_error_message = parse_as_Union_of_str0None_endof_(valueObject.error_message);
  if (temp_error_message instanceof Error) return temp_error_message;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof Error) return temp_datasink;
  return new OpenDatasinkJobDto({
    name: temp_name,
    num_args: temp_num_args,
    uuid: temp_uuid,
    status: temp_status,
    num_completed_steps: temp_num_completed_steps,
    error_message: temp_error_message,
    datasink: temp_datasink,
  });
}
// Automatically generated via DataTransferObject for OpenDatasinkJobDto
// Do not edit!
export class OpenDatasinkJobDto {
  public name: string;
  public num_args: number | undefined;
  public uuid: string;
  public status: "pending" | "running" | "cancelled" | "failed" | "succeeded";
  public num_completed_steps: number;
  public error_message: string | undefined;
  public datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  constructor(_params: {
    name: string;
    num_args: number | undefined;
    uuid: string;
    status: "pending" | "running" | "cancelled" | "failed" | "succeeded";
    num_completed_steps: number;
    error_message: string | undefined;
    datasink: PrecomputedChunksSinkDto | N5DataSinkDto | DziLevelSinkDto;
  }) {
    this.name = _params.name;
    this.num_args = _params.num_args;
    this.uuid = _params.uuid;
    this.status = _params.status;
    this.num_completed_steps = _params.num_completed_steps;
    this.error_message = _params.error_message;
    this.datasink = _params.datasink;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "OpenDatasinkJobDto",
      name: this.name,
      num_args: toJsonValue(this.num_args),
      uuid: this.uuid,
      status: this.status,
      num_completed_steps: this.num_completed_steps,
      error_message: toJsonValue(this.error_message),
      datasink: toJsonValue(this.datasink),
    };
  }
  public static fromJsonValue(value: JsonValue): OpenDatasinkJobDto | Error {
    return parse_as_OpenDatasinkJobDto(value);
  }
}

export function parse_as_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_(
  value: JsonValue,
): ExportJobDto | OpenDatasinkJobDto | Error {
  const parsed_option_0 = parse_as_ExportJobDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_OpenDatasinkJobDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into ExportJobDto | OpenDatasinkJobDto`);
}
export function parse_as_Tuple_of_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_0_varlen__endof_(
  value: JsonValue,
): Array<ExportJobDto | OpenDatasinkJobDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<ExportJobDto | OpenDatasinkJobDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Tuple_of_LabelHeaderDto0_varlen__endof_(value: JsonValue): Array<LabelHeaderDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<LabelHeaderDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_LabelHeaderDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_Union_of_Tuple_of_LabelHeaderDto0_varlen__endof_0None_endof_(
  value: JsonValue,
): Array<LabelHeaderDto> | undefined | Error {
  const parsed_option_0 = parse_as_Tuple_of_LabelHeaderDto0_varlen__endof_(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into Array<LabelHeaderDto> | undefined`);
}
export function parse_as_Union_of_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_0None_endof_(
  value: JsonValue,
):
  | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
  | undefined
  | Error {
  const parsed_option_0 =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      value,
    );
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(
    `Could not parse ${
      JSON.stringify(value)
    } into Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto> | undefined`,
  );
}
export function parse_as_PixelClassificationExportAppletStateDto(
  value: JsonValue,
): PixelClassificationExportAppletStateDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "PixelClassificationExportAppletStateDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a PixelClassificationExportAppletStateDto`);
  }
  const temp_jobs = parse_as_Tuple_of_Union_of_ExportJobDto0OpenDatasinkJobDto_endof_0_varlen__endof_(valueObject.jobs);
  if (temp_jobs instanceof Error) return temp_jobs;
  const temp_populated_labels = parse_as_Union_of_Tuple_of_LabelHeaderDto0_varlen__endof_0None_endof_(
    valueObject.populated_labels,
  );
  if (temp_populated_labels instanceof Error) return temp_populated_labels;
  const temp_datasource_suggestions =
    parse_as_Union_of_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_0None_endof_(
      valueObject.datasource_suggestions,
    );
  if (temp_datasource_suggestions instanceof Error) return temp_datasource_suggestions;
  return new PixelClassificationExportAppletStateDto({
    jobs: temp_jobs,
    populated_labels: temp_populated_labels,
    datasource_suggestions: temp_datasource_suggestions,
  });
}
// Automatically generated via DataTransferObject for PixelClassificationExportAppletStateDto
// Do not edit!
export class PixelClassificationExportAppletStateDto {
  public jobs: Array<ExportJobDto | OpenDatasinkJobDto>;
  public populated_labels: Array<LabelHeaderDto> | undefined;
  public datasource_suggestions:
    | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
    | undefined;
  constructor(_params: {
    jobs: Array<ExportJobDto | OpenDatasinkJobDto>;
    populated_labels: Array<LabelHeaderDto> | undefined;
    datasource_suggestions:
      | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
      | undefined;
  }) {
    this.jobs = _params.jobs;
    this.populated_labels = _params.populated_labels;
    this.datasource_suggestions = _params.datasource_suggestions;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "PixelClassificationExportAppletStateDto",
      jobs: this.jobs.map((item) => toJsonValue(item)),
      populated_labels: toJsonValue(this.populated_labels),
      datasource_suggestions: toJsonValue(this.datasource_suggestions),
    };
  }
  public static fromJsonValue(value: JsonValue): PixelClassificationExportAppletStateDto | Error {
    return parse_as_PixelClassificationExportAppletStateDto(value);
  }
}

export function parse_as_float(value: JsonValue): number | Error {
  return ensureJsonNumber(value);
}
export function parse_as_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_(
  value: JsonValue,
): "x" | "y" | "z" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "x") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "y") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "z") {
    return tmp_2;
  }
  return Error(`Could not parse ${value} as 'x' | 'y' | 'z'`);
}
export function parse_as_Union_of_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_0None_endof_(
  value: JsonValue,
): "x" | "y" | "z" | undefined | Error {
  const parsed_option_0 = parse_as_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_None(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  return Error(`Could not parse ${JSON.stringify(value)} into 'x' | 'y' | 'z' | undefined`);
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
  | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "Gaussian Smoothing") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "Laplacian of Gaussian") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "Gaussian Gradient Magnitude") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof Error) && tmp_3 === "Difference of Gaussians") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof Error) && tmp_4 === "Structure Tensor Eigenvalues") {
    return tmp_4;
  }
  const tmp_5 = parse_as_str(value);
  if (!(tmp_5 instanceof Error) && tmp_5 === "Hessian of Gaussian Eigenvalues") {
    return tmp_5;
  }
  return Error(
    `Could not parse ${value} as 'Gaussian Smoothing' | 'Laplacian of Gaussian' | 'Gaussian Gradient Magnitude' | 'Difference of Gaussians' | 'Structure Tensor Eigenvalues' | 'Hessian of Gaussian Eigenvalues'`,
  );
}
export function parse_as_IlpFeatureExtractorDto(value: JsonValue): IlpFeatureExtractorDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "IlpFeatureExtractorDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a IlpFeatureExtractorDto`);
  }
  const temp_ilp_scale = parse_as_float(valueObject.ilp_scale);
  if (temp_ilp_scale instanceof Error) return temp_ilp_scale;
  const temp_axis_2d = parse_as_Union_of_Literal_of__quote_x_quote_0_quote_y_quote_0_quote_z_quote__endof_0None_endof_(
    valueObject.axis_2d,
  );
  if (temp_axis_2d instanceof Error) return temp_axis_2d;
  const temp_class_name =
    parse_as_Literal_of__quote_GaussianSmoothing_quote_0_quote_LaplacianofGaussian_quote_0_quote_GaussianGradientMagnitude_quote_0_quote_DifferenceofGaussians_quote_0_quote_StructureTensorEigenvalues_quote_0_quote_HessianofGaussianEigenvalues_quote__endof_(
      valueObject.class_name,
    );
  if (temp_class_name instanceof Error) return temp_class_name;
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
  public static fromJsonValue(value: JsonValue): IlpFeatureExtractorDto | Error {
    return parse_as_IlpFeatureExtractorDto(value);
  }
}

export function parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
  value: JsonValue,
): Array<IlpFeatureExtractorDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<IlpFeatureExtractorDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_IlpFeatureExtractorDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_FeatureSelectionAppletStateDto(value: JsonValue): FeatureSelectionAppletStateDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "FeatureSelectionAppletStateDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a FeatureSelectionAppletStateDto`);
  }
  const temp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
    valueObject.feature_extractors,
  );
  if (temp_feature_extractors instanceof Error) return temp_feature_extractors;
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
  public static fromJsonValue(value: JsonValue): FeatureSelectionAppletStateDto | Error {
    return parse_as_FeatureSelectionAppletStateDto(value);
  }
}

export function parse_as_AddFeatureExtractorsParamsDto(value: JsonValue): AddFeatureExtractorsParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "AddFeatureExtractorsParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a AddFeatureExtractorsParamsDto`);
  }
  const temp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
    valueObject.feature_extractors,
  );
  if (temp_feature_extractors instanceof Error) return temp_feature_extractors;
  return new AddFeatureExtractorsParamsDto({
    feature_extractors: temp_feature_extractors,
  });
}
// Automatically generated via DataTransferObject for AddFeatureExtractorsParamsDto
// Do not edit!
export class AddFeatureExtractorsParamsDto {
  public feature_extractors: Array<IlpFeatureExtractorDto>;
  constructor(_params: {
    feature_extractors: Array<IlpFeatureExtractorDto>;
  }) {
    this.feature_extractors = _params.feature_extractors;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "AddFeatureExtractorsParamsDto",
      feature_extractors: this.feature_extractors.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): AddFeatureExtractorsParamsDto | Error {
    return parse_as_AddFeatureExtractorsParamsDto(value);
  }
}

export function parse_as_RemoveFeatureExtractorsParamsDto(value: JsonValue): RemoveFeatureExtractorsParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "RemoveFeatureExtractorsParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a RemoveFeatureExtractorsParamsDto`);
  }
  const temp_feature_extractors = parse_as_Tuple_of_IlpFeatureExtractorDto0_varlen__endof_(
    valueObject.feature_extractors,
  );
  if (temp_feature_extractors instanceof Error) return temp_feature_extractors;
  return new RemoveFeatureExtractorsParamsDto({
    feature_extractors: temp_feature_extractors,
  });
}
// Automatically generated via DataTransferObject for RemoveFeatureExtractorsParamsDto
// Do not edit!
export class RemoveFeatureExtractorsParamsDto {
  public feature_extractors: Array<IlpFeatureExtractorDto>;
  constructor(_params: {
    feature_extractors: Array<IlpFeatureExtractorDto>;
  }) {
    this.feature_extractors = _params.feature_extractors;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "RemoveFeatureExtractorsParamsDto",
      feature_extractors: this.feature_extractors.map((item) => item.toJsonValue()),
    };
  }
  public static fromJsonValue(value: JsonValue): RemoveFeatureExtractorsParamsDto | Error {
    return parse_as_RemoveFeatureExtractorsParamsDto(value);
  }
}

export function parse_as_Literal_of__quote_BOOT_FAIL_quote_0_quote_CANCELLED_quote_0_quote_COMPLETED_quote_0_quote_DEADLINE_quote_0_quote_FAILED_quote_0_quote_NODE_FAIL_quote_0_quote_OUT_OF_MEMORY_quote_0_quote_PENDING_quote_0_quote_PREEMPTED_quote_0_quote_RUNNING_quote_0_quote_REQUEUED_quote_0_quote_RESIZING_quote_0_quote_REVOKED_quote_0_quote_SUSPENDED_quote_0_quote_TIMEOUT_quote__endof_(
  value: JsonValue,
):
  | "BOOT_FAIL"
  | "CANCELLED"
  | "COMPLETED"
  | "DEADLINE"
  | "FAILED"
  | "NODE_FAIL"
  | "OUT_OF_MEMORY"
  | "PENDING"
  | "PREEMPTED"
  | "RUNNING"
  | "REQUEUED"
  | "RESIZING"
  | "REVOKED"
  | "SUSPENDED"
  | "TIMEOUT"
  | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "BOOT_FAIL") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "CANCELLED") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "COMPLETED") {
    return tmp_2;
  }
  const tmp_3 = parse_as_str(value);
  if (!(tmp_3 instanceof Error) && tmp_3 === "DEADLINE") {
    return tmp_3;
  }
  const tmp_4 = parse_as_str(value);
  if (!(tmp_4 instanceof Error) && tmp_4 === "FAILED") {
    return tmp_4;
  }
  const tmp_5 = parse_as_str(value);
  if (!(tmp_5 instanceof Error) && tmp_5 === "NODE_FAIL") {
    return tmp_5;
  }
  const tmp_6 = parse_as_str(value);
  if (!(tmp_6 instanceof Error) && tmp_6 === "OUT_OF_MEMORY") {
    return tmp_6;
  }
  const tmp_7 = parse_as_str(value);
  if (!(tmp_7 instanceof Error) && tmp_7 === "PENDING") {
    return tmp_7;
  }
  const tmp_8 = parse_as_str(value);
  if (!(tmp_8 instanceof Error) && tmp_8 === "PREEMPTED") {
    return tmp_8;
  }
  const tmp_9 = parse_as_str(value);
  if (!(tmp_9 instanceof Error) && tmp_9 === "RUNNING") {
    return tmp_9;
  }
  const tmp_10 = parse_as_str(value);
  if (!(tmp_10 instanceof Error) && tmp_10 === "REQUEUED") {
    return tmp_10;
  }
  const tmp_11 = parse_as_str(value);
  if (!(tmp_11 instanceof Error) && tmp_11 === "RESIZING") {
    return tmp_11;
  }
  const tmp_12 = parse_as_str(value);
  if (!(tmp_12 instanceof Error) && tmp_12 === "REVOKED") {
    return tmp_12;
  }
  const tmp_13 = parse_as_str(value);
  if (!(tmp_13 instanceof Error) && tmp_13 === "SUSPENDED") {
    return tmp_13;
  }
  const tmp_14 = parse_as_str(value);
  if (!(tmp_14 instanceof Error) && tmp_14 === "TIMEOUT") {
    return tmp_14;
  }
  return Error(
    `Could not parse ${value} as 'BOOT_FAIL' | 'CANCELLED' | 'COMPLETED' | 'DEADLINE' | 'FAILED' | 'NODE_FAIL' | 'OUT_OF_MEMORY' | 'PENDING' | 'PREEMPTED' | 'RUNNING' | 'REQUEUED' | 'RESIZING' | 'REVOKED' | 'SUSPENDED' | 'TIMEOUT'`,
  );
}
export function parse_as_ComputeSessionDto(value: JsonValue): ComputeSessionDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ComputeSessionDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ComputeSessionDto`);
  }
  const temp_start_time_utc_sec = parse_as_Union_of_int0None_endof_(valueObject.start_time_utc_sec);
  if (temp_start_time_utc_sec instanceof Error) return temp_start_time_utc_sec;
  const temp_time_elapsed_sec = parse_as_int(valueObject.time_elapsed_sec);
  if (temp_time_elapsed_sec instanceof Error) return temp_time_elapsed_sec;
  const temp_time_limit_minutes = parse_as_int(valueObject.time_limit_minutes);
  if (temp_time_limit_minutes instanceof Error) return temp_time_limit_minutes;
  const temp_num_nodes = parse_as_int(valueObject.num_nodes);
  if (temp_num_nodes instanceof Error) return temp_num_nodes;
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof Error) return temp_compute_session_id;
  const temp_state =
    parse_as_Literal_of__quote_BOOT_FAIL_quote_0_quote_CANCELLED_quote_0_quote_COMPLETED_quote_0_quote_DEADLINE_quote_0_quote_FAILED_quote_0_quote_NODE_FAIL_quote_0_quote_OUT_OF_MEMORY_quote_0_quote_PENDING_quote_0_quote_PREEMPTED_quote_0_quote_RUNNING_quote_0_quote_REQUEUED_quote_0_quote_RESIZING_quote_0_quote_REVOKED_quote_0_quote_SUSPENDED_quote_0_quote_TIMEOUT_quote__endof_(
      valueObject.state,
    );
  if (temp_state instanceof Error) return temp_state;
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
    | "DEADLINE"
    | "FAILED"
    | "NODE_FAIL"
    | "OUT_OF_MEMORY"
    | "PENDING"
    | "PREEMPTED"
    | "RUNNING"
    | "REQUEUED"
    | "RESIZING"
    | "REVOKED"
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
      | "DEADLINE"
      | "FAILED"
      | "NODE_FAIL"
      | "OUT_OF_MEMORY"
      | "PENDING"
      | "PREEMPTED"
      | "RUNNING"
      | "REQUEUED"
      | "RESIZING"
      | "REVOKED"
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
  public static fromJsonValue(value: JsonValue): ComputeSessionDto | Error {
    return parse_as_ComputeSessionDto(value);
  }
}

export function parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
  value: JsonValue,
): "LOCAL" | "CSCS" | "JUSUF" | Error {
  const tmp_0 = parse_as_str(value);
  if (!(tmp_0 instanceof Error) && tmp_0 === "LOCAL") {
    return tmp_0;
  }
  const tmp_1 = parse_as_str(value);
  if (!(tmp_1 instanceof Error) && tmp_1 === "CSCS") {
    return tmp_1;
  }
  const tmp_2 = parse_as_str(value);
  if (!(tmp_2 instanceof Error) && tmp_2 === "JUSUF") {
    return tmp_2;
  }
  return Error(`Could not parse ${value} as 'LOCAL' | 'CSCS' | 'JUSUF'`);
}
export function parse_as_bool(value: JsonValue): boolean | Error {
  return ensureJsonBoolean(value);
}
export function parse_as_ComputeSessionStatusDto(value: JsonValue): ComputeSessionStatusDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ComputeSessionStatusDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ComputeSessionStatusDto`);
  }
  const temp_compute_session = parse_as_ComputeSessionDto(valueObject.compute_session);
  if (temp_compute_session instanceof Error) return temp_compute_session;
  const temp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
    valueObject.hpc_site,
  );
  if (temp_hpc_site instanceof Error) return temp_hpc_site;
  const temp_session_url = parse_as_UrlDto(valueObject.session_url);
  if (temp_session_url instanceof Error) return temp_session_url;
  const temp_connected = parse_as_bool(valueObject.connected);
  if (temp_connected instanceof Error) return temp_connected;
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
  public hpc_site: "LOCAL" | "CSCS" | "JUSUF";
  public session_url: UrlDto;
  public connected: boolean;
  constructor(_params: {
    compute_session: ComputeSessionDto;
    hpc_site: "LOCAL" | "CSCS" | "JUSUF";
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
  public static fromJsonValue(value: JsonValue): ComputeSessionStatusDto | Error {
    return parse_as_ComputeSessionStatusDto(value);
  }
}

export function parse_as_CreateComputeSessionParamsDto(value: JsonValue): CreateComputeSessionParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CreateComputeSessionParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CreateComputeSessionParamsDto`);
  }
  const temp_session_duration_minutes = parse_as_int(valueObject.session_duration_minutes);
  if (temp_session_duration_minutes instanceof Error) return temp_session_duration_minutes;
  const temp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
    valueObject.hpc_site,
  );
  if (temp_hpc_site instanceof Error) return temp_hpc_site;
  return new CreateComputeSessionParamsDto({
    session_duration_minutes: temp_session_duration_minutes,
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for CreateComputeSessionParamsDto
// Do not edit!
export class CreateComputeSessionParamsDto {
  public session_duration_minutes: number;
  public hpc_site: "LOCAL" | "CSCS" | "JUSUF";
  constructor(_params: {
    session_duration_minutes: number;
    hpc_site: "LOCAL" | "CSCS" | "JUSUF";
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
  public static fromJsonValue(value: JsonValue): CreateComputeSessionParamsDto | Error {
    return parse_as_CreateComputeSessionParamsDto(value);
  }
}

export function parse_as_GetComputeSessionStatusParamsDto(value: JsonValue): GetComputeSessionStatusParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetComputeSessionStatusParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a GetComputeSessionStatusParamsDto`);
  }
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof Error) return temp_compute_session_id;
  const temp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
    valueObject.hpc_site,
  );
  if (temp_hpc_site instanceof Error) return temp_hpc_site;
  return new GetComputeSessionStatusParamsDto({
    compute_session_id: temp_compute_session_id,
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for GetComputeSessionStatusParamsDto
// Do not edit!
export class GetComputeSessionStatusParamsDto {
  public compute_session_id: string;
  public hpc_site: "LOCAL" | "CSCS" | "JUSUF";
  constructor(_params: {
    compute_session_id: string;
    hpc_site: "LOCAL" | "CSCS" | "JUSUF";
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
  public static fromJsonValue(value: JsonValue): GetComputeSessionStatusParamsDto | Error {
    return parse_as_GetComputeSessionStatusParamsDto(value);
  }
}

export function parse_as_CloseComputeSessionParamsDto(value: JsonValue): CloseComputeSessionParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CloseComputeSessionParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CloseComputeSessionParamsDto`);
  }
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof Error) return temp_compute_session_id;
  const temp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
    valueObject.hpc_site,
  );
  if (temp_hpc_site instanceof Error) return temp_hpc_site;
  return new CloseComputeSessionParamsDto({
    compute_session_id: temp_compute_session_id,
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for CloseComputeSessionParamsDto
// Do not edit!
export class CloseComputeSessionParamsDto {
  public compute_session_id: string;
  public hpc_site: "LOCAL" | "CSCS" | "JUSUF";
  constructor(_params: {
    compute_session_id: string;
    hpc_site: "LOCAL" | "CSCS" | "JUSUF";
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
  public static fromJsonValue(value: JsonValue): CloseComputeSessionParamsDto | Error {
    return parse_as_CloseComputeSessionParamsDto(value);
  }
}

export function parse_as_CloseComputeSessionResponseDto(value: JsonValue): CloseComputeSessionResponseDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CloseComputeSessionResponseDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CloseComputeSessionResponseDto`);
  }
  const temp_compute_session_id = parse_as_str(valueObject.compute_session_id);
  if (temp_compute_session_id instanceof Error) return temp_compute_session_id;
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
  public static fromJsonValue(value: JsonValue): CloseComputeSessionResponseDto | Error {
    return parse_as_CloseComputeSessionResponseDto(value);
  }
}

export function parse_as_ListComputeSessionsParamsDto(value: JsonValue): ListComputeSessionsParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListComputeSessionsParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ListComputeSessionsParamsDto`);
  }
  const temp_hpc_site = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(
    valueObject.hpc_site,
  );
  if (temp_hpc_site instanceof Error) return temp_hpc_site;
  return new ListComputeSessionsParamsDto({
    hpc_site: temp_hpc_site,
  });
}
// Automatically generated via DataTransferObject for ListComputeSessionsParamsDto
// Do not edit!
export class ListComputeSessionsParamsDto {
  public hpc_site: "LOCAL" | "CSCS" | "JUSUF";
  constructor(_params: {
    hpc_site: "LOCAL" | "CSCS" | "JUSUF";
  }) {
    this.hpc_site = _params.hpc_site;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "ListComputeSessionsParamsDto",
      hpc_site: this.hpc_site,
    };
  }
  public static fromJsonValue(value: JsonValue): ListComputeSessionsParamsDto | Error {
    return parse_as_ListComputeSessionsParamsDto(value);
  }
}

export function parse_as_Tuple_of_ComputeSessionStatusDto0_varlen__endof_(
  value: JsonValue,
): Array<ComputeSessionStatusDto> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<ComputeSessionStatusDto> = [];
  for (let item of arr) {
    let parsed_item = parse_as_ComputeSessionStatusDto(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_ListComputeSessionsResponseDto(value: JsonValue): ListComputeSessionsResponseDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListComputeSessionsResponseDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ListComputeSessionsResponseDto`);
  }
  const temp_compute_sessions_stati = parse_as_Tuple_of_ComputeSessionStatusDto0_varlen__endof_(
    valueObject.compute_sessions_stati,
  );
  if (temp_compute_sessions_stati instanceof Error) return temp_compute_sessions_stati;
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
  public static fromJsonValue(value: JsonValue): ListComputeSessionsResponseDto | Error {
    return parse_as_ListComputeSessionsResponseDto(value);
  }
}

export function parse_as_Tuple_of_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_0_varlen__endof_(
  value: JsonValue,
): Array<"LOCAL" | "CSCS" | "JUSUF"> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<"LOCAL" | "CSCS" | "JUSUF"> = [];
  for (let item of arr) {
    let parsed_item = parse_as_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_GetAvailableHpcSitesResponseDto(value: JsonValue): GetAvailableHpcSitesResponseDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetAvailableHpcSitesResponseDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a GetAvailableHpcSitesResponseDto`);
  }
  const temp_available_sites =
    parse_as_Tuple_of_Literal_of__quote_LOCAL_quote_0_quote_CSCS_quote_0_quote_JUSUF_quote__endof_0_varlen__endof_(
      valueObject.available_sites,
    );
  if (temp_available_sites instanceof Error) return temp_available_sites;
  return new GetAvailableHpcSitesResponseDto({
    available_sites: temp_available_sites,
  });
}
// Automatically generated via DataTransferObject for GetAvailableHpcSitesResponseDto
// Do not edit!
export class GetAvailableHpcSitesResponseDto {
  public available_sites: Array<"LOCAL" | "CSCS" | "JUSUF">;
  constructor(_params: {
    available_sites: Array<"LOCAL" | "CSCS" | "JUSUF">;
  }) {
    this.available_sites = _params.available_sites;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetAvailableHpcSitesResponseDto",
      available_sites: this.available_sites.map((item) => item),
    };
  }
  public static fromJsonValue(value: JsonValue): GetAvailableHpcSitesResponseDto | Error {
    return parse_as_GetAvailableHpcSitesResponseDto(value);
  }
}

export function parse_as_CheckLoginResultDto(value: JsonValue): CheckLoginResultDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CheckLoginResultDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CheckLoginResultDto`);
  }
  const temp_logged_in = parse_as_bool(valueObject.logged_in);
  if (temp_logged_in instanceof Error) return temp_logged_in;
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
  public static fromJsonValue(value: JsonValue): CheckLoginResultDto | Error {
    return parse_as_CheckLoginResultDto(value);
  }
}

export function parse_as_StartPixelProbabilitiesExportJobParamsDto(
  value: JsonValue,
): StartPixelProbabilitiesExportJobParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "StartPixelProbabilitiesExportJobParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a StartPixelProbabilitiesExportJobParamsDto`);
  }
  const temp_datasource =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.datasource,
    );
  if (temp_datasource instanceof Error) return temp_datasource;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof Error) return temp_datasink;
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
  public static fromJsonValue(value: JsonValue): StartPixelProbabilitiesExportJobParamsDto | Error {
    return parse_as_StartPixelProbabilitiesExportJobParamsDto(value);
  }
}

export function parse_as_StartSimpleSegmentationExportJobParamsDto(
  value: JsonValue,
): StartSimpleSegmentationExportJobParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "StartSimpleSegmentationExportJobParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a StartSimpleSegmentationExportJobParamsDto`);
  }
  const temp_datasource =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(
      valueObject.datasource,
    );
  if (temp_datasource instanceof Error) return temp_datasource;
  const temp_datasink = parse_as_Union_of_PrecomputedChunksSinkDto0N5DataSinkDto0DziLevelSinkDto_endof_(
    valueObject.datasink,
  );
  if (temp_datasink instanceof Error) return temp_datasink;
  const temp_label_header = parse_as_LabelHeaderDto(valueObject.label_header);
  if (temp_label_header instanceof Error) return temp_label_header;
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
  public static fromJsonValue(value: JsonValue): StartSimpleSegmentationExportJobParamsDto | Error {
    return parse_as_StartSimpleSegmentationExportJobParamsDto(value);
  }
}

export function parse_as_LoadProjectParamsDto(value: JsonValue): LoadProjectParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "LoadProjectParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a LoadProjectParamsDto`);
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.fs);
  if (temp_fs instanceof Error) return temp_fs;
  const temp_project_file_path = parse_as_str(valueObject.project_file_path);
  if (temp_project_file_path instanceof Error) return temp_project_file_path;
  return new LoadProjectParamsDto({
    fs: temp_fs,
    project_file_path: temp_project_file_path,
  });
}
// Automatically generated via DataTransferObject for LoadProjectParamsDto
// Do not edit!
export class LoadProjectParamsDto {
  public fs: OsfsDto | HttpFsDto | BucketFSDto;
  public project_file_path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): LoadProjectParamsDto | Error {
    return parse_as_LoadProjectParamsDto(value);
  }
}

export function parse_as_SaveProjectParamsDto(value: JsonValue): SaveProjectParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "SaveProjectParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a SaveProjectParamsDto`);
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.fs);
  if (temp_fs instanceof Error) return temp_fs;
  const temp_project_file_path = parse_as_str(valueObject.project_file_path);
  if (temp_project_file_path instanceof Error) return temp_project_file_path;
  return new SaveProjectParamsDto({
    fs: temp_fs,
    project_file_path: temp_project_file_path,
  });
}
// Automatically generated via DataTransferObject for SaveProjectParamsDto
// Do not edit!
export class SaveProjectParamsDto {
  public fs: OsfsDto | HttpFsDto | BucketFSDto;
  public project_file_path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): SaveProjectParamsDto | Error {
    return parse_as_SaveProjectParamsDto(value);
  }
}

export function parse_as_GetDatasourcesFromUrlParamsDto(value: JsonValue): GetDatasourcesFromUrlParamsDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetDatasourcesFromUrlParamsDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a GetDatasourcesFromUrlParamsDto`);
  }
  const temp_url = parse_as_UrlDto(valueObject.url);
  if (temp_url instanceof Error) return temp_url;
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
  public static fromJsonValue(value: JsonValue): GetDatasourcesFromUrlParamsDto | Error {
    return parse_as_GetDatasourcesFromUrlParamsDto(value);
  }
}

export function parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto0Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_0None_endof_(
  value: JsonValue,
):
  | PrecomputedChunksDataSourceDto
  | N5DataSourceDto
  | SkimageDataSourceDto
  | DziLevelDataSourceDto
  | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
  | undefined
  | Error {
  const parsed_option_0 = parse_as_PrecomputedChunksDataSourceDto(value);
  if (!(parsed_option_0 instanceof Error)) {
    return parsed_option_0;
  }
  const parsed_option_1 = parse_as_N5DataSourceDto(value);
  if (!(parsed_option_1 instanceof Error)) {
    return parsed_option_1;
  }
  const parsed_option_2 = parse_as_SkimageDataSourceDto(value);
  if (!(parsed_option_2 instanceof Error)) {
    return parsed_option_2;
  }
  const parsed_option_3 = parse_as_DziLevelDataSourceDto(value);
  if (!(parsed_option_3 instanceof Error)) {
    return parsed_option_3;
  }
  const parsed_option_4 =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      value,
    );
  if (!(parsed_option_4 instanceof Error)) {
    return parsed_option_4;
  }
  const parsed_option_5 = parse_as_None(value);
  if (!(parsed_option_5 instanceof Error)) {
    return parsed_option_5;
  }
  return Error(
    `Could not parse ${
      JSON.stringify(value)
    } into PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto> | undefined`,
  );
}
export function parse_as_GetDatasourcesFromUrlResponseDto(value: JsonValue): GetDatasourcesFromUrlResponseDto | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "GetDatasourcesFromUrlResponseDto") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a GetDatasourcesFromUrlResponseDto`);
  }
  const temp_datasources =
    parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto0Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_0None_endof_(
      valueObject.datasources,
    );
  if (temp_datasources instanceof Error) return temp_datasources;
  return new GetDatasourcesFromUrlResponseDto({
    datasources: temp_datasources,
  });
}
// Automatically generated via DataTransferObject for GetDatasourcesFromUrlResponseDto
// Do not edit!
export class GetDatasourcesFromUrlResponseDto {
  public datasources:
    | PrecomputedChunksDataSourceDto
    | N5DataSourceDto
    | SkimageDataSourceDto
    | DziLevelDataSourceDto
    | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
    | undefined;
  constructor(_params: {
    datasources:
      | PrecomputedChunksDataSourceDto
      | N5DataSourceDto
      | SkimageDataSourceDto
      | DziLevelDataSourceDto
      | Array<PrecomputedChunksDataSourceDto | N5DataSourceDto | SkimageDataSourceDto | DziLevelDataSourceDto>
      | undefined;
  }) {
    this.datasources = _params.datasources;
  }
  public toJsonValue(): JsonObject {
    return {
      "__class__": "GetDatasourcesFromUrlResponseDto",
      datasources: toJsonValue(this.datasources),
    };
  }
  public static fromJsonValue(value: JsonValue): GetDatasourcesFromUrlResponseDto | Error {
    return parse_as_GetDatasourcesFromUrlResponseDto(value);
  }
}

export function parse_as_CheckDatasourceCompatibilityParams(
  value: JsonValue,
): CheckDatasourceCompatibilityParams | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CheckDatasourceCompatibilityParams") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CheckDatasourceCompatibilityParams`);
  }
  const temp_datasources =
    parse_as_Tuple_of_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_0_varlen__endof_(
      valueObject.datasources,
    );
  if (temp_datasources instanceof Error) return temp_datasources;
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
  public static fromJsonValue(value: JsonValue): CheckDatasourceCompatibilityParams | Error {
    return parse_as_CheckDatasourceCompatibilityParams(value);
  }
}

export function parse_as_Tuple_of_bool0_varlen__endof_(value: JsonValue): Array<boolean> | Error {
  const arr = ensureJsonArray(value);
  if (arr instanceof Error) return arr;
  const out: Array<boolean> = [];
  for (let item of arr) {
    let parsed_item = parse_as_bool(item);
    if (parsed_item instanceof Error) return parsed_item;
    out.push(parsed_item);
  }
  return out;
}
export function parse_as_CheckDatasourceCompatibilityResponse(
  value: JsonValue,
): CheckDatasourceCompatibilityResponse | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "CheckDatasourceCompatibilityResponse") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a CheckDatasourceCompatibilityResponse`);
  }
  const temp_compatible = parse_as_Tuple_of_bool0_varlen__endof_(valueObject.compatible);
  if (temp_compatible instanceof Error) return temp_compatible;
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
  public static fromJsonValue(value: JsonValue): CheckDatasourceCompatibilityResponse | Error {
    return parse_as_CheckDatasourceCompatibilityResponse(value);
  }
}

export function parse_as_ListFsDirRequest(value: JsonValue): ListFsDirRequest | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListFsDirRequest") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ListFsDirRequest`);
  }
  const temp_fs = parse_as_Union_of_OsfsDto0HttpFsDto0BucketFSDto_endof_(valueObject.fs);
  if (temp_fs instanceof Error) return temp_fs;
  const temp_path = parse_as_str(valueObject.path);
  if (temp_path instanceof Error) return temp_path;
  return new ListFsDirRequest({
    fs: temp_fs,
    path: temp_path,
  });
}
// Automatically generated via DataTransferObject for ListFsDirRequest
// Do not edit!
export class ListFsDirRequest {
  public fs: OsfsDto | HttpFsDto | BucketFSDto;
  public path: string;
  constructor(_params: {
    fs: OsfsDto | HttpFsDto | BucketFSDto;
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
  public static fromJsonValue(value: JsonValue): ListFsDirRequest | Error {
    return parse_as_ListFsDirRequest(value);
  }
}

export function parse_as_ListFsDirResponse(value: JsonValue): ListFsDirResponse | Error {
  const valueObject = ensureJsonObject(value);
  if (valueObject instanceof Error) {
    return valueObject;
  }
  if (valueObject["__class__"] != "ListFsDirResponse") {
    return Error(`Could not deserialize ${JSON.stringify(valueObject)} as a ListFsDirResponse`);
  }
  const temp_files = parse_as_Tuple_of_str0_varlen__endof_(valueObject.files);
  if (temp_files instanceof Error) return temp_files;
  const temp_directories = parse_as_Tuple_of_str0_varlen__endof_(valueObject.directories);
  if (temp_directories instanceof Error) return temp_directories;
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
  public static fromJsonValue(value: JsonValue): ListFsDirResponse | Error {
    return parse_as_ListFsDirResponse(value);
  }
}
