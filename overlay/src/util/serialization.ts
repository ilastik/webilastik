export type JsonLeafValue = number | string | boolean | null

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
    return typeof value == "number" || typeof value == "string" || value === null
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

export function ensureJsonBoolean(value: JsonValue): boolean{
    if(typeof(value) !== "boolean"){
        throw `Expected boolean, found ${JSON.stringify(value)}`
    }
    return value
}

export function ensureJsonNumber(value: JsonValue): number{
    if(typeof(value) !== "number"){
        throw `Expected number, found ${JSON.stringify(value)}`
    }
    return value
}

export function ensureJsonString(value: JsonValue): string{
    if(typeof(value) !== "string"){
        throw `Expected number, found ${JSON.stringify(value)}`
    }
    return value
}

export function ensureJsonObject(value: JsonValue): JsonObject{
    if(!isJsonableObject(value)){
        throw `Expected JSON object, found this: ${JSON.stringify(value)}`
    }
    return value
}

export function ensureJsonArray(value: JsonValue): JsonArray{
    if(!isJsonableArray(value)){
        throw `Expected JSON object, found this: ${JSON.stringify(value)}`
    }
    return value
}

export function ensureJsonNumberTripplet(value: JsonValue): [number, number, number]{
    let number_array = ensureJsonArray(value).map(element => ensureJsonNumber(element))
    if(number_array.length != 3){
        throw Error(`Expected number tripplet, found this: ${JSON.stringify(value)}`)
    }
    return [number_array[0], number_array[1], number_array[2]]
}
