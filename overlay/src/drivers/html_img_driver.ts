import { vec3, quat, mat4 } from "gl-matrix";
import { IViewerDriver } from "..";
import { createElement } from "../util/misc";
import { Url } from "../util/parsed_url";
import { INativeView, IViewportDriver, IViewportGeometry } from "./viewer_driver";
import { PredictionsView, View } from "../viewer/view";

export class HtmlImgDriver implements IViewerDriver{
    public readonly img: HTMLImageElement;
    public readonly container: HTMLElement;
    public readonly data_url: Url;

    private onViewportChangedHandlers = new Array<() => void>()

    constructor({img}:{img: HTMLImageElement}){
        this.img = img
        this.container = img.parentElement || document.body
        try{
            this.data_url = Url.parse(this.img.src)
        }catch{
            this.data_url = Url.parse(window.location.href).joinPath(this.img.src)
        }
    }
    public getViewportDrivers() : Array<HtmlImgViewportDriver>{
        return [new HtmlImgViewportDriver(this.img)]
    }
    public getTrackedElement(): HTMLImageElement{
        return this.img
    }
    public refreshView(params: {native_view: INativeView, similar_url_hint?: string, channel_colors?: vec3[]}){
        const output_css_class = "ilastik_img_output_image"
        document.querySelectorAll("." + output_css_class).forEach(element => {
            const htmlElement = (element as HTMLElement)
            htmlElement.parentElement?.removeChild(htmlElement)
        })
        const container = createElement({tagName: "div", parentElement: this.img.parentElement!, cssClasses: [output_css_class]});

        (async () => {
            let view = View.tryFromNative(params.native_view)
            if(view === undefined){
                throw `Could not convert to view: ${JSON.stringify(params.native_view)}`
            }
            if(!(view instanceof PredictionsView)){
                return
            }
            const increment_x = 128 //FIXME
            const increment_y = 128 //FIXME
            for(let y=0; y<this.img.height; y += increment_y){
                let row = createElement({tagName: "div", parentElement: container})
                for(let x=0; x<this.img.width; x += increment_x){
                    let tile = createElement({tagName: "img", parentElement: row, inlineCss: {float: "left"}}) as HTMLImageElement
                    let x_end = Math.min(x + increment_x, this.img.width);
                    let y_end = Math.min(y + increment_y, this.img.height);
                    tile.width = x_end - x;
                    tile.height = y_end - y;
                    tile.src = view.getChunkUrl({
                        x: [x, x_end],
                        y: [y, y_end],
                        z: [0, 1]
                    })
                    .updatedWith({extra_search: new Map([["format", "png"]])})
                    .schemeless_raw
                }
            }
        })()
    }
    public getDataViewOnDisplay(): INativeView | undefined{
        return {name: this.data_url.name, url: this.data_url.schemeless_raw}
    }
    public onViewportsChanged(handler: () => void){
        this.onViewportChangedHandlers.push(handler)
    }
    public getOpenDataViews(): Array<INativeView>{
        return [
            {name: "FIXME", url: this.data_url.raw}
        ]
    }
}

export class HtmlImgViewportDriver implements IViewportDriver{
    private voxelToWorld = mat4.fromScaling(mat4.create(), vec3.fromValues(1, -1, -1))

    constructor(public readonly img: HTMLImageElement){
    }
    public getGeometry(): IViewportGeometry{
        return {left: 0, bottom: 0, height: this.img.height, width: this.img.width}
    }
    public getCameraPoseInUvwSpace(): {position_uvw: vec3, orientation_uvw: quat}{
        return {
            position_uvw: vec3.fromValues(this.img.width / 2, this.img.height / 2, 0),
            orientation_uvw: quat.create(),
        }
    }
    public getUvwToWorldMatrix(): mat4{
        return this.voxelToWorld
    }
    public getZoomInPixelsPerNm(): number{
        return 1
    }
}
