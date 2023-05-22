import { quat, vec3 } from "gl-matrix";
import { Color, FsDataSource } from "../../../client/ilastik";
import { PixelAnnotationDto } from "../../../client/dto";
import { VecAttributeBuffer, BufferUsageHint } from "../../../gl/buffer";
import { VertexArray } from "../../../gl/vertex_primitives";
import { Quat, Vec3 } from "../../../util/ooglmatrix";
// import { vec3ToString } from "./utils";

export class BrushStroke extends VertexArray{
    public readonly camera_orientation: quat
    public num_points : number
    public readonly positions_buffer: VecAttributeBuffer<3, Float32Array>
    public readonly annotated_data_source: FsDataSource;

    private constructor({gl, points_uvw, camera_orientation, annotated_data_source}: {
        gl: WebGL2RenderingContext,
        points_uvw: vec3[], // points in "voxel-space" (i.e. cooridnates are pixel indices into the image array)
        camera_orientation: quat,
        annotated_data_source: FsDataSource,
    }){
        let data = new Float32Array(1024 * 3) // 1024 vec3's
        super(data)
        this.camera_orientation = quat.create(); quat.copy(this.camera_orientation, camera_orientation)
        this.annotated_data_source = annotated_data_source
        this.num_points = 0
        this.positions_buffer = new VecAttributeBuffer({gl, numComponents: 3, data, usageHint: BufferUsageHint.DYNAMIC_DRAW})
        points_uvw.forEach(pt_uvw => this.try_add_point_uvw(pt_uvw))
    }

    public static create({gl, start_postition_uvw, camera_orientation, annotated_data_source}: {
        gl: WebGL2RenderingContext,
        start_postition_uvw: vec3,
        camera_orientation: quat,
        annotated_data_source: FsDataSource,
    }): BrushStroke{
        const stroke = new BrushStroke({gl, points_uvw: [], camera_orientation, annotated_data_source})
        stroke.try_add_point_uvw(start_postition_uvw)
        return stroke
    }

    private getLastVoxelRef() : vec3{
        return this.getVertRef(this.num_points - 1)
    }

    public interpolate_until_point_uvw(point_uvw: Vec3<"voxel">){
        let previous_point_uvw = new Vec3<"voxel">(this.getVertRef(this.num_points - 1))
        let delta_uvw = point_uvw.minus(previous_point_uvw)
        let num_steps = delta_uvw.getMaxAbsCoord()

        let step_increment_uvw = delta_uvw.scale(1/num_steps)
        for(let i=1; i < num_steps; i++){
            let interpolated_point_uvw =  new Vec3<"voxel">(vec3.fromValues(
                Math.floor(previous_point_uvw.x + step_increment_uvw.x * i),
                Math.floor(previous_point_uvw.y + step_increment_uvw.y * i),
                Math.floor(previous_point_uvw.z + step_increment_uvw.z * i),
            ))
            this.try_add_point_uvw(interpolated_point_uvw.raw)
        }
        this.try_add_point_uvw(point_uvw.raw) //Ensure last point is present
    }

    public try_add_point_uvw(point_uvw: vec3): boolean{
        point_uvw = vec3.floor(vec3.create(), point_uvw);
        if(this.num_points > 0 && vec3.equals(this.getLastVoxelRef(), point_uvw)){
            return false
        }
        vec3.copy(this.getVertRef(this.num_points), point_uvw)
        this.positions_buffer.populate({
            dstByteOffset: this.num_points * point_uvw.length * Float32Array.BYTES_PER_ELEMENT,
            data: new Float32Array(point_uvw)
        })
        this.num_points += 1
        return true
    }

    public destroy(){
        this.positions_buffer.destroy()
    }

    public toDto(): PixelAnnotationDto{
        let raw_voxels: Array<[number, number, number]> = []
        for(let i=0; i<this.num_points; i++){
            let vert = this.getVertRef(i)
            raw_voxels.push([vert[0], vert[1], vert[2]])
        }

        return new PixelAnnotationDto({
            points: raw_voxels,
            raw_data: this.annotated_data_source.toDto(),
            // "camera_orientation": [
                // this.camera_orientation[0], this.camera_orientation[1], this.camera_orientation[2], this.camera_orientation[3],
            // ],

        })
    }

    public static fromDto(gl: WebGL2RenderingContext, message: PixelAnnotationDto): BrushStroke{
        //FIXME: better error checking
        let camera_orientation: quat;
        // if("camera_orientation" in message){
        //     let raw_camera_orientation = message["camera_orientation"] as Array<number>;
        //     camera_orientation = quat.fromValues(
        //         raw_camera_orientation[0], raw_camera_orientation[1], raw_camera_orientation[2], raw_camera_orientation[3]
        //     )
        // }else{
            camera_orientation = quat.create()
        // }
        let annotated_data_source = FsDataSource.fromDto(message.raw_data)
        return new BrushStroke({
            gl, points_uvw: message.points, camera_orientation, annotated_data_source
        })
    }
}

export type IStagingBrushStroke = {stroke: BrushStroke, color: Color}

export interface IBrushStrokeHandler{
    handleNewBrushStroke: (params: {start_position: Vec3<"voxel">, camera_orientation: Quat<"voxel">}) => BrushStroke,
    handleFinishedBrushStroke: (stagingStroke: BrushStroke) => any,
}
