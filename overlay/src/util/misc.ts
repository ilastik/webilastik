import { vec3, mat4, vec4, quat } from "gl-matrix";

export function project(out: vec3, v: vec3, onto: vec3){
    // a . b = |a| * |b| * cos(alpha)
    // if |b| == 1 -> a . b = |a| * cos(alpha) = projection_length
    vec3.normalize(out, onto)
    let projection_length = vec3.dot(v, out)
    vec3.scale(out, out, projection_length)
    return out
}

export function project_onto_plane(out: vec3, v: vec3, plane_ortho: vec3): vec3{
    let v_parallel_planeOrtho = out; project(v_parallel_planeOrtho, v, plane_ortho)
    vec3.sub(out, v, v_parallel_planeOrtho)
    return out
}

export function manualLookAt(out: mat4, eye: vec3, center: vec3, up: vec3): mat4{
    let cameraZ_w = vec3.create(); vec3.sub(cameraZ_w, center, eye); vec3.normalize(cameraZ_w, cameraZ_w); vec3.negate(cameraZ_w, cameraZ_w)
    let cameraY_w = vec3.create(); project_onto_plane(cameraY_w, up, cameraZ_w)
    let cameraX_w = vec3.create(); vec3.cross(cameraX_w, cameraY_w, cameraZ_w); vec3.normalize(cameraX_w, cameraX_w)

    var cam_to_world = mat4.fromValues( //column major
        cameraX_w[0], cameraX_w[1], cameraX_w[2], 0,
        cameraY_w[0], cameraY_w[1], cameraY_w[2], 0,
        cameraZ_w[0], cameraZ_w[1], cameraZ_w[2], 0,
                   0,            0,            0, 1,
    )

    mat4.invert(out, cam_to_world) // out = cam_to_world ^ -1 = world_to_cam
    return out
}

// type KnownKeys<T> = {
//     [K in keyof T]: string extends K ? never : number extends K ? never : K
// } extends { [_ in keyof T]: infer U } ? U : never;

export type InlineCss = Partial<Omit<
    CSSStyleDeclaration,
    "getPropertyPriority" | "getPropertyValue" | "item" | "removeProperty" | "setProperty"
>>

export interface CreateElementParams{
    tagName:string,
    parentElement:HTMLElement,
    innerHTML?:string,
    cssClasses?:Array<string>,
    inlineCss?: InlineCss,
    onClick?: (event: MouseEvent) => void,
}


export interface CreateInputParams extends Omit<CreateElementParams, "tagName">{
    inputType: string,
    parentElement:HTMLElement,
    value?:string,
    name?:string,
    disabled?:boolean,
    required?:boolean,
}

export function createElement({tagName, parentElement, innerHTML, cssClasses, inlineCss={}, onClick}: CreateElementParams): HTMLElement{
    const element = document.createElement(tagName);
    parentElement.appendChild(element)
    if(innerHTML !== undefined){
        element.innerHTML = innerHTML
    }
    (cssClasses || []).forEach(klass => {
        element.classList.add(klass)
    })
    if(onClick !== undefined){
        element.addEventListener('click', onClick)
    }
    applyInlineCss(element, inlineCss)
    return element
}

export function applyInlineCss(element: HTMLElement, inlineCss: InlineCss){
    for(let key in inlineCss){ //FIXME: remove any
        (element.style as any)[key] = inlineCss[key]
    }
}

export function insertAfter({reference, new_element}: {reference: HTMLElement, new_element: HTMLElement}){
    if(!reference.parentNode){
        throw `Element ${reference} has no parent node!`
    }
    reference.parentNode.insertBefore(new_element, reference.nextSibling);
}

export function createImage({src, parentElement, cssClasses, onClick}:
    {src:string, parentElement:HTMLElement, cssClasses?:Array<string>, onClick?: (event: MouseEvent) => void}
): HTMLImageElement{
    const image = <HTMLImageElement>createElement({tagName: 'img', cssClasses, parentElement, onClick});
    image.src = src
    return image
}


export function createInput(params : CreateInputParams): HTMLInputElement{
    const input = <HTMLInputElement>createElement({tagName:'input', ...params})
    input.type = params.inputType;
    if(params.value !== undefined){
        input.value = params.value
    }
    if(params.name !== undefined){
        input.name = params.name
    }
    if(params.required !== undefined){
        input.required = params.required
    }
    input.disabled = params.disabled ? true : false
    return input
}

export function createSelect({parentElement, values, name, onClick}:
    {parentElement:HTMLElement, values?: Map<string, string>, name?:string, onClick?: (event: MouseEvent) => void}
): HTMLSelectElement{
    const select = <HTMLSelectElement>createElement({tagName: 'select', parentElement, onClick})
    if(values !== undefined){
        values.forEach((value:string, displayValue:string) => {
            let option = <HTMLInputElement>createElement({tagName: 'option', innerHTML: displayValue, parentElement: select, onClick})
            option.value = value
        })
    }
    if(name !== undefined){
        select.name = name
    }
    return select
}

export function createOption({displayText, value, parentElement}:
    {displayText:string, value:string, parentElement:HTMLElement}
): HTMLOptionElement{
    let option = <HTMLOptionElement>createElement({tagName: 'option', parentElement, innerHTML: displayText})
    option.value = value
    return option
}

//Gets element geometry, with offsets relative to bottom-left of the screen
export function getElementContentRect(element: HTMLElement){
    let clientRect = element.getBoundingClientRect() //with border and padding

    let paddingLeft = parseInt(element.style.paddingLeft) || 0
    let paddingTop = parseInt(element.style.paddingTop) || 0
    let paddingRight = parseInt(element.style.paddingRight) || 0
    let paddingBottom = parseInt(element.style.paddingBottom) || 0

    let borderLeft = parseInt(element.style.borderLeft) || 0
    let borderTop = parseInt(element.style.borderTop) || 0
    let borderRight = parseInt(element.style.borderRight) || 0
    let borderBottom = parseInt(element.style.borderBottom) || 0

    return {
        width:  clientRect.width  - borderLeft - paddingLeft - paddingRight - borderRight,
        height: clientRect.height - borderTop - paddingTop - paddingBottom - borderBottom,
        left:   clientRect.left   + paddingLeft + borderLeft,
        //offset from bottom OF THE SCREEN
        bottom: document.documentElement.clientHeight - (clientRect.bottom - paddingBottom - borderBottom) //FIXME: horizontal scrollbar?
    }
}

//FIXME: this assumes overlay has no padding or border
export function coverContents({target, overlay, offsetLeft=0, offsetBottom=0, width, height}: {
    target: HTMLElement,
    overlay: HTMLElement,
    offsetLeft?: number,
    offsetBottom?: number,
    width?: number,
    height?: number,
}){
    let targetContentRect = getElementContentRect(target);
    overlay.style.position = "fixed"
    overlay.style.width =  (width !== undefined ? width : targetContentRect.width)  + "px"
    overlay.style.height = (height !== undefined ? height : targetContentRect.height) + "px"
    overlay.style.bottom = (targetContentRect.bottom + offsetBottom)    + "px"
    overlay.style.left =   (targetContentRect.left + offsetLeft)   + "px"
}



export function vec3ToRgb(value: vec3): string{
    return "rgb(" + value.map((c: number) => Math.floor(c * 255)).join(", ") + ")"
}

export function vecToString(value: Float32Array | Array<number>, decimals: number = 3): string{
    let axisNames = "xyzw";
    return Array.from(value).map((value, idx) => {
        const value_str = value >= 0 ? " " + value.toFixed(decimals) : value.toFixed(decimals);
        return axisNames[idx] + ": " + value_str
    }).join(", ")
}

function float_to_s(num: number){
    let base = "      "
    let out = num.toFixed(3)
    let leading_zeros =  base.slice(0, base.length - out.length)
    return leading_zeros + out
}

export function m4_to_s(m: mat4) : string{
    let columns = [
      m.slice(0,  4),
      m.slice(4,  8),
      m.slice(8,  12),
      m.slice(12,  16)
    ]

    let lines = []
    for(var line_idx of [0,1,2,3]){
        let line = []
        for(var col of columns){
            line.push(float_to_s(col[line_idx]))
        }
        lines.push(line)
    }
    let comma_sep_lines = lines.map((line) => line.join(", "))
    return comma_sep_lines.join("\n")
}

export function hexColorToVec3(color: string): vec3{
    let channels = color.slice(1).match(/../g)!.map(c => parseInt(c, 16) / 255)
    return vec3.fromValues(channels[0], channels[1], channels[2])
}

export function vec3ToHexColor(color: vec3): string{
    return "#" + Array.from(color).map((val) => {
        const val_str = Math.round(val * 255).toString(16)
        return val_str.length < 2 ? "0" + val_str : val_str
    }).join("")
}

export function vec3to4(v: vec3, w: number): vec4{
    return vec4.fromValues(v[0], v[1], v[2], w)
}

export function vec4to3(v: vec4): vec3{
    return vec3.fromValues(v[0], v[1], v[2])
}

export function vec3c(x: number, y: number, z: number): vec3{
    return vec3.fromValues(x,y,z)
}


export function vec4c(x: number, y: number, z: number, w: number): vec4{
    return vec4.fromValues(x,y,z, w)
}

export function vec3abs(v: vec3): vec3{
    return vec3c(Math.abs(v[0]), Math.abs(v[1]), Math.abs(v[2]))
}

export function vec4abs(v: vec4): vec4{
    return vec4c(Math.abs(v[0]), Math.abs(v[1]), Math.abs(v[2]), Math.abs(v[3]))
}

export function all(arr: Array<boolean>): boolean{
    for(let v of arr){
        if(!v){
            return false
        }
    }
    return true
}

export function lessThan<T extends vec3 | vec4>(a: T, b: T) : Array<boolean>{
    return Array.from(a).map((value, index) => value < b[index])
}

export function changeOrientationBase(orientation_current: quat, transform: mat4): quat{
    const rotation_axis_current = vec3.create();
    const rotation_rads = quat.getAxisAngle(rotation_axis_current, orientation_current)
    const rotation_axis_target = vec3.transformMat4(vec3.create(), rotation_axis_current, transform);
    return quat.setAxisAngle(quat.create(), rotation_axis_target, rotation_rads)
}

export function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

export function websocket_connect(url: string) : Promise<WebSocket>{
    return new Promise((resolve, reject) => {
        var socket = new WebSocket(url);
        socket.addEventListener("message", (event) => {
            console.log(`Received this websocket payload: ${event.data}`)
        })
        socket.onopen = () => resolve(socket);
        socket.onerror = (err) => reject(err);
    });
}

export type WebsocketPayload =  string | ArrayBufferLike | Blob | ArrayBufferView

export function sleep(ms: number){
    return new Promise(resolve => setTimeout(resolve, ms));
}

export function injectCss(url: URL){
    let link_element = createElement({tagName: "link", parentElement: document.head}) as HTMLLinkElement
    link_element.rel = "stylesheet"
    link_element.href = url.toString()
}

export function removeElement(element: HTMLElement){
    element.parentNode?.removeChild(element)
}

export function show_if_changed(key: string, value: any, suffix = ""){
    const str_value = JSON.stringify(value);
    if((window as any)[key] !== str_value){
        (window as any)[key] = str_value
        console.log(`===> ${key} is now ${str_value} ${suffix}`)
    }
}
