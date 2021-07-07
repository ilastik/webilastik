import { vec3, mat4, mat3 } from "gl-matrix"

export enum ShaderType{
    FRAGMENT_SHADER = WebGL2RenderingContext.FRAGMENT_SHADER,
    VERTEX_SHADER = WebGL2RenderingContext.VERTEX_SHADER,
}

export class Shader{
    public readonly raw: WebGLShader
    public readonly source: string
    constructor(public readonly gl: WebGL2RenderingContext, source: string, shader_type: ShaderType){
        this.source = source = "#version 300 es\n" + source
        let glshader = gl.createShader(shader_type)! //FIXME check this?
        gl.shaderSource(glshader, source)
        gl.compileShader(glshader)
        let success = gl.getShaderParameter(glshader, gl.COMPILE_STATUS);
        if (!success){
            let error_log = gl.getShaderInfoLog(glshader);
            gl.deleteShader(glshader);
            throw error_log + "\n\n" + source.split("\n").map((code_line, line_index) => `${line_index + 1}: ${code_line}`).join("\n")
        }
        this.raw = glshader
    }
}

export class FragmentShader extends Shader{
    constructor(gl: WebGL2RenderingContext, source: string){
        super(gl, source, ShaderType.FRAGMENT_SHADER)
    }
}

export class VertexShader extends Shader{
    constructor(gl: WebGL2RenderingContext, source: string){
        super(gl, source, ShaderType.VERTEX_SHADER)
    }
}

export class AttributeLocation{
    constructor(public readonly name: string, public readonly raw: number){
        //if(raw == -1){throw `Could not find GlslAttribute ${name}`}
    }
}

export class UniformLocation{
    constructor(public readonly name: string, public readonly raw: WebGLUniformLocation | null){
        // if(raw === null){throw `Could not find Glsl Uniform ${name}`}
    }
}

export class ShaderProgram{
    public readonly glprogram: WebGLProgram
    constructor(
        public readonly gl: WebGL2RenderingContext,
        vertexShader: VertexShader,
        fragmentShader: FragmentShader
    ){
        let program = gl.createProgram()!; //FIXME check this?
        gl.attachShader(program, vertexShader.raw);
        gl.attachShader(program, fragmentShader.raw);
        gl.linkProgram(program);
        var success = gl.getProgramParameter(program, gl.LINK_STATUS);
        if (!success) {
            let error_log = gl.getProgramInfoLog(program);
            gl.deleteProgram(program);
            throw error_log
        }
        this.glprogram = program;
    }

    public getAttribLocation(name: string) : AttributeLocation{
        return new AttributeLocation(name, this.gl.getAttribLocation(this.glprogram, name))
    }

    public getUniformLocation(name: string): UniformLocation{
        return new UniformLocation(name, this.gl.getUniformLocation(this.glprogram, name))
    }

    public uniform3fv(name: string, value: vec3){
        this.gl.uniform3fv(this.getUniformLocation(name).raw, value);
    }

    public uniformMatrix4fv(name: string, value: mat4){
        this.gl.uniformMatrix4fv(this.getUniformLocation(name).raw, false, value);
    }

    public uniformMatrix3fv(name: string, value: mat3){
        this.gl.uniformMatrix3fv(this.getUniformLocation(name).raw, false, value);
    }


    public use(){
        this.gl.useProgram(this.glprogram)
    }
}
