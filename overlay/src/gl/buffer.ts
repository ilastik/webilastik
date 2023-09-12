import { AttributeElementType, AttributeNumComponents } from "./gl";
import { AttributeLocation } from "./shader";

export type BinaryArray =
    Int8Array |
    Uint8Array |
    Int16Array |
    Uint16Array |
    Float32Array;


/**Collects shader attribute configuration (what buffers supply what attributes and how) */
export class VertexArrayObject{
    private glAttributeObject : WebGLVertexArrayObject
    constructor(public readonly gl: WebGL2RenderingContext){
        let vao = this.gl.createVertexArray();
        if(vao === null){
            throw `Could not create vertex GlslAttribute object`
        }
        this.glAttributeObject = vao;
    }

    public bind(){
        this.gl.bindVertexArray(this.glAttributeObject);
    }

    public unbind(){
        this.gl.bindVertexArray(null);
    }

    public delete(){
        this.gl.deleteVertexArray(this.glAttributeObject)
    }
}

export enum BindTarget {
    //Buffer containing vertex attributes, such as vertex coordinates, texture coordinate data, or vertex color data
    ARRAY_BUFFER = WebGL2RenderingContext.ARRAY_BUFFER,
    //Buffer used for element indices
    ELEMENT_ARRAY_BUFFER = WebGL2RenderingContext.ELEMENT_ARRAY_BUFFER,
}

export enum BufferUsageHint{
    STATIC_DRAW = WebGL2RenderingContext.STATIC_DRAW,
    DYNAMIC_DRAW = WebGL2RenderingContext.DYNAMIC_DRAW,
}

export abstract class Buffer<Arr extends BinaryArray>{
    protected glbuffer: WebGLBuffer
    public readonly gl: WebGL2RenderingContext;
    public readonly bindTarget: BindTarget;

    constructor(params: {
        gl: WebGL2RenderingContext,
        data: Arr,
        usageHint: BufferUsageHint,
        name?: string,
        bindTarget: BindTarget,
    }){
        this.gl = params.gl
        this.bindTarget = params.bindTarget
        let buf = this.gl.createBuffer();
        if(buf === null){
            throw `Could not create buffer`
        }
        this.glbuffer = buf
        this.bind()
        this.gl.bufferData(this.bindTarget, params.data, params.usageHint)
    }

    public destroy(){
        this.gl.deleteBuffer(this.glbuffer)
    }

    public bind(){
        this.gl.bindBuffer(this.bindTarget, this.glbuffer);
    }

    public unbind(){
        this.gl.bindBuffer(this.bindTarget, null);
    }

    public populate({dstByteOffset=0, data, srcElementOffset=0, length=0}: {
         dstByteOffset?: number,
         data: Arr,
         srcElementOffset?: number //in elements (not bytes)
         length?: number // in elements (not bytes)
        }){
        this.bind()
        this.gl.bufferSubData(
            /*target=*/this.bindTarget,
            /*dstByteOffset=*/dstByteOffset,
            /*srcData=*/data,
            /*srcOffset=*/srcElementOffset,
            /*length=*/length
        )
        //this.unbind() //i'm not sure if unbinding will remove the index buffer from its vao
    }
}

export abstract class VertexAttributeBuffer<Arr extends BinaryArray> extends Buffer<Arr>{
    public readonly elementType: AttributeElementType;
    public readonly numComponents: number;

    constructor(params: {
        gl: WebGL2RenderingContext,
        data: Arr,
        usageHint: BufferUsageHint,
        numComponents: number,
        name?: string,
    }){
        super({bindTarget: BindTarget.ARRAY_BUFFER, ...params})
        this.elementType = AttributeElementType.fromBinaryArray(params.data)
        this.numComponents = params.numComponents
    }

    /** Configures the VertexArrayObject 'vao' to use this buffer as an attribute in location 'location'*/
    protected vertexAttribPointer({vao, location, byteOffset=0, normalize, numComponents}:{
        vao: VertexArrayObject,
        location: AttributeLocation,
        byteOffset?: number,
        normalize: boolean,
        numComponents: AttributeNumComponents,
        elementType: AttributeElementType
    }){
        vao.bind();
        this.gl.enableVertexAttribArray(location.raw);
        this.bind()
        this.gl.vertexAttribPointer(
            /*index=*/location.raw,
            /*size=*/numComponents,
            /*type=*/this.elementType.raw,
            /*normalize=*/normalize,
            /*stride=*/0,
            /*offset=*/byteOffset
        )
    }
}


export class VecAttributeBuffer<NUM_COMPONENTS extends 2 | 3 | 4, Arr extends BinaryArray> extends VertexAttributeBuffer<Arr>{
    constructor(params: {
        gl: WebGL2RenderingContext,
        data: Arr,
        usageHint: BufferUsageHint,
        numComponents: NUM_COMPONENTS,
        name?: string,
    }){
        super(params)
    }

    public useWithAttribute({vao, location}:{
        vao: VertexArrayObject,
        location: AttributeLocation,
    }){
        this.vertexAttribPointer({vao, location, numComponents: 3, elementType: AttributeElementType.FLOAT, normalize: false})
    }

    public useAsInstacedAttribute({vao, location, attributeDivisor=1}:{
        vao: VertexArrayObject,
        location: AttributeLocation,
        attributeDivisor?: number //number of instances that will pass between updates of the generic attribute.
    }){
        this.useWithAttribute({vao, location})
        this.bind()
        this.gl.vertexAttribDivisor(location.raw, attributeDivisor);
    }
}

export class Mat4AttributeBuffer extends VertexAttributeBuffer<Float32Array>{
    constructor(params: {
        gl: WebGL2RenderingContext,
        data: Float32Array,
        usageHint: BufferUsageHint,
        name?: string,
    }){
        if(params.data.length % 16 != 0){
            debugger
            throw new Error(`Expected data's length to be multiple of 16. Found this: ${params.data.length}`)
        }
        super({...params, numComponents: 16})
    }

    public useWithAttribute({vao, location}:{vao: VertexArrayObject, location: AttributeLocation}){
        this.vertexAttribPointer({vao, location, numComponents: 3, elementType: AttributeElementType.FLOAT, normalize: false})
    }

    public useAsInstacedAttribute({vao, location, attributeDivisor=1}:{
        vao: VertexArrayObject,
        location: AttributeLocation,
        attributeDivisor?: number //number of instances that will pass between updates of the generic attribute.
    }){
        this.useWithAttribute({vao, location})
        this.bind()
        this.gl.vertexAttribDivisor(location.raw, attributeDivisor);
    }
}