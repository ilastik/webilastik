import { quat, vec3 } from "gl-matrix";
import { DataSource } from "../../../client/ilastik";
import { Vec3AttributeBuffer, BufferUsageHint } from "../../../gl/buffer";
import { VertexArray } from "../../../gl/vertex_primitives";
import { ensureJsonObject, IJsonable, JsonObject, JsonValue} from "../../../util/serialization";
// import { vec3ToString } from "./utils";

export class BrushStroke extends VertexArray implements IJsonable{
    public readonly camera_orientation: quat
    public num_points : number
    public readonly color : vec3
    public readonly positions_buffer: Vec3AttributeBuffer
    public readonly annotated_data_source: DataSource;

    private constructor({gl, points_vx, color, camera_orientation, annotated_data_source}: {
        gl: WebGL2RenderingContext,
        points_vx: vec3[],
        color: vec3,
        camera_orientation: quat,
        annotated_data_source: DataSource,
    }){
        let data = new Float32Array(1024 * 3) // 1024 vec3's
        super(data)
        this.camera_orientation = quat.create(); quat.copy(this.camera_orientation, camera_orientation)
        this.annotated_data_source = annotated_data_source
        this.num_points = 0
        this.color = vec3.create(); vec3.copy(this.color, color)
        this.positions_buffer = new Vec3AttributeBuffer(gl, data, BufferUsageHint.DYNAMIC_DRAW)
        points_vx.forEach(pt_vx => this.try_add_point_vx(pt_vx))
    }

    public static create({gl, start_postition_uvw, color, camera_orientation, annotated_data_source}: {
        gl: WebGL2RenderingContext,
        start_postition_uvw: vec3,
        color: vec3,
        camera_orientation: quat,
        annotated_data_source: DataSource,
    }): BrushStroke{
        const stroke = new BrushStroke({gl, points_vx: [], color, camera_orientation, annotated_data_source})
        stroke.try_add_point_uvw(start_postition_uvw)
        return stroke
    }

    public get resolution(): vec3{
        return this.annotated_data_source.spatial_resolution
    }

    private getLastVoxelRef() : vec3{
        return this.getVertRef(this.num_points - 1)
    }

    public try_add_point_uvw(point_uvw: vec3): boolean{
        let point_vx = vec3.floor(vec3.create(), vec3.divide(vec3.create(), point_uvw, this.resolution))
        return this.try_add_point_vx(point_vx)
    }

    public try_add_point_vx(point_vx: vec3): boolean{
        if(this.num_points > 0 && vec3.equals(this.getLastVoxelRef(), point_vx)){
            return false
        }
        vec3.copy(this.getVertRef(this.num_points), point_vx)
        this.positions_buffer.populate({
            dstByteOffset: this.num_points * point_vx.length * Float32Array.BYTES_PER_ELEMENT,
            data: new Float32Array(point_vx)
        })
        this.num_points += 1
        return true
    }

    public destroy(){
        this.positions_buffer.destroy()
    }

    public toJsonValue(): JsonObject{
        let raw_voxels: Array<{x: number, y: number, z: number}> = []
        for(let i=0; i<this.num_points; i++){
            let vert = this.getVertRef(i)
            raw_voxels.push({x: vert[0], y: vert[1], z: vert[2]})
        }

        return {
            "voxels": raw_voxels,
            "color": {
                "r": Math.floor(this.color[0] * 255), //FIXME: rounding issues?
                "g": Math.floor(this.color[1] * 255),
                "b": Math.floor(this.color[2] * 255),
            },
            "raw_data": this.annotated_data_source.toJsonValue(),
            "camera_orientation": [
                this.camera_orientation[0], this.camera_orientation[1], this.camera_orientation[2], this.camera_orientation[3],
            ],
        }
    }

    public static fromJsonValue(gl: WebGL2RenderingContext, value: JsonValue): BrushStroke{
        let raw = ensureJsonObject(value)
        //FIXME: better error checking
        let voxels = (raw["voxels"] as Array<any>).map(v => vec3.fromValues(v["x"], v["y"], v["z"]));
        let raw_color = ensureJsonObject(raw["color"])
        let color = vec3.fromValues(
            raw_color["r"] as number / 255,  //FIXME: rounding issues?
            raw_color["g"]  as number / 255,
            raw_color["b"]  as number / 255,
        )
        let camera_orientation: quat;
        if("camera_orientation" in raw){
            let raw_camera_orientation = raw["camera_orientation"] as Array<number>;
            camera_orientation = quat.fromValues(
                raw_camera_orientation[0], raw_camera_orientation[1], raw_camera_orientation[2], raw_camera_orientation[3]
            )
        }else{
            camera_orientation = quat.create()
        }
        let annotated_data_source = DataSource.fromJsonValue(raw["raw_data"])
        return new BrushStroke({
            gl, points_vx: voxels, camera_orientation, color, annotated_data_source
        })
    }
}

export interface IBrushStrokeHandler{
    handleNewBrushStroke: (params: {start_position_uvw: vec3, camera_orientation_uvw: quat}) => BrushStroke,
    handleFinishedBrushStroke: (stroke: BrushStroke) => any,
}
