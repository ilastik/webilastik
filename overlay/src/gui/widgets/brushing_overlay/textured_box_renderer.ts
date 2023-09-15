import { VertexArrayObject } from "../../../gl/buffer";
import { RenderParams } from "../../../gl/gl";
import { ShaderProgram, UniformLocation, VertexShader, FragmentShader } from "../../../gl/shader";
import { Texture3D } from "../../../gl/texture";
import { Mat4 } from "../../../util/ooglmatrix";
import { Cube } from "./brush_boxes_renderer";
import { Camera } from "./camera";

export class TexturedBoxRenderer extends ShaderProgram{
    readonly vao: VertexArrayObject
    private u_BoxRadius_o__location: UniformLocation;
    private u_ObjectToClip__location: UniformLocation;
    private u_ClipToObject__location: UniformLocation;
    texture: Texture3D;
    u_ObjectToTexture__location: UniformLocation;
    u_texture__location: UniformLocation;

    constructor({gl, highlightCrossSection, onlyCrossSection}: {
        gl: WebGL2RenderingContext, debugColors?: boolean, highlightCrossSection: boolean, onlyCrossSection: boolean
    }){
        console.log(`highlightCrossSection is ${highlightCrossSection}`)
        super(
            gl,
            new VertexShader(gl, `
                precision highp float;

                const vec3 boxCenter_o = vec3(0,0,0); //FIXME?

                uniform mat4 u_ObjectToClip;
                uniform mat4 u_ClipToObject;
                uniform mat4 u_ObjectToTexture;

                in vec3 a_vertPos_o;

                out vec3 v_Dist_from_VertProj_to_BoxCenter_o;
                out highp vec3 v_vertProj_on_SlcPlane_tx;
                out vec3 debugColor;

                vec3 face_colors[6] = vec3[](
                    vec3(1, 0, 0), vec3(0, 1, 0), vec3(0, 0, 1),
                    vec3(1, 1, 0), vec3(0, 1, 1), vec3(1, 0, 1)
                );


                void main(){
                    vec4 vertPos_c = u_ObjectToClip * vec4(a_vertPos_o, 1.0);

                    //FIXME?: assuming slicing plane is the Z=0 plane (middle of clip space), so proj is just setting z to 0
                    vec4 vertProj_on_SlcPlane_c = vec4(vertPos_c.xy, 0, 1);
                    vec4 vertProj_on_SlcPlane_o = u_ClipToObject * vertProj_on_SlcPlane_c;
                    v_vertProj_on_SlcPlane_tx = (u_ObjectToTexture * vertProj_on_SlcPlane_o).xyz;

                    v_Dist_from_VertProj_to_BoxCenter_o = vertProj_on_SlcPlane_o.xyz - boxCenter_o;
                    gl_Position = vertPos_c;
                    debugColor = face_colors[gl_VertexID / 6]; //2 tris per side, 3 verts per tri
                }
            `),
            new FragmentShader(gl, `
                precision highp float;

                uniform highp sampler3D u_texture;
                uniform vec3 u_BoxRadius_o;

                in highp vec3 v_vertProj_on_SlcPlane_tx;
                in vec3 v_Dist_from_VertProj_to_BoxCenter_o;
                in vec3 debugColor;

                out highp vec4 outf_color;

                void main(){
                    vec3 fragProj_distanceToCenter_o = abs(v_Dist_from_VertProj_to_BoxCenter_o);

                    bool fragProj_is_strictly_inside_box = all( lessThan(fragProj_distanceToCenter_o, u_BoxRadius_o) );
                    bool fragProj_is_on_face = (
                        all(lessThanEqual(fragProj_distanceToCenter_o, u_BoxRadius_o)) &&
                        any(equal(fragProj_distanceToCenter_o, u_BoxRadius_o))
                    );

                    if(
                        fragProj_is_strictly_inside_box ||
                        gl_FrontFacing && fragProj_is_on_face /*||
                        gl_FragCoord.z == 0.5 //FIXME: double check: this assumes frag depth is in 0 to 1 range (not -1 to +1), so midpoint is 0.5
                        */
                    ){
                        vec4 texelColor = texture(u_texture, v_vertProj_on_SlcPlane_tx);
                        // vec4 texelColor = texture(u_texture, vec3(0.5, 0.5, 0.5));
                        outf_color = texelColor; //increase brightness
                    }else{
                        ${onlyCrossSection
                          ? "discard;"
                          : "outf_color = vec4(debugColor, 1);"}
                    }
                }
            `)
        )
        this.vao = new VertexArrayObject(gl) //FIXME: cleanup the vao and box buffer (but vao autodelets on GC anyway...)

        this.u_ObjectToClip__location = this.getUniformLocation("u_ObjectToClip")
        this.u_ClipToObject__location = this.getUniformLocation("u_ClipToObject")
        this.u_BoxRadius_o__location = this.getUniformLocation("u_BoxRadius_o")
        this.u_ObjectToTexture__location = this.getUniformLocation("u_ObjectToTexture")
        this.u_texture__location = this.getUniformLocation("u_texture")

        this.vao.bind()
        Cube.getVertPositions_o(this.gl).enable({
            vao: this.vao, location: this.getAttribLocation("a_vertPos_o"), normalize: false
        })
        this.texture = Texture3D.defaultDebug({gl: this.gl, textureUnit: WebGL2RenderingContext.TEXTURE0})
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
        let u_ObjectToClip = camera.worldToClip.mul(objectToWorld)
        u_ObjectToClip.useAsUniform(this.gl, this.u_ObjectToClip__location)

        u_ObjectToClip.inverted().useAsUniform(this.gl, this.u_ClipToObject__location);

        Cube.objectToTexture.useAsUniform(this.gl, this.u_ObjectToTexture__location);

        this.uniform3fv(this.u_BoxRadius_o__location, Cube.radius_o)

        this.texture.bind({textureUnit: WebGL2RenderingContext.TEXTURE0})
        this.uniform1i(this.u_texture__location, 0);

        //setup attributes =========


        // render ================
        this.gl.drawArrays( //instance-draw a bunch of cubes, one cube for each voxel in the brush stroke
        /*mode=*/Cube.drawingMode,
        /*first=*/0,
        /*count=*/Cube.numVerts,
        );
        // this.gl.drawArraysInstanced( //instance-draw a bunch of cubes, one cube for each voxel in the brush stroke
        // /*mode=*/this.box.getDrawingMode(),
        // /*first=*/0,
        // /*count=*/this.box.vertCapacity,
        // /*instanceCount=*/brush_stroke.num_points
        // );
    }
}
