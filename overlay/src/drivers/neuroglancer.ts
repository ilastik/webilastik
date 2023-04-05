import { vec3, mat4, quat } from "gl-matrix"
import { IViewportDriver, IViewerDriver } from "..";
import { Color } from "../client/ilastik";
import { CssClasses } from "../gui/css_classes";
import { Div } from "../gui/widgets/widget";
import { createElement, getElementContentRect } from "../util/misc";
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
        const position_uvw = vec3.scale(
            vec3.create(),
            ng_position_obj.value, this.viewer.navigationState.zoomFactor.curCanonicalVoxelPhysicalSize * 1e9
        )
        return {
            position_uvw: position_uvw as vec3,
            orientation_uvw: quat.normalize(orientation_uvw, orientation_uvw),
        }
    }
    public getUvwToWorldMatrix(): mat4{
        return mat4.fromScaling(mat4.create(), vec3.fromValues(1, -1, -1))
    }
    public getZoomInPixelsPerNm(): number{
        const finest_voxel_size_in_nm = this.viewer.navigationState.zoomFactor.curCanonicalVoxelPhysicalSize * 1e9
        const finest_voxels_per_viewport_pixel = this.viewer.navigationState.zoomFactor.value
        const nm_per_viewport_pixel = finest_voxel_size_in_nm * finest_voxels_per_viewport_pixel;

        //FIXME: check if this is acually in Nm and not in finest-voxel-units
        return 1 / nm_per_viewport_pixel
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
    private channelColors: Color[];
    private opacity: number;
    private viewerDriver: NeuroglancerDriver;
    private readonly name: string;

    public constructor(params: {
        name: string,
        isVisible: boolean,
        channelColors: Color[],
        opacity: number,
        viewerDriver: NeuroglancerDriver,
    }){
        this.name = params.name
        this.channelColors = params.channelColors
        this.opacity = params.opacity
        this.viewerDriver = params.viewerDriver
        this.reconfigure({
            isVisible: params.isVisible, channelColors: params.channelColors, opacity: params.opacity
        })
    }

    public getState(): LayerRawState{
        return this.viewerDriver.getState().layers.find(ls => ls.name == this.name)!
    }

    public getName(): string{
        return this.name
    }

    public setVisible(visible: boolean){
        this.reconfigure({isVisible: visible})
    }

    public getManagedLayer(): any{
        return this.viewerDriver.getManagedLayer(this.name)
    }

    public async getNumChannels(): Promise<number>{
        return this.getManagedLayer().layer.multiscaleSource.then((mss: any) => mss.numChannels)
    }

    public close(){
        // from neuroglancer/layer.ts
        const managedLayer = this.getManagedLayer()
        if (!managedLayer || managedLayer.wasDisposed){
            return;
        }
        for (const layerManager of managedLayer.containers) {
          layerManager.removeManagedLayer(managedLayer);
        }
    }

    public static makeShader({channelColors, opacity}: {channelColors: Array<Color>, opacity: number}): string{
        let color_lines = channelColors.map((color, idx) => {
            return `vec3 color${idx} = vec3(${color.vec3f[0]}, ${color.vec3f[1]}, ${color.vec3f[2]}) * toNormalized(getDataValue(${idx}));`
        })
        let colors_to_mix = channelColors.map((_, idx) => `color${idx}`)

        return [
            "void main() {",
            "    " + color_lines.join("\n    "),
            "    emitRGBA(",
            `        vec4(${colors_to_mix.join(' + ')}, ${opacity.toFixed(3)})`,
            `        //vec4(${colors_to_mix.join(' + ')}, 1.0)`,
            `        //${colors_to_mix.join(' + ')}`,
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
        this.opacity = params.opacity === undefined ? this.opacity : params.opacity;



        let viewerState = this.viewerDriver.getState()
        let layerState = viewerState.layers.find(l => l.name == this.name)!
        if(params.url){
            layerState.url = params.url.double_protocol_raw
        }

        layerState.shader = Layer.makeShader({channelColors: this.channelColors, opacity: this.opacity})
        console.log(`This is the actual shader I wanted to use: \n ${layerState.shader}`)
        if(params.isVisible !== undefined){
            layerState.visible = params.isVisible
        }
        this.viewerDriver.setState(viewerState)
    }
}

// const defaultShader = 'void main() {\n  emitGrayscale(toNormalized(getDataValue()));\n}\n'

type LayerRawState = {
    name: string,
    url: string,
    visible?: boolean,
    shader?: string,
}

interface ViewerState{
    layers: Array<LayerRawState>
}

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

    getState(): ViewerState{
        return this.viewer.state.toJSON()
    }

    getManagedLayer(name: string): any{
        return this.viewer.layerManager.managedLayers.find((ml: any) => ml.name == name)
    }

    setState(state: ViewerState){
        this.viewer.state.restoreState(state)
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
        const styleElementClassName = "neuroglancer_driver__hide_layout_controls";
        if(enable){
            window.removeEventListener("wheel", this.suppressMouseWheel, true)
            document.head.querySelector("." + styleElementClassName)?.remove()
        }else{
            createElement({
                tagName: "style",
                parentElement: document.head,
                cssClasses: [styleElementClassName],
                innerText: ".neuroglancer-data-panel-layout-controls{ display: none }"
            })
            this.viewer.layout.restoreState("xy")
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
        let viewerState = this.viewer.state.toJSON();
        viewerState.layers = viewerState.layers || [];
        viewerState.layers.push({
            type: "image",
            source: params.url.double_protocol_raw,
            tab: "rendering",
            opacity: 1,
            channelDimensions: {
              "c^": [1, ""] //FIXME: what does this do?
            },
            name: params.name,
            visible: params.isVisible,
        });

        this.setState(viewerState);
        return new Promise(resolve => {
            const waitUntilLayerExists = () => {
                if(this.getManagedLayer(params.name).layer){
                    console.log(`LAYER ${params.name} BECOMES READY!!!`)
                    this.removeViewportsChangedHandler(waitUntilLayerExists)
                    resolve(new Layer({...params, viewerDriver: this}))
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
