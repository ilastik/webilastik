import { vec3, quat, mat4 } from "gl-matrix";
import { IViewerDriver } from "..";
import { createElement } from "../util/misc";
import { ParsedUrl } from "../util/parsed_url";
import { PrecomputedChunks } from "../datasource/precomputed_chunks";
import { IDataView, IViewportDriver, IViewportGeometry } from "./viewer_driver";
import { HtmlImgSource } from "../datasource/html_img";

export class HtmlImgDriver implements IViewerDriver{
    public readonly img: HTMLImageElement;
    public readonly container: HTMLElement;
    public readonly data_url: ParsedUrl;
    constructor({img}:{img: HTMLImageElement}){
        this.img = img
        this.container = img.parentElement || document.body
        try{
            this.data_url = ParsedUrl.parse(this.img.src)
        }catch{
            this.data_url = ParsedUrl.parse(window.location.href).concat(this.img.src)
        }
    }
    public getViewportDrivers() : Array<HtmlImgViewportDriver>{
        return [new HtmlImgViewportDriver(this.img)]
    }
    public getTrackedElement(): HTMLImageElement{
        return this.img
    }
    public refreshView(view: {name: string, url: string, similar_url_hint?: string, channel_colors?: vec3[]}){
        const output_css_class = "ilastik_img_output_image"
        document.querySelectorAll("." + output_css_class).forEach(element => {
            const htmlElement = (element as HTMLElement)
            htmlElement.parentElement?.removeChild(htmlElement)
        })
        const container = createElement({tagName: "div", parentElement: this.img.parentElement!, cssClasses: [output_css_class]})
        const url = ParsedUrl.parse(view.url)

        if(HtmlImgSource.accepts(url)){
            return //FIXME
        }

        PrecomputedChunks.fromUrl(ParsedUrl.parse(view.url)).then(precomp_chunks => {
            const scale = precomp_chunks.scales[0]
            const increment = 128
            for(let y=0; y<this.img.height; y += increment){
                let row = createElement({tagName: "div", parentElement: container})
                for(let x=0; x<this.img.width; x += increment){
                    let tile = createElement({tagName: "img", parentElement: row, inlineCss: {float: "left"}}) as HTMLImageElement
                    let x_end = Math.min(x + increment, this.img.width);
                    let y_end = Math.min(y + increment, this.img.height);
                    tile.width = x_end - x;
                    tile.height = y_end - y;
                    tile.src = scale.getChunkUrl({
                        x: [x, x_end],
                        y: [y, y_end],
                        z: [0, 1]
                    })
                    .withAddedSearchParams(new Map([["format", "png"]]))
                    .href
                }
            }
        })
    }
    public getDataViewOnDisplay(): IDataView | undefined{
        return {name: this.data_url.name, url: this.data_url.href}
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
