import { mat3, mat4 } from "gl-matrix"
import { BrushStroke } from "../../..";
import { VertexArrayObject, BufferUsageHint } from "../../../gl/buffer";
import { RenderParams } from "../../../gl/gl";
import { ShaderProgram, VertexShader, FragmentShader } from "../../../gl/shader";
import { TriangleArray } from "../../../gl/vertex_primitives";
import { BrushRenderer } from "./brush_renderer"
import { Camera } from "./camera"

enum X{
    RIGHT = 0.5,
    LEFT = -0.5,
}

enum Y{
    TOP = 0.5,
    BOTTOM = -0.5,
}

enum Z{
    BACK = 0.5,
    FRONT = -0.5, //forwards is -z like in the camera
}


/**
         +y (top)                            +---------+ (right, top, front)
        ^                                   /   top   /|
        |                                  /   face  / |
        |                                 +---------+  |
        |   (front)                       |   back  |  |
        |     -z                          |   face  |  /
        |   /                             |         | /
        |  /                              +---------+
        | /          (left, back, bottom)
        |/
        *-------------------> +x (right)
 */


/**
 * A cube of side 1, centered on 0,0,0
*/
export class Cube extends TriangleArray{
    constructor(){
        super(new Float32Array([
            // front face,
            X.RIGHT, Y.BOTTOM, Z.FRONT,
            X.LEFT,  Y.BOTTOM, Z.FRONT,
            X.LEFT,  Y.TOP,    Z.FRONT,

            X.RIGHT, Y.TOP,    Z.FRONT,
            X.RIGHT, Y.BOTTOM, Z.FRONT,
            X.LEFT,  Y.TOP,    Z.FRONT,

            //back face,
            X.LEFT,  Y.TOP,    Z.BACK,
            X.LEFT,  Y.BOTTOM, Z.BACK,
            X.RIGHT, Y.BOTTOM, Z.BACK,

            X.LEFT,  Y.TOP,    Z.BACK,
            X.RIGHT, Y.BOTTOM, Z.BACK,
            X.RIGHT, Y.TOP,    Z.BACK,

            // right face,
            X.RIGHT, Y.TOP,    Z.BACK,
            X.RIGHT, Y.BOTTOM, Z.BACK,
            X.RIGHT, Y.BOTTOM, Z.FRONT,

            X.RIGHT, Y.TOP,    Z.BACK,
            X.RIGHT, Y.BOTTOM, Z.FRONT,
            X.RIGHT, Y.TOP,    Z.FRONT,

            // left face,
            X.LEFT, Y.BOTTOM, Z.FRONT,
            X.LEFT, Y.BOTTOM, Z.BACK,
            X.LEFT, Y.TOP,    Z.BACK,

            X.LEFT, Y.TOP,    Z.FRONT,
            X.LEFT, Y.BOTTOM, Z.FRONT,
            X.LEFT, Y.TOP,    Z.BACK,

            // top face,
            X.LEFT,  Y.TOP, Z.FRONT,
            X.LEFT,  Y.TOP, Z.BACK,
            X.RIGHT, Y.TOP, Z.BACK,

            X.LEFT,  Y.TOP, Z.FRONT,
            X.RIGHT, Y.TOP, Z.BACK,
            X.RIGHT, Y.TOP, Z.FRONT,

            // bottom face()
            X.RIGHT, Y.BOTTOM, Z.BACK,
            X.LEFT, Y.BOTTOM, Z.BACK,
            X.LEFT, Y.BOTTOM, Z.FRONT,

            X.RIGHT, Y.BOTTOM, Z.BACK,
            X.LEFT, Y.BOTTOM, Z.FRONT,
            X.RIGHT, Y.BOTTOM, Z.FRONT,
        ]));
    }
}

export class BrushelBoxRenderer extends ShaderProgram implements BrushRenderer{
    readonly box : Cube
    readonly vao: VertexArrayObject
    readonly debugColors: boolean

    constructor({gl, debugColors=false, highlightCrossSection, onlyCrossSection}: {
        gl: WebGL2RenderingContext, debugColors?: boolean, highlightCrossSection: boolean, onlyCrossSection: boolean
    }){
        super(
            gl,
            new VertexShader(gl, `
                //vertex shader to render a single voxel of the brush stroke. Use instanced rendering to render the whole stroke
                precision mediump float;

                in vec3 a_vert_pos_o; //box vertex, different for every vertex
                in vec3 a_offset_vx; //voxel coordinates (cube)

                uniform vec3 u_brush_resolution;

                uniform mat4 u_voxel_to_world;
                uniform mat4 u_world_to_clip;
                uniform mat3 u_clip_to_world;

                out vec3 v_dist_vert_proj_to_box_center_w;

                vec3 face_colors[6] = vec3[](
                    vec3(1, 0, 0), vec3(0, 1, 0), vec3(0, 0, 1),
                    vec3(1, 1, 0), vec3(0, 1, 1), vec3(1, 0, 1)
                );

                ${debugColors ? `out vec3 color;` : ``}

                void main(){
                    vec3 voxel_shape_vx = vec3(1,1,1);
                    vec3 voxel_shape_uvw = voxel_shape_vx * u_brush_resolution;
                    vec3 voxel_shape_w = abs(u_voxel_to_world * vec4(voxel_shape_uvw, 0)).xyz;

                    vec3 box_center_vx = a_offset_vx + vec3(0.5, 0.5, 0.5); // 0.5 -> center of the voxel
                    vec3 box_center_uvw = box_center_vx * u_brush_resolution;
                    vec4 box_center_w = u_voxel_to_world * vec4(box_center_uvw, 1.0);
                    vec4 box_center_c = u_world_to_clip * box_center_w;

                    vec3 vert_pos_w = (a_vert_pos_o * voxel_shape_w) + box_center_w.xyz; //apply voxel_to_world just to the offset so faces don't flip
                    vec4 vert_pos_c = u_world_to_clip * vec4(vert_pos_w, 1.0);

                    vec3 vert_pos_proj_on_slc_plane_c = vec3(vert_pos_c.xy, 0);
                    vec3 dist_vert_proj_to_box_center_c = vert_pos_proj_on_slc_plane_c - box_center_c.xyz;
                    v_dist_vert_proj_to_box_center_w = u_clip_to_world * dist_vert_proj_to_box_center_c;


                    gl_Position = vert_pos_c;
                    ${debugColors ? 'color = face_colors[int(floor(float(gl_VertexID) / 6.0))]; //2 tris per side, 3 verts per tri' : ''}
                }
            `),
            new FragmentShader(gl, `
                precision mediump float;

                uniform mat4 u_voxel_to_world;
                uniform vec3 u_brush_resolution;

                ${debugColors ? `in` : `uniform`} vec3 color;
                in vec3 v_dist_vert_proj_to_box_center_w;


                out highp vec4 outf_color;

                void main(){
                    vec3 voxel_shape_w = abs(u_voxel_to_world * vec4(u_brush_resolution, 0)).xyz; // w=0 because this is a distance, not a point
                    if(all(lessThanEqual(
                        abs(v_dist_vert_proj_to_box_center_w), voxel_shape_w / 2.0  //if projection onto slicing plane is still inside box
                    ))){
                        ${highlightCrossSection ?
                            'outf_color = vec4(mix(color, vec3(1,1,1), 0.5), 1); //increase brightness'
                            :
                            'outf_color = vec4(color, 1);'
                        }

                    }else{
                        ${onlyCrossSection ? "discard;" : "outf_color = vec4(color, 1);"}
                    }
                }
            `)
        )
        this.debugColors = debugColors
        this.box = new Cube()
        this.vao = new VertexArrayObject(gl) //FIXME: cleanup the vao and box buffer (but vao autodelets on GC anyway...)
    }

    public destroy(){
        this.vao.delete()
    }

    public render({
        brush_strokes,
        camera,
        voxelToWorld,
        renderParams=new RenderParams({})
    }: {
        brush_strokes: Array<BrushStroke>,
        camera: Camera,
        voxelToWorld: mat4,
        renderParams?: RenderParams
    }){
        renderParams.use(this.gl)
        this.use()
        this.vao.bind()

        this.box.getPositionsBuffer(this.gl, BufferUsageHint.STATIC_DRAW).useWithAttribute({
            vao: this.vao, location: this.getAttribLocation("a_vert_pos_o")
        })

        let u_voxel_to_world = mat4.clone(voxelToWorld);
        this.uniformMatrix4fv("u_voxel_to_world", u_voxel_to_world);

        let u_world_to_clip = mat4.clone(camera.world_to_clip);
        this.uniformMatrix4fv("u_world_to_clip", u_world_to_clip);

        let u_clip_to_world = mat3.create(); mat3.fromMat4(u_clip_to_world, camera.clip_to_world)
        this.uniformMatrix3fv("u_clip_to_world", u_clip_to_world)

        let a_offset_vx_location = this.getAttribLocation("a_offset_vx");
        for(let brush_stroke of brush_strokes){
            if(!this.debugColors){
                this.uniform3fv("color", brush_stroke.color)
            }
            this.uniform3fv("u_brush_resolution", brush_stroke.resolution)
            brush_stroke.positions_buffer.useAsInstacedAttribute({vao: this.vao, location: a_offset_vx_location, attributeDivisor: 1})
            this.gl.drawArraysInstanced( //instance-draw a bunch of cubes, one cube for each voxel in the brush stroke
                /*mode=*/this.box.getDrawingMode(),
                /*first=*/0,
                /*count=*/this.box.numVerts,
                /*instanceCount=*/brush_stroke.num_points
            );
        }
    }
}
