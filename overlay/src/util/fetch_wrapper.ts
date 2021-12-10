/**While there is no alternative solution to authenticating with the data proxy,
 * I'll be injecting token headers into requests done by neuroglancer
 * (and other 3rd party libs) when those go to the data-proxy.
 *
 * To do that, this file hijacks the `fetch` function
 *
 * https://stackoverflow.com/questions/45425169/intercept-fetch-api-requests-and-responses-in-javascript
 */

import { Session } from "../client/ilastik";

export {}

const __origFetch = window.fetch;
const hijackedFetch = async (input: RequestInfo, init?: RequestInit) => {
    const ebrainsToken = Session.getEbrainsToken()
    //FIXME: we should probably prompt the user to log in?
    if(ebrainsToken === undefined){
        return __origFetch(input, init)
    }
    const requestedUrl: string = typeof input === "string" ? input : input.destination
    const authHeaderName = "Authorization"
    const authHeaderValue = `Bearer ${ebrainsToken}`
    if(requestedUrl.startsWith("https://data-proxy.ebrains.eu/api/")){
        init = init || {}
        let headers: HeadersInit | undefined = init.headers
        if(headers === undefined){
            init.headers = {[authHeaderName]: authHeaderValue}
        }else if(Array.isArray(headers)){
            headers.push([authHeaderName, authHeaderValue])
        }else if(headers instanceof Headers){
            headers.set(authHeaderName, authHeaderValue)
        }else{
            headers[authHeaderName] = authHeaderValue
        }
    }
    return __origFetch(input, init);
};

window.fetch = hijackedFetch