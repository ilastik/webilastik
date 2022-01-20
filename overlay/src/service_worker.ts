import { Url } from "./util/parsed_url";


interface FetchEvent{
    ///...
    request: Request,
    respondWith: (response: Promise<Response>) => void,
}

type FetchEventListener = (event: FetchEvent) => void;
const addFetchListener = (self.addEventListener as (eventName: "fetch", listener: FetchEventListener) => void)

console.log("Registering service worker!!!")

// The activate handler takes care of cleaning up old caches.
self.addEventListener('activate', _ => {
    console.log("Claiming clients or whatever......");
    (self as any).clients.claim()
});


addFetchListener('fetch', async (event: FetchEvent) => {
    const ebrainsToken = "FIXME: grab token"
    const request = event.request;
    const url = Url.parse(request.url)
    if(
        ebrainsToken === undefined || //FIXME: we should probably prompt the user to log in?
        url.hostname !== "data-proxy.ebrains.eu" ||
        !url.path.raw.startsWith("/api/")
    ){
        event.respondWith(fetch(request))
        return
    }

    let newHeaders = new Headers(request.headers);
    newHeaders.append("Authorization", `Bearer ${ebrainsToken}`);
    let newRequest = new Request(request.url, {
        method: request.method,
        headers: newHeaders,
        body: request.body,
    })
    event.respondWith((async () => {
        const response = await fetch(newRequest)
        if(url.path.name == "stat" || request.method.toLowerCase() !== "get" || !response.ok){
            return await response
        }
        const response_payload = await response.json();
        const cscsObjectUrl = response_payload["url"]
        return await fetch(cscsObjectUrl)
    })());
});