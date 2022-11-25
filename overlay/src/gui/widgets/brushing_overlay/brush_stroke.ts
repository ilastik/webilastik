import { quat, vec3 } from "gl-matrix";
import { Color, FsDataSource } from "../../../client/ilastik";
import { PixelAnnotationDto } from "../../../client/dto";
import { VecAttributeBuffer, BufferUsageHint } from "../../../gl/buffer";
import { VertexArray } from "../../../gl/vertex_primitives";
// import { vec3ToString } from "./utils";

export class BrushStroke extends VertexArray{
    public readonly camera_orientation: quat
    public num_points : number
    public readonly positions_buffer: VecAttributeBuffer<3, Float32Array>
    public readonly annotated_data_source: FsDataSource;

    private constructor({gl, points_vx, camera_orientation, annotated_data_source}: {
        gl: WebGL2RenderingContext,
        points_vx: vec3[], // points in "voxel-space" (i.e. cooridnates are pixel indices into the image array)
        camera_orientation: quat,
        annotated_data_source: FsDataSource,
    }){
        let data = new Float32Array(1024 * 3) // 1024 vec3's
        super(data)
        this.camera_orientation = quat.create(); quat.copy(this.camera_orientation, camera_orientation)
        this.annotated_data_source = annotated_data_source
        this.num_points = 0
        this.positions_buffer = new VecAttributeBuffer({gl, numComponents: 3, data, usageHint: BufferUsageHint.DYNAMIC_DRAW})
        points_vx.forEach(pt_vx => this.try_add_point_vx(pt_vx))
    }

    public static create({gl, start_postition_uvw, camera_orientation, annotated_data_source}: {
        gl: WebGL2RenderingContext,
        start_postition_uvw: vec3,
        camera_orientation: quat,
        annotated_data_source: FsDataSource,
    }): BrushStroke{
        const stroke = new BrushStroke({gl, points_vx: [], camera_orientation, annotated_data_source})
        stroke.try_add_point_uvw(start_postition_uvw)
        return stroke
    }

    public get resolution(): vec3{
        return this.annotated_data_source.spatial_resolution
    }

    private getLastVoxelRef() : vec3{
        return this.getVertRef(this.num_points - 1)
    }

    public interpolate_until_point_uvw(point_uvw: vec3){
        let point_vx = vec3.floor(vec3.create(), vec3.divide(vec3.create(), point_uvw, this.resolution))
        let previous_point_vx = this.getVertRef(this.num_points - 1)
        let delta_vx = vec3.subtract(vec3.create(), point_vx, previous_point_vx)
        let num_steps = Math.max(Math.abs(delta_vx[0]), Math.abs(delta_vx[1]), Math.abs(delta_vx[2]))

        let step_increment_vx = vec3.div(vec3.create(), delta_vx, vec3.fromValues(num_steps, num_steps, num_steps))
        for(let i=1; i < num_steps; i++){
            let interpolated_point_vx =  vec3.fromValues(
                Math.floor(previous_point_vx[0] + step_increment_vx[0] * i),
                Math.floor(previous_point_vx[1] + step_increment_vx[1] * i),
                Math.floor(previous_point_vx[2] + step_increment_vx[2] * i),
            )
            this.try_add_point_vx(interpolated_point_vx)
        }
        this.try_add_point_vx(point_vx) //Ensure last point is present
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
            gl, points_vx: message.points, camera_orientation, annotated_data_source
        })
    }
}

export type IStagingBrushStroke = {stroke: BrushStroke, color: Color}

export interface IBrushStrokeHandler{
    handleNewBrushStroke: (params: {start_position_uvw: vec3, camera_orientation_uvw: quat}) => BrushStroke,
    handleFinishedBrushStroke: (stagingStroke: BrushStroke) => any,
}
