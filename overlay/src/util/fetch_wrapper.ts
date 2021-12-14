/**While there is no alternative solution to authenticating with the data proxy,
 * I'll be injecting token headers into requests done by neuroglancer
 * (and other 3rd party libs) when those go to the data-proxy.
 *
 * To do that, this file hijacks the `fetch` function
 *
 * https://stackoverflow.com/questions/45425169/intercept-fetch-api-requests-and-responses-in-javascript
 */

import { Session } from "../client/ilastik";
import { Url } from "./parsed_url";

export {}

const __origFetch = window.fetch;
const hijackedFetch = async (input: RequestInfo, init?: RequestInit) => {
    const ebrainsToken = Session.getEbrainsToken()
    const url = Url.parse(typeof input === "string" ? input : input.destination)
    if(
        ebrainsToken === undefined || //FIXME: we should probably prompt the user to log in?
        url.hostname !== "data-proxy.ebrains.eu" ||
        !url.path.raw.startsWith("/api/buckets/") ||
        url.path.name == "stat" ||
        (init?.method !== undefined && init.method.toLowerCase() !== "get")
    ){
        return __origFetch(input, init);
    }
    const authHeaderName = "Authorization"
    const authHeaderValue = `Bearer ${ebrainsToken}`

    let headers: HeadersInit | undefined = init?.headers
    let fixedHeaders: HeadersInit
    if(headers === undefined){
        fixedHeaders = {[authHeaderName]: authHeaderValue}
    }else if(Array.isArray(headers)){
        fixedHeaders = [...headers, [authHeaderName, authHeaderValue]]
    }else if(headers instanceof Headers){
        fixedHeaders = [...headers.entries(), [authHeaderName, authHeaderValue]]
    }else{
        fixedHeaders = {...headers, [authHeaderName]: authHeaderValue}
    }

    const responsePromise = __origFetch(input, {...init, headers: fixedHeaders});
    const response = await responsePromise
    if(!response.ok){
        return responsePromise
    }
    const cscsObjectUrl = (await response.json())["url"]
    return fetch(cscsObjectUrl)
};

window.fetch = hijackedFetch
