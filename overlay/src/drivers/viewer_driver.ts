import { mat4, quat, vec3 } from "gl-matrix";
import { Session, FsDataSource, Color } from "../client/ilastik";

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
        isVisible?: boolean,
        channelColors?: Color[],
        opacity?: number
    }): void;
    // setProperties(props: {name?: string, opacity?: number, visible?: boolean}): void;
}

export interface IRawDataView extends INativeView{
    readonly datasource: FsDataSource;
}

export interface IPredictionsView extends INativeView{
    readonly rawData: FsDataSource;

    reconfigure(params: {
        source?: {session: Session, classifierGeneration: number},
        isVisible?: boolean | undefined,
        channelColors?: Color[],
        opacity?: number
    }): void;
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

    openDataSource(params: {
        session: Session,
        datasource: FsDataSource,
        name: string,
        isVisible: boolean,
        channelColors?: Color[],
        opacity?: number,
    }): IRawDataView | Error;

    openPixelPredictions(params: {
        session: Session,
        rawData: FsDataSource,
        classifierGeneration: number,
        channelColors: Color[],
        opacity: number,
        isVisible: boolean,
        name: string,
    }): IPredictionsView | Error;
    enable3dNavigation(enable: boolean): void;
    addViewportsChangedHandler: (handler: () => void) => void;
    removeViewportsChangedHandler: (handler: () => void) => void;
    getContainerForWebilastikControls: () => HTMLElement | undefined;
    snapTo?: (params: {position_vx: vec3, orientation_w: quat, voxel_size_nm: vec3}) => void;
}

/**
 * A description of a viewport's offset and geometry relative to the entirety of the display area; analogous to a WebGl viewport
 */
export interface IViewportGeometry{
    left: number;
    bottom: number;
    width: number;
    height: number;
}

/**
 * Hints on how to inject the overlay div that captures mouse events into the DOM
 */
export interface IViewportInjectionParams{
    precedingElement?: HTMLElement;
    zIndex?: string
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
    getGeometry(): IViewportGeometry;

    /**
     * @returns the camera position and orientation in data space
     */
    getCameraPoseInUvwSpace(): {position_uvw: vec3, orientation_uvw: quat};

    /**
     * @returns a mat4 that converts from voxel to worlkd space. Scaling part must have at least one axis set to 1
     */
    getUvwToWorldMatrix(): mat4;

    /**
     * @returns orthogonal zoom; must be positive. Describes how many pixels (the smallest dimension of) one voxel should occupy on screen
     */
    getZoomInPixelsPerNm(): number;

    /**
     * Moves the viewport camera over to pose
     *
     * @param pose.voxel_position_uvw - position to snap to, in data space
     * @param pose.voxel_orientation_uvw - orientation to snap to, in data space
     */
    snapCameraTo?: (pose: {voxel_position_uvw: vec3, orientation_uvw: quat}) => any;
    getInjectionParams?: () => IViewportInjectionParams
}
