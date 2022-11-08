

export class Texture{
    public readonly glTexture: WebGLTexture;

    constructor(gl: WebGL2RenderingContext){
        const texture = gl.createTexture();
        if(texture === null){
            throw `Could not create a gl texture`
        }
        this.glTexture = texture
    }
}