import { vec3, quat } from "gl-matrix"
import { IViewportDriver, IViewerDriver } from "..";
import { EbrainsAccessTokenDto } from "../client/dto";
import { Color } from "../client/ilastik";
import { CssClasses } from "../gui/css_classes";
import { Div } from "../gui/widgets/widget";
import { createElement, getElementContentRect } from "../util/misc";
import { Mat4, Quat, Vec3 } from "../util/ooglmatrix";
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
    public getCameraPose = (): {position: Vec3<"world">, orientation: Quat<"world">} => {
        const orientation_uvw = new Quat<"voxel">(quat.multiply(
            quat.create(), this.viewer.navigationState.pose.orientation.orientation, this.orientation_offset
        ))
        const position_uvw = new Vec3<"voxel">(
            vec3.clone(this.viewer.navigationState.pose.position.value)
        )

        let uvw_to_w = this.getVoxelToWorldMatrix({voxelSizeInNm: this.viewer_driver.getUnitSize_nm()})

        let cameraPosition_w = position_uvw.transformedWith(uvw_to_w);
        let cameraOrientation_w = orientation_uvw.relativeToBase(uvw_to_w);

        return {position: cameraPosition_w, orientation: cameraOrientation_w}
    }
    public getVoxelToWorldMatrix(params: {voxelSizeInNm: vec3}): Mat4<"voxel", "world">{
        const voxelScale = this.viewer_driver.getVoxelScale(params);
        const scaling: vec3 = vec3.mul(vec3.create(), voxelScale, vec3.fromValues(1, -1, -1));
        return Mat4.fromScaling(scaling)
    }
    public getZoomInWorldUnitsPerPixel(): number{
        return this.viewer.navigationState.zoomFactor.value //FIXME: maybe pick the smallest? idk
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
    private readonly suppressShiftPointermove = (ev: PointerEvent) => {
        if (ev.shiftKey && ev.target == document.querySelector('.neuroglancer-rendered-data-panel.neuroglancer-panel.neuroglancer-noselect')!){
            ev.stopPropagation();
            ev.stopImmediatePropagation();
        }
    }
    private trackedElement: HTMLElement;

    constructor(public readonly viewer: any){
        this.trackedElement = document.querySelector("#neuroglancer-container canvas")! //FIXME: double-check selector
    }

    public getUnitSize_nm(): vec3{
        //FIXME: couldn't the voxels be unisotropic?
        let length_in_nm = this.viewer.navigationState.zoomFactor.curCanonicalVoxelPhysicalSize * 1e9
        return vec3.fromValues(length_in_nm, length_in_nm, length_in_nm)
    }
    public getVoxelScale({voxelSizeInNm}: {voxelSizeInNm: vec3}): vec3{
        return vec3.div(vec3.create(), voxelSizeInNm, this.getUnitSize_nm());
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

    setUserToken(token: EbrainsAccessTokenDto): void{
        this.viewer.dataContext.worker.postMessage(token);
        window.postMessage(token);
    }

    getViewportDrivers(): Array<NeuroglancerViewportDriver>{
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
            window.removeEventListener("pointermove", this.suppressShiftPointermove, true)
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
            window.addEventListener("pointermove", this.suppressShiftPointermove, true)
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

    public snapTo(params: {position_w: Vec3<"world">, orientation_w: Quat<"world">}): void{
        const {position_w, orientation_w} = params;

        const worldToSmallestVoxel = Mat4.fromScaling(vec3.fromValues(1, -1, -1)).inverted() //FIXME?
        const viewer_pos = position_w.transformedWith(worldToSmallestVoxel) //viewer position is _not_ in world space

        this.viewer.navigationState.pose.position.restoreState([viewer_pos.x, viewer_pos.y, viewer_pos.z])
        this.viewer.navigationState.pose.orientation.restoreState(
            [orientation_w.raw[0], orientation_w.raw[1], orientation_w.raw[2], orientation_w.raw[3]]
        )
    }
}
