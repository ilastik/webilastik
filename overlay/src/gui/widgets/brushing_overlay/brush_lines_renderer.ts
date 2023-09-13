import { mat4 } from "gl-matrix"
import { BrushRenderer } from "./brush_renderer"
import { Camera } from "./camera"
import { VertexArrayObject } from "../../../gl/buffer"
import { DrawingMode, RenderParams } from "../../../gl/gl"
import { FragmentShader, ShaderProgram, UniformLocation, VertexShader } from "../../../gl/shader"
import { BrushStroke } from "./brush_stroke"
import { Color } from "../../../client/ilastik"
import { Mat4 } from "../../../util/ooglmatrix"


export class BrushelLinesRenderer extends ShaderProgram implements BrushRenderer{
    readonly vao: VertexArrayObject
    private readonly u_voxel_to_clip__location: UniformLocation
    private readonly color__location: UniformLocation

    constructor(gl: WebGL2RenderingContext){
        super(
            gl,
            new VertexShader(gl, `
                //vertex shader to render a single voxel of the brush stroke. Use instanced rendering to render the whole stroke
                precision mediump float;

                uniform mat4 u_voxel_to_clip;
                in vec3 a_offset_vx; //voxel coordinates (cube)

                void main(){
                    gl_Position = u_voxel_to_clip * vec4(a_offset_vx + vec3(0.5, 0.5, 0.5), 1);
                }
            `),
            new FragmentShader(gl, `
                precision mediump float;

                uniform vec3 color;
                out highp vec4 outf_color;

                void main(){
                    outf_color = vec4(color, 1);
                }
            `)
        )
        this.vao = new VertexArrayObject(gl) //FIXME: cleanup the vao and box buffer (but vao autodelets on GC anyway...)

        this.u_voxel_to_clip__location = this.getUniformLocation("u_voxel_to_clip")
        this.color__location = this.getUniformLocation("color")
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
        brush_strokes: Array<[Color, BrushStroke[]]>,
        camera: Camera,
        voxelToWorld: Mat4<"voxel", "world">,
        renderParams?: RenderParams
    }){
        renderParams.use(this.gl)
        this.use()
        this.vao.bind()

        let u_voxel_to_clip = mat4.multiply(mat4.create(), camera.world_to_clip, voxelToWorld.raw);
        this.uniformMatrix4fv(this.u_voxel_to_clip__location, u_voxel_to_clip);

        let a_offset_vx_location = this.getAttribLocation("a_offset_vx");
        for(let [color, annotations] of brush_strokes){
            for(let brush_stroke of annotations){
                this.uniform3fv(this.color__location, color.vec3f)
                brush_stroke.positions_buffer.enable({vao: this.vao, location: a_offset_vx_location, normalize: false})
                this.gl.drawArrays(brush_stroke.num_points == 1 ? DrawingMode.POINTS : DrawingMode.LINE_STRIP, 0, brush_stroke.num_points)
            }
        }
    }
}
