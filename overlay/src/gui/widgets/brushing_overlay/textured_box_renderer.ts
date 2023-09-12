import { vec3 } from "gl-matrix";
import { VertexArrayObject, BufferUsageHint } from "../../../gl/buffer";
import { RenderParams } from "../../../gl/gl";
import { ShaderProgram, UniformLocation, VertexShader, FragmentShader } from "../../../gl/shader";
import { Mat4, Vec3 } from "../../../util/ooglmatrix";
import { Cube } from "./brush_boxes_renderer";
import { Camera } from "./camera";

export class TexturedBoxRenderer extends ShaderProgram{
    readonly box : Cube
    readonly vao: VertexArrayObject
    private u_BoxRadius_v__location: UniformLocation;
    private u_ObjectToView__location: UniformLocation;
    private u_ObjectToClip__location: UniformLocation;

    constructor({gl, highlightCrossSection, onlyCrossSection}: {
        gl: WebGL2RenderingContext, debugColors?: boolean, highlightCrossSection: boolean, onlyCrossSection: boolean
    }){
        super(
            gl,
            new VertexShader(gl, `
                precision highp float;

                in vec3 a_vertPos_o;

                uniform mat4 u_ObjectToView;
                uniform mat4 u_ObjectToClip;

                out vec3 v_Dist_from_VertProj_to_BoxCenter_v;
                out vec3 debugColor;

                vec3 face_colors[6] = vec3[](
                    vec3(1, 0, 0), vec3(0, 1, 0), vec3(0, 0, 1),
                    vec3(1, 1, 0), vec3(0, 1, 1), vec3(1, 0, 1)
                );


                void main(){
                    vec4 boxCenter_o = vec4(0,0,0, 1);
                    vec4 boxCenter_v = u_ObjectToView * boxCenter_o;

                    vec4 vertPos_v =   u_ObjectToView * vec4(a_vertPos_o, 1.0);

                    //FIXME: assuming slicing plane is the Z=0 plane, so proj is just setting z to 0
                    vec3 vertPos_proj_on_SlcPlane_v = vec3(vertPos_v.xy, 0);
                    vec3 v_Dist_from_VertProj_to_BoxCenter_v = vertPos_proj_on_SlcPlane_v - boxCenter_v.xyz;

                    gl_Position = u_ObjectToClip * vec4(a_vertPos_o, 1.0);
                    debugColor = face_colors[gl_VertexID / 6]; //2 tris per side, 3 verts per tri
                }
            `),
            new FragmentShader(gl, `
                precision highp float;

                uniform mat4 u_ObjectToView;
                uniform vec3 u_BoxRadius_v;

                in vec3 debugColor;
                in vec3 v_Dist_from_VertProj_to_BoxCenter_v;


                out highp vec4 outf_color;

                void main(){
                    vec3 fragProj_distanceToCenter_v = abs(v_Dist_from_VertProj_to_BoxCenter_v);
                    bool projected_frag_is_strictly_inside_box = all( lessThan(fragProj_distanceToCenter_v, u_BoxRadius_v) );
                    bool projected_frag_is_on_face = fragProj_distanceToCenter_v == u_BoxRadius_v;
                    if(
                        projected_frag_is_strictly_inside_box ||
                        gl_FrontFacing && projected_frag_is_on_face ||
                        gl_FragCoord.z == 0.5 //FIXME: double check: this assumes frag depth is in 0 to 1 range (not -1 to +1), so midpoint is 0.5
                    ){
                        ${highlightCrossSection
                          ? 'outf_color = vec4(mix(debugColor, vec3(1,1,1), 0.5), 1); //increase brightness'
                          : 'outf_color = vec4(debugColor, 1);'}
                    }else{
                        ${onlyCrossSection
                          ? "discard;"
                          : "outf_color = vec4(debugColor, 1);"}
                    }
                }
            `)
        )
        this.box = new Cube()
        this.vao = new VertexArrayObject(gl) //FIXME: cleanup the vao and box buffer (but vao autodelets on GC anyway...)


        this.u_ObjectToView__location = this.getUniformLocation("u_ObjectToView")
        this.u_ObjectToClip__location = this.getUniformLocation("u_ObjectToClip")
        this.u_BoxRadius_v__location = this.getUniformLocation("u_BoxRadius_v")

        this.vao.bind()
        this.box.getPositionsBuffer(this.gl, BufferUsageHint.STATIC_DRAW).useWithAttribute({
            vao: this.vao, location: this.getAttribLocation("a_vertPos_o")
        })
    }

    public destroy(){
        this.vao.delete()
    }

    public render({
        objectToWorld,
        camera,
        renderParams=new RenderParams({})
    }: {
        objectToWorld: Mat4<"object", "world">,
        camera: Camera,
        renderParams?: RenderParams
    }){
        renderParams.use(this.gl)
        this.use()
        this.vao.bind()

        // show_if_changed("u_voxel_to_world", mat4.str(u_voxel_to_world))

        //setup uniforms ========
        // let u_ObjectToView: Mat4<"object", "view"> = camera.worldToView.mul(objectToWorld)
        let u_ObjectToView = camera.worldToView.mul(objectToWorld)
        u_ObjectToView.useAsUniform(this.gl, this.u_ObjectToView__location)

        let u_ObjectToClip = camera.worldToClip.mul(objectToWorld)
        u_ObjectToClip.useAsUniform(this.gl, this.u_ObjectToClip__location)

        //FIXME: asumes box has 1 unit of length. Can the ObjectToWorld matrix compensate for that?
        const u_BoxRadius_v = new Vec3<"object">(vec3.fromValues(1,1,1)).transformedWith(u_ObjectToView)
        u_BoxRadius_v.useAsUniform(this.gl, this.u_BoxRadius_v__location)


        //setup attributes =========
        // boxTransforms.useAsInstacedAttribute({
        //     vao: this.vao, location: this.a_offset_vx__location, attributeDivisor: 1
        // })

        // render ================
        this.gl.drawArrays( //instance-draw a bunch of cubes, one cube for each voxel in the brush stroke
        /*mode=*/this.box.getDrawingMode(),
        /*first=*/0,
        /*count=*/this.box.vertCapacity,
        );
        // this.gl.drawArraysInstanced( //instance-draw a bunch of cubes, one cube for each voxel in the brush stroke
        // /*mode=*/this.box.getDrawingMode(),
        // /*first=*/0,
        // /*count=*/this.box.vertCapacity,
        // /*instanceCount=*/brush_stroke.num_points
        // );
    }
}
