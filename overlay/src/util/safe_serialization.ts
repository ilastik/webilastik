import { JsonValue, JsonObject, isJsonableObject, JsonArray, isJsonableArray } from "./serialization"


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