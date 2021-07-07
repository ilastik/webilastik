import { mat4 } from "gl-matrix";
import { BrushStroke } from "../../..";
import { RenderParams } from "../../../gl/gl";
import { Camera } from "./camera";

export interface BrushRenderer{
    render: (params: {
        brush_strokes: Array<BrushStroke>,
        camera: Camera,
        voxelToWorld: mat4,
        renderParams?: RenderParams
    }) => void,
}
