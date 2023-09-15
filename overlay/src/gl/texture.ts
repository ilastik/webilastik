import { BinaryArray } from "./buffer";
import { AttributeElementType } from "./gl";


export type TextureUnit = |
    WebGL2RenderingContext["TEXTURE0"] |
    WebGL2RenderingContext["TEXTURE1"] |
    WebGL2RenderingContext["TEXTURE2"] |
    WebGL2RenderingContext["TEXTURE3"] |
    WebGL2RenderingContext["TEXTURE4"] |
    WebGL2RenderingContext["TEXTURE5"] |
    WebGL2RenderingContext["TEXTURE6"] |
    WebGL2RenderingContext["TEXTURE7"] |
    WebGL2RenderingContext["TEXTURE8"] |
    WebGL2RenderingContext["TEXTURE9"] |
    WebGL2RenderingContext["TEXTURE10"] |
    WebGL2RenderingContext["TEXTURE11"] |
    WebGL2RenderingContext["TEXTURE12"] |
    WebGL2RenderingContext["TEXTURE13"] |
    WebGL2RenderingContext["TEXTURE14"] |
    WebGL2RenderingContext["TEXTURE15"] |
    WebGL2RenderingContext["TEXTURE16"] |
    WebGL2RenderingContext["TEXTURE17"] |
    WebGL2RenderingContext["TEXTURE18"] |
    WebGL2RenderingContext["TEXTURE19"] |
    WebGL2RenderingContext["TEXTURE20"] |
    WebGL2RenderingContext["TEXTURE21"] |
    WebGL2RenderingContext["TEXTURE22"] |
    WebGL2RenderingContext["TEXTURE23"] |
    WebGL2RenderingContext["TEXTURE24"] |
    WebGL2RenderingContext["TEXTURE25"] |
    WebGL2RenderingContext["TEXTURE26"] |
    WebGL2RenderingContext["TEXTURE27"] |
    WebGL2RenderingContext["TEXTURE28"] |
    WebGL2RenderingContext["TEXTURE29"] |
    WebGL2RenderingContext["TEXTURE30"] |
    WebGL2RenderingContext["TEXTURE31"];

//FIXME: add other formats
export type TextureFormat = |
    WebGL2RenderingContext["RGBA"]

//FIXME: add other formats
export type TextureInternalFormat = |
    WebGL2RenderingContext["RGBA"]

//FIXME: add type union with all combinations form here:
//https://www.khronos.org/registry/webgl/specs/latest/2.0/#TEXTURE_TYPES_FORMATS_FROM_DOM_ELEMENTS_TABLE

export class Texture3D{
    public readonly __name__ = "Texture3D"
    public readonly gl: WebGL2RenderingContext
    public readonly glTexture: WebGLTexture;

    constructor(params: {
        gl: WebGL2RenderingContext,
        texImageParams: Parameters<Texture3D["texImage3D"]>[0],
    }){
        this.gl = params.gl
        const texture = params.gl.createTexture();
        if(texture === null){
            throw `Could not create a gl texture`
        }
        this.glTexture = texture
        this.texImage3D(params.texImageParams)
    }

    public texImage3D<Arr extends BinaryArray>(params: {
        textureUnit: TextureUnit,
        level: number, //mipmap level. 0 is the finest detail
        internalformat: TextureInternalFormat,
        width: number,
        height: number,
        depth: number,
        format: TextureFormat
        pixels: Arr,
        offset: number,
    }){
        this.gl.activeTexture(params.textureUnit)
        this.gl.bindTexture(this.gl.TEXTURE_3D, this.glTexture);
        // this.gl.pixelStorei(WebGL2RenderingContext.UNPACK_FLIP_Y_WEBGL, params.UNPACK_FLIP_Y_WEBGL);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_WRAP_R, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_MIN_FILTER, this.gl.NEAREST);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_MAG_FILTER, this.gl.NEAREST);

        // Fill the texture with a 1x1 blue pixel.
        this.gl.texImage3D(
            /*target=*/WebGL2RenderingContext.TEXTURE_3D,
            /*level=*/params.level,
            /*internalformat=*/params.internalformat,
            /*width=*/params.width,
            /*height=*/params.height,
            /*depth=*/params.depth,
            /*border=*/0, //MUST be 0
            /*format=*/params.format,
            /*type=*/AttributeElementType.fromBinaryArray(params.pixels).raw,
            /*pixels=*/params.pixels,
            /*offset=*/params.offset,
        );
    }

    public bind(params: {textureUnit: TextureUnit}){
        this.gl.activeTexture(params.textureUnit)
        this.gl.bindTexture(WebGL2RenderingContext.TEXTURE_3D, this.glTexture)
    }

    public static defaultDebug(params: {
        gl: WebGL2RenderingContext,
        textureUnit: TextureUnit,
    }): Texture3D{
        const RED = [255, 0,   0,   255];
        const blu = [  0, 0, 255,   255];

        const pixels = new Uint8Array([
            ...blu, ...blu, ...blu, ...blu, ...blu,
            ...blu, ...RED, ...RED, ...RED, ...blu,
            ...blu, ...RED, ...blu, ...blu, ...blu,
            ...blu, ...RED, ...blu, ...blu, ...blu,
            ...blu, ...RED, ...RED, ...blu, ...blu,
            ...blu, ...RED, ...blu, ...blu, ...blu,
            ...blu, ...RED, ...blu, ...blu, ...blu,
            ...blu, ...RED, ...blu, ...blu, ...blu,
            ...blu, ...blu, ...blu, ...blu, ...blu,
        ])

        // const pixels = new Uint8Array([
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        //     ...RED, ...RED, ...RED, ...RED, ...RED,
        // ])

        const width = 5;
        const height = 9;
        const depth = 1;

        return new Texture3D({
            gl: params.gl,
            texImageParams: {
                textureUnit: params.textureUnit,
                level: 0,
                width,
                height,
                depth,
                format: WebGL2RenderingContext.RGBA,
                internalformat: WebGL2RenderingContext.RGBA,
                offset: 0,
                pixels: pixels,
            }
        })
    }
}