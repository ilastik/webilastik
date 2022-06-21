import { mat4 } from "gl-matrix";
import { BrushStroke } from "../../..";
import { Color } from "../../../client/ilastik";
import { RenderParams } from "../../../gl/gl";
import { Camera } from "./camera";

export interface BrushRenderer{
    render: (params: {
        brush_strokes: Array<[Color, BrushStroke[]]>,
        camera: Camera,
        voxelToWorld: mat4,
        renderParams?: RenderParams
    }) => void,
}
