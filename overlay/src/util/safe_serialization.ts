export type JsonLeafValue = number | string | boolean | null | undefined

export interface JsonObject{
    [key: string]: JsonValue
}

export type JsonArray = Array<JsonValue>

export type JsonValue = JsonLeafValue | JsonArray | JsonObject

//////////////////////////////

export interface IJsonable{
    toJsonValue(): JsonValue
}

export interface IJsonableObject{
    [key: string]: JsonableValue
}

export type JsonableArray = Array<JsonableValue>

export type JsonableValue = JsonValue | IJsonable | IJsonableObject | JsonableArray

///////////////////////////////////////////

export function toJsonValue(value: JsonableValue) : JsonValue{
    if(isJsonLeafValue(value)){
        return value
    }
    if(isJsonableArray(value)){
        return value.map((val : JsonableValue) => toJsonValue(val))
    }
    if(isJsonableObject(value)){
        let out : JsonObject = {}
        for(let key in value){
            out[key] = toJsonValue(value[key])
        }
        return out
    }
    return (value as IJsonable).toJsonValue()
}

///////////////////////////////////////////

export interface IDeserializer<T>{
    (data: JsonValue): T;
}

///////////////////////////////////////////

export function isJsonLeafValue(value: JsonableValue): value is JsonLeafValue{
    return typeof value == "number" || typeof value == "string" || typeof value == "boolean" || value === null || value === undefined
}

export function isJsonableArray(value: JsonableValue): value is JsonableArray{
    return value instanceof Array
}

export function isIJsonable(value: JsonableValue): value is IJsonable{
    return value !== null && typeof(value) == "object" && "toJsonValue" in value
}

export function isJsonableObject(value: JsonableValue): value is IJsonableObject{
    return typeof(value) == "object" && value != null && !isIJsonable(value)
}

/////////////////////////////////////////

export function ensureJsonUndefined(value: JsonValue): undefined | Error{
    if(value === undefined || value === null){ //FIXME? null AND undefined?
        return Error(`Expected boolean, found ${JSON.stringify(value)}`)
    }
    return undefined
}

export function ensureJsonBoolean(value: JsonValue): boolean | Error{
    if(typeof(value) !== "boolean"){
        return Error(`Expected boolean, found ${JSON.stringify(value)}`)
    }
    return value
}

export function ensureJsonNumber(value: JsonValue): number | Error{
    if(typeof(value) !== "number"){
        return Error(`Expected number, found ${JSON.stringify(value)}`)
    }
    return value
}

export function ensureJsonString(value: JsonValue): string | Error{
    if(typeof(value) !== "string"){
        return Error(`Expected string, found ${JSON.stringify(value)}`)
    }
    return value
}

export function ensureJsonObject(value: JsonValue): JsonObject | Error{
    if(!isJsonableObject(value)){
        return Error(`Expected JSON object, found this: ${JSON.stringify(value)}`)
    }
    return value
}

export function ensureJsonArray(value: JsonValue): JsonArray | Error{
    if(!isJsonableArray(value)){
        return Error(`Expected JSON array, found this: ${JSON.stringify(value)}`)
    }
    return value
}