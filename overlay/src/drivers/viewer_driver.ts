import { mat4, quat, vec3 } from "gl-matrix";

export interface IDataView{
    name: string,
    url: string,
}

export interface IViewerDriver{
    getViewportDrivers: () => Array<IViewportDriver>;
    getTrackedElement: () => HTMLElement;
    refreshView: (params: {name: string, url: string, similar_url_hint?: string, channel_colors?: vec3[]}) => void;
    onViewportsChanged?: (handler: () => void) => void;
    getDataViewOnDisplay(): IDataView | undefined;
}

export interface IDataSourceScale{
    url: string;
    resolution: vec3;
}

//TThe dimensions and offset of a viewport within a viewer, measured in pixels
export interface IViewportGeometry{
    left: number;
    bottom: number;
    width: number;
    height: number;
}

export interface IViewportInjectionParams{
    precedingElement?: HTMLElement;
    zIndex?: string
}

// A viewer can be broken down into multiple viewports, that is, multiple non-overlapping
// mini-screens within the main view where it can show the same data, but from different angles or
// with different viewing options. A IViewerDriver should provide as many of these viewport drivers
// as there are "brushable" viewports in the viewer.
//
// The reason to have multiple IVewportDriver instead of simply having multiple IViewerDrivers
// is that by splitting a single canvas into multiple viewports it is possible to have a single webgl
// context be shared between them.
export interface IViewportDriver{
    getGeometry(): IViewportGeometry;
    //gets camera pose in data space, measured in Nm (NOT in fines-voxel-units)
    getCameraPoseInUvwSpace(): {position_uvw: vec3, orientation_uvw: quat};
     //get a mat4 tjat converts from voxel to worlkd space. Scaling part must have at least one axis set to 1
    getUvwToWorldMatrix(): mat4;
     //orthogonal zoom; must be positive. Describes how many pixels (the smallest dimension of) the voxel should occupy on screen
    getZoomInPixelsPerNm(): number;
    snapCameraTo?: (voxel_position: vec3, orientation: quat) => any;
    getInjectionParams?: () => IViewportInjectionParams
}
