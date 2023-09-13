import { vec3 } from "gl-matrix";
import { BufferUsageHint, VecAttributeBuffer } from "./buffer";
import { DrawingMode, FrontFace } from "./gl";

export class VertexArray{
    public readonly data: Float32Array
    public readonly vertCapacity: number
    constructor(arr: Float32Array){
        if(arr.length % 3){
            throw `Bad array length when creating VertexArray: ${arr.length}`
        }
        this.data = arr
        this.vertCapacity = arr.length / 3
    }

    public getVertRef(index: number) : vec3{
        return this.data.subarray((index * 3), (index + 1) * 3)
    }
}

export abstract class VertexPrimitive extends VertexArray{
    private positionsBuffer?: VecAttributeBuffer<3, Float32Array>

    public abstract getDrawingMode() : DrawingMode;

    public getPositionsBuffer(gl: WebGL2RenderingContext, usageHint: BufferUsageHint): VecAttributeBuffer<3, Float32Array>{
        if(this.positionsBuffer === undefined){
            this.positionsBuffer = new VecAttributeBuffer({gl, numComponents: 3, data: this.data, usageHint})
        }
        return this.positionsBuffer
    }

    public deletePositionsBuffer(){
        this.positionsBuffer!.destroy()
        this.positionsBuffer = undefined
    }
}

export class TriangleArray extends VertexPrimitive{
    public readonly vertexOrder: FrontFace
    public readonly numTriangles: number

    constructor(arr: Float32Array, vertexOrder: FrontFace = FrontFace.CCW){
        if(arr.length % (3 * 3) != 0){
            throw `Trying to create a triangle strip with array of ${arr.length} floats`
        }
        super(arr)
        this.vertexOrder = vertexOrder
        this.numTriangles = this.vertCapacity / 3
    }

    public getDrawingMode(): DrawingMode{
        return DrawingMode.TRIANGLES
    }
}
