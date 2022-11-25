import { vec3, mat4, quat } from "gl-matrix"
import { IViewportDriver, IViewerDriver } from "..";
import { getElementContentRect } from "../util/misc";
import { Url } from "../util/parsed_url";
import { INativeView } from "./viewer_driver";

type NeuroglancerLayout = "4panel" | "xy" | "xy-3d" | "xz" | "xz-3d" | "yz" | "yz-3d";

export class NeuroglancerViewportDriver implements IViewportDriver{
    private viewer: any
    constructor(
        public readonly viewer_driver: NeuroglancerDriver,
        public readonly panel: HTMLElement,
        private readonly orientation_offset: quat,
    ){
        this.viewer = viewer_driver.viewer
    }
    public getCameraPoseInUvwSpace = () => {
        const orientation_uvw = quat.multiply(
            quat.create(), this.viewer.navigationState.pose.orientation.orientation, this.orientation_offset
        )
        const ng_position_obj = this.viewer.navigationState.pose.position
        //old neuroglancers do not have the "value" key
        //FIXME: check if this is in Nm and not finest-voxel-space
        const position_uvw = "value" in ng_position_obj ? ng_position_obj.value : ng_position_obj.spatialCoordinates
        return {
            position_uvw: position_uvw as vec3,
            orientation_uvw: quat.normalize(orientation_uvw, orientation_uvw),
        }
    }
    public getUvwToWorldMatrix(): mat4{
        return mat4.fromScaling(mat4.create(), vec3.fromValues(1, -1, -1))
    }
    public getZoomInPixelsPerNm(): number{
        //FIXME: check if this is acually in Nm and not in finest-voxel-units
        return 1 / this.viewer.navigationState.zoomFactor.value
    }
    public getGeometry = () => {
        const panelContentRect = getElementContentRect(this.panel)
        const trackedElementRect = getElementContentRect(this.viewer_driver.getTrackedElement())
        return {
            left: panelContentRect.left - trackedElementRect.left,
            bottom: panelContentRect.bottom - trackedElementRect.bottom,
            width: panelContentRect.width,
            height: panelContentRect.height,
        }
    }
    public getInjectionParams = () => ({
        precedingElement: this.panel,
        // zIndex: 10
    })
}

class Layer{
    constructor(private readonly managedLayer: any){
        if(managedLayer.layer === undefined){
            throw `UNDEFINED LAYER!`
        }
    }

    public get name(): string{
        return this.managedLayer.name
    }

    public get hidden(): boolean{
        //a layer might be hidden but not really "visible", because it can be behind other opaque layers
        return !this.managedLayer.visible
    }

    public get fragmentShader(): string{
        return this.managedLayer.layer.fragmentMain.value
    }

    public set fragmentShader(shader: string){
        this.managedLayer.layer.fragmentMain.value = shader
    }

    public get sourceUrl(): string{
        return this.managedLayer.sourceUrl.replace(/\bgs:\/\//, "https://storage.googleapis.com/")
    }

    public async getNumChannels(): Promise<number>{
        return this.managedLayer.layer.multiscaleSource.then((mss: any) => mss.numChannels)
    }
}

const defaultShader = 'void main() {\n  emitGrayscale(toNormalized(getDataValue()));\n}\n'

export class NeuroglancerDriver implements IViewerDriver{
    private generation = 0

    constructor(public readonly viewer: any){
        this.guessShader()
        this.addDataChangedHandler(() => console.log("driver: Layers changed!"))
        this.addViewportsChangedHandler(() => console.log("driver: Viewports changed!"))
        this.addDataChangedHandler(this.guessShader)
    }

    private guessShader = async () => {
        const generation = this.generation += 1
        for(let layer of this.getImageLayers()){
            if(layer.fragmentShader != defaultShader){
                continue
            }
            let numChannels = await layer.getNumChannels()
            if(generation != this.generation){
                return
            }
            if(numChannels == 3){
                layer.fragmentShader = this.makePredictionsShader([
                    vec3.fromValues(255, 0, 0), vec3.fromValues(0, 255, 0), vec3.fromValues(0, 0, 255)
                ])
            }
        }
    }
    getTrackedElement() : HTMLElement{
        return document.querySelector("canvas")! //FIXME: double-check selector
    }
    getViewportDrivers(): Array<IViewportDriver>{
        const panels = Array(...document.querySelectorAll(".neuroglancer-panel")) as Array<HTMLElement>;
        if(panels.length == 0){
            return []
        }
        const layout: NeuroglancerLayout = this.viewer.state.toJSON()["layout"]
        const orientation_offsets = new Map<string, quat>([
            ["xy", quat.create()],
            ["xz", quat.setAxisAngle(quat.create(), vec3.fromValues(1, 0, 0), Math.PI / 2)], // FIXME
            ["yz", quat.setAxisAngle(quat.create(), vec3.fromValues(0, 1, 0), Math.PI / 2)],//FIXME
        ])
        if(layout == "4panel" && panels.length == 4){ //the layout switches name to '4panel' even without the panels being created
            console.log("Detected 4panel layout!s!")
            return [
                new NeuroglancerViewportDriver(this, panels[0], orientation_offsets.get("xy")!),
                new NeuroglancerViewportDriver(this, panels[1], orientation_offsets.get("xz")!),
                new NeuroglancerViewportDriver(this, panels[3], orientation_offsets.get("yz")!),
            ]
        }
        return [new NeuroglancerViewportDriver(this, panels[0], orientation_offsets.get(layout.replace("-3d", ""))!)]
    }

    public addViewportsChangedHandler(handler: () => void){
        this.viewer.display.changed.add(handler)
    }
    public removeViewportsChangedHandler(handler: () => void){
        this.viewer.display.changed.remove(handler)
    }

    public addDataChangedHandler(handler: () => void){
        this.viewer.layerManager.layersChanged.add(handler)
    }
    public removeDataChangedHandler(handler: () => void){
        this.viewer.layerManager.layersChanged.remove(handler)
    }

    refreshView(params: {native_view: INativeView, similar_url_hint?: string, channel_colors?: vec3[]}){
        let shader: string | undefined = undefined;
        let similar_url_hint = params.similar_url_hint && Url.parse(params.similar_url_hint).double_protocol_raw
        if(params.channel_colors !== undefined){
            shader = this.makePredictionsShader(params.channel_colors)
        }else if(similar_url_hint !== undefined){
            const similar_layers = this.getImageLayers().filter(layer => layer.sourceUrl == similar_url_hint)
            if(similar_layers.length > 0){
                shader = similar_layers[0].fragmentShader
            }
        }
        this.refreshLayer({name: params.native_view.name, url: params.native_view.url, shader})
    }

    closeView(params: { native_view: INativeView; }){
        this.dropLayer(params.native_view.name)
    }

    private refreshLayer({name, url, shader}: {name: string, url: string, shader?: string}){
        this.dropLayer(name)
        this.openNewDataSource({name, url: Url.parse(url).double_protocol_raw, shader})
    }

    private getLayerManager(): any {
        return this.viewer.layerSpecification.layerManager;
    }

    private dropLayer(name: string): boolean{
        const layerManager = this.getLayerManager();
        const predictionsLayer = layerManager.getLayerByName(name);

        if(predictionsLayer !== undefined){
            layerManager.removeManagedLayer(predictionsLayer);
            return true
        }
        return false
    }

    private openNewDataSource(params: {name: string, url: string, shader?: string}){
        const newPredictionsLayer = this.viewer.layerSpecification.getLayer(
            params.name,
            {source: Url.parse(params.url).double_protocol_raw, shader: params.shader}
        );
        this.viewer.layerSpecification.add(newPredictionsLayer);
    }

    private makePredictionsShader(channel_colors: Array<vec3>): string{
            let color_lines = channel_colors.map((c: vec3, idx: number) => {
                return `vec3 color${idx} = (vec3(${c[0]}, ${c[1]}, ${c[2]}) / 255.0) * toNormalized(getDataValue(${idx}));`
            })
            let colors_to_mix = channel_colors.map((_: vec3, idx: number) => `color${idx}`)

            return [
                "void main() {",
                "    " + color_lines.join("\n    "),
                "    emitRGBA(",
                `        vec4(${colors_to_mix.join(' + ')}, 1.0)`,
                "    );",
                "}",
            ].join("\n")
    }

    public getImageLayers() : Array<Layer>{
        return Array.from(this.viewer.layerManager.layerSet)
        .filter((managedLayer: any) => {
            return managedLayer.layer && managedLayer.layer.constructor.name == "ImageUserLayer" && managedLayer.sourceUrl //FIXME?
        })
        .map((managedLayer: any) : Layer => new Layer(managedLayer));
    }

    public getOpenDataViews(): Array<INativeView>{
        return this.getImageLayers().map(layer => ({name: layer.name, url: layer.sourceUrl}))
    }

    public getDataViewOnDisplay(): INativeView | undefined{
        return this.getImageLayers()
            .filter(layer => !layer.hidden)
            .map(layer => ({
                name: layer.name,
                url: layer.sourceUrl,
            }))[0];
    }

    public snapTo(pose: {position_uvw?: vec3, orientation_uvw?: quat}): void{
        if(pose.orientation_uvw !== undefined){
            this.viewer.navigationState.pose.position.setVoxelCoordinates(pose.position_uvw)
        }
        if(pose.orientation_uvw !== undefined){
            this.viewer.navigationState.pose.orientation.restoreState(pose.orientation_uvw)
        }
    }
}
