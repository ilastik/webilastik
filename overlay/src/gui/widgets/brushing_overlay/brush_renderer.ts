import { BrushStroke } from "../../..";
import { Color } from "../../../client/ilastik";
import { RenderParams } from "../../../gl/gl";
import { Mat4 } from "../../../util/ooglmatrix";
import { Camera } from "./camera";

export interface BrushRenderer{
    render: (params: {
        brush_strokes: Array<[Color, BrushStroke[]]>,
        camera: Camera,
        voxelToWorld: Mat4<"voxel", "world">,
        renderParams?: RenderParams
    }) => void,
}
