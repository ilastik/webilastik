import { vec3, mat4, quat } from "gl-matrix"
import { IViewportDriver, IViewerDriver } from "..";
import { Color } from "../client/ilastik";
import { CssClasses } from "../gui/css_classes";
import { Div } from "../gui/widgets/widget";
import { getElementContentRect } from "../util/misc";
import { Url } from "../util/parsed_url";

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

interface NgManagedLayer{}



class Layer{
    private managedLayer: any;
    private channelColors: Color[];
    private opacity: number;

    public constructor(params: {
        name: string,
        isVisible: boolean,
        channelColors: Color[],
        opacity: number,
        managedLayer: NgManagedLayer,
    }){
        this.managedLayer = params.managedLayer
        this.channelColors = params.channelColors
        this.opacity = params.opacity
        this.reconfigure({
            isVisible: params.isVisible, channelColors: params.channelColors, opacity: params.opacity
        })
    }

    public getName(): string{
        return this.managedLayer.name
    }

    public getHidden(): boolean{
        //a layer might be hidden but not really "visible", because it can be behind other opaque layers
        return !this.managedLayer.visible
    }

    public getVisible(): boolean{
        return !this.getHidden()
    }
    public setVisible(visible: boolean){
        this.managedLayer.setVisible(visible)
    }

    public getOpacity(): number{
        let opacity = this.managedLayer.layer?.opacity?.value
        return opacity === undefined ? 1 : opacity
    }

    public get fragmentShader(): string{
        return this.managedLayer.layer.fragmentMain.value
    }

    public set fragmentShader(shader: string){
        this.managedLayer.layer.fragmentMain.value = shader
    }

    public getUrl(): Url{
        const rawUrl = this.managedLayer.sourceUrl.replace(/\bgs:\/\//, "https://storage.googleapis.com/")
        return Url.parse(rawUrl)
    }

    public async getNumChannels(): Promise<number>{
        return this.managedLayer.layer.multiscaleSource.then((mss: any) => mss.numChannels)
    }

    public async is3D(): Promise<boolean>{
        return this.managedLayer.layer.multiscaleSource.then((mss: any) => mss.scales[0].size[2] > 1)
    }

    public close(){
        this.managedLayer.manager.layerManager.removeManagedLayer(this.managedLayer)
    }

    public static makeShader({channelColors, opacity}: {channelColors: Array<Color>, opacity: number}): string{
        let color_lines = channelColors.map((color, idx) => {
            return `vec3 color${idx} = vec3(${color.vec3f[0]}, ${color.vec3f[1]}, ${color.vec3f[2]}) * toNormalized(getDataValue(${idx}));`
        })
        let colors_to_mix = channelColors.map((_, idx) => `color${idx}`)

        return [
            "void main() {",
            "    " + color_lines.join("\n    "),
            "    emit(",
            `        vec4(${colors_to_mix.join(' + ')}, ${opacity.toFixed(3)})`,
            "    );",
            "}",
        ].join("\n")
    }

    public reconfigure(params: {
        url?: Url,
        isVisible?: boolean,
        channelColors?: Color[],
        opacity?: number,
    }){
        this.channelColors = params.channelColors || this.channelColors
        this.opacity = params.opacity === undefined ? this.opacity : params.opacity

        let state = {...this.managedLayer.layer.toJSON()}
        if(params.url){
            state.url = params.url.double_protocol_raw
        }

        state.shader = Layer.makeShader({channelColors: this.channelColors, opacity: this.opacity})

        this.managedLayer.layer.restoreState(state)
        if(params.isVisible !== undefined){
            this.managedLayer.setVisible(params.isVisible)
        }
    }
}

// const defaultShader = 'void main() {\n  emitGrayscale(toNormalized(getDataValue()));\n}\n'

export class NeuroglancerDriver implements IViewerDriver{
    private containerForWebilastikControls: HTMLElement | undefined
    private readonly suppressMouseWheel = (ev: WheelEvent) => {
        if (!ev.ctrlKey && ev.target == document.querySelector('.neuroglancer-rendered-data-panel.neuroglancer-panel.neuroglancer-noselect')!){
            ev.stopPropagation();
            ev.stopImmediatePropagation();
        }
    }
    private trackedElement: HTMLElement;

    constructor(public readonly viewer: any){
        this.trackedElement = document.querySelector("#neuroglancer-container canvas")! //FIXME: double-check selector
    }

    getTrackedElement() : HTMLElement{
        return this.trackedElement
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

    public enable3dNavigation(enable: boolean): void{
        if(enable){
            window.removeEventListener("wheel", this.suppressMouseWheel, true)
        }else{
            window.addEventListener("wheel", this.suppressMouseWheel, true)
        }
    }
    public addViewportsChangedHandler(handler: () => void){
        this.viewer.display.changed.add(handler)
    }
    public removeViewportsChangedHandler(handler: () => void){
        this.viewer.display.changed.remove(handler)
    }
    public getContainerForWebilastikControls(): HTMLElement | undefined{
        if(!this.containerForWebilastikControls){
            let ngContainer = document.querySelector("#neuroglancer-container")! as HTMLElement;
            this.containerForWebilastikControls = new Div({
                parentElement: undefined,
                cssClasses: [CssClasses.ItkContainerForWebilastikControls]
            }).element
            ngContainer.parentElement!.insertBefore(this.containerForWebilastikControls, ngContainer)
        }
        return this.containerForWebilastikControls
    }

    public async openUrl(params: {
        url: Url,
        name: string,
        isVisible: boolean,
        channelColors: Color[],
        opacity: number,
    }): Promise<Layer | Error>{
        const managedLayer = this.viewer.layerSpecification.getLayer(
            params.name, {source: params.url.double_protocol_raw}
        );
        this.viewer.layerSpecification.add(managedLayer);
        return new Promise(resolve => {
            const waitUntilLayerExists = () => {
                if(managedLayer.layer){
                    console.log(`LAYER ${params.name} BECOMES READY!!!`)
                    this.removeViewportsChangedHandler(waitUntilLayerExists)
                    resolve(new Layer({...params, managedLayer}))
                }
            }
            this.addViewportsChangedHandler(waitUntilLayerExists)
        })
    }

    public snapTo(params: {position_vx: vec3, orientation_w: quat, voxel_size_nm: vec3}): void{
        this.viewer.navigationState.pose.restoreState({
            position: {
                voxelSize: Array.from(params.voxel_size_nm),
                spatialCoordinates: Array.from(
                    vec3.multiply(vec3.create(), params.position_vx, params.voxel_size_nm)
                ),
            },
            orientation: Array.from(params.orientation_w),
        })
    }
}
