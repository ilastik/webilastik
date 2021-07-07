import { mat4, vec3 } from "gl-matrix"
import { BinaryArray, AttributeElementType } from "./gl"
import { ShaderProgram } from "./shader"
import { Buffer } from "./buffer"

export type AttributeNumElements = 1 | 2 | 3 | 4

export class GlslType<Arr extends BinaryArray>{
    private constructor(
        public readonly GlslName: string,
        public readonly elementType: AttributeElementType,
        public readonly numElements: number,
        public readonly binaryArrayFactory: {new(values: Array<number>): Arr}
    ){
    }

    static vec4 = new GlslType("vec4", AttributeElementType.FLOAT, 4, Float32Array)
    static vec3 = new GlslType("vec3", AttributeElementType.FLOAT, 3, Float32Array)
    static vec2 = new GlslType("vec2", AttributeElementType.FLOAT, 2, Float32Array)
}

export type UniformHostType = mat4 | vec3

export abstract class GlslUniform<VARIABLE_TYPE extends UniformHostType>{
    constructor(
        public readonly gl: WebGL2RenderingContext,
        public readonly name: string,
    ){}

    public abstract toCode() : string;
    protected abstract doSet(position: WebGLUniformLocation, value: VARIABLE_TYPE): void;

    public set(value: VARIABLE_TYPE, program: ShaderProgram){
        program.use()
        var uniform_location = this.gl.getUniformLocation(program.glprogram, this.name);
        if(uniform_location === null){
            throw `Could not find uniform named ${this.name}`
        }
        this.doSet(uniform_location, value);
    }
}

export class GlslUniformMat4 extends GlslUniform<mat4>{
    protected doSet(uniform_location: WebGLUniformLocation, value: mat4){
        this.gl.uniformMatrix4fv(uniform_location, false, value)
    }

    public toCode() : string{
        return `uniform mat4 ${this.name};\n`
    }
}

export class GlslAttribute<Arr extends BinaryArray>{
    constructor(
        public readonly gl: WebGL2RenderingContext,
        public readonly GlslType: GlslType<Arr>,
        public readonly name: string
    ){}

    public toCode() : string{
        return `in ${this.GlslType.GlslName} ${this.name};\n`
    }

    public enable({program, buffer, normalize, byteOffset=0}: {
        program: ShaderProgram,
        buffer: Buffer<Arr>,
        normalize: boolean,
        byteOffset?: number
    }){
        let location = program.getAttribLocation(this.name);
        this.gl.enableVertexAttribArray(location.raw);
        buffer.bind()
        this.gl.vertexAttribPointer(
            /*index=*/location.raw,
            /*size=*/this.GlslType.numElements,
            /*type=*/this.GlslType.elementType,
            /*normalize=*/normalize,
            /*stride=*/0,
            /*offset=*/byteOffset
        )
        buffer.unbind()
    }
}
