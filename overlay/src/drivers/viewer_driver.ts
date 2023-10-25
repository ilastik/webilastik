import { quat, vec3 } from "gl-matrix";
import { EbrainsAccessTokenDto } from "../client/dto";
import { Color } from "../client/ilastik";
import { Mat4, Quat, Vec3 } from "../util/ooglmatrix";
import { Url } from "../util/parsed_url";

/**
 * A data source from a viewer. Usually
 */
export interface INativeView{
    getName(): unknown;
    // getName(): string
    // getUrl(): Url
    // getOpacity(): number
    // getVisible(): boolean
    // setVisible(visible: boolean): void
    close(): void;
    reconfigure(params: {
        url?: Url,
        isVisible?: boolean,
        channelColors?: Color[],
        opacity?: number,
    }): void;
    // setProperties(props: {name?: string, opacity?: number, visible?: boolean}): void;
}

/**
 * Represents glue code with Basic functionality that any viewer must implement to be able to be used by
 * the ilastik overlay.
 */
export interface IViewerDriver{
    /**
     * @returns an array of all viewport drivers corresponding to the currently visible
     * viewports of the viewer. See IViewportDriver for more details
     */
    getViewportDrivers: () => Array<IViewportDriver>;
    /**
     * @returns the HTML element that is actually displaying the data pixels in the viewer.
     * This element is "tracked" by the ilastik overlay, i.e., the overlay stays on floating
     * on top of the tracked element and forces itself to have the same size as the tracked element
     */
    getTrackedElement: () => HTMLElement;

    setUserToken: (token: EbrainsAccessTokenDto) => void;

    openUrl(params: {
        name: string,
        url: Url,
        isVisible: boolean,
        channelColors?: Color[],
        opacity?: number,
    }): Promise<INativeView | Error>;

    enable3dNavigation(enable: boolean): void;
    addViewportsChangedHandler: (handler: () => void) => void;
    removeViewportsChangedHandler: (handler: () => void) => void;
    getContainerForWebilastikControls: () => HTMLElement | undefined;
    snapTo?: (params: {position_w: Vec3<"world">, orientation_w: Quat<"world">}) => void;
}

/**
 * A description of a viewport's offset and geometry relative to the entirety of the display area; analogous to a WebGl viewport
 */
export class ViewportGeometry{
    public readonly left: number
    public readonly bottom  : number
    public readonly width   : number
    public readonly height  : number
    constructor(params: {
        left: number;
        bottom: number;
        width: number;
        height: number;
    }){
        this.left = params.left
        this.bottom = params.bottom
        this.width = params.width
        this.height = params.height
    }

    public equals(other: ViewportGeometry): boolean{
        return (
            this.left == other.left &&
            this.bottom == other.bottom &&
            this.width == other.width &&
            this.height == other.height
        )
    }
}

/**
 * Hints on how to inject the overlay div that captures mouse events into the DOM
 */
export class ViewportInjectionParams{
    public readonly precedingElement?: HTMLElement;
    public readonly zIndex?: string
    public constructor(params: {
        precedingElement?: HTMLElement;
        zIndex?: string
    }){
        this.precedingElement = params.precedingElement
        this.zIndex = params.zIndex
    }

    public equals(other: ViewportInjectionParams){
        return (
            this.precedingElement == other.precedingElement &&
            this.zIndex == other.zIndex
        )
    }
}

/**
 * A viewer can be broken down into multiple viewports, that is, multiple non-overlapping
 * mini-screens within the main view where it can show the same data, but from different angles or
 * with different viewing options. An IViewerDriver should provide as many of these viewport drivers
 * as there are "brushable" viewports in the viewer.
 *
 * The reason to have multiple IVewportDriver instead of simply having multiple IViewerDrivers
 * is that by splitting a single canvas into multiple viewports it is possible to have a single webgl
 * context be shared between them.
 */
export interface IViewportDriver{
    getGeometry(): ViewportGeometry;

    getCameraPose(): {position: Vec3<"world">, orientation: Quat<"world">};

    getVoxelToWorldMatrix(params: {voxelSizeInNm: vec3}): Mat4<"voxel", "world">;

    getZoomInWorldUnitsPerPixel(): number;

    /**
     * Moves the viewport camera over to pose
     *
     * @param pose.voxel_position_uvw - position to snap to, in data space
     * @param pose.voxel_orientation_uvw - orientation to snap to, in data space
     */
    snapCameraTo?: (pose: {voxel_position_uvw: vec3, orientation_uvw: quat}) => any;
    getInjectionParams: () => ViewportInjectionParams
}
