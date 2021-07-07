import { vec4 } from "gl-matrix"

export type BinaryArray = ArrayBufferView & {length: number}

export enum DrawingMode{
    POINTS = WebGL2RenderingContext.POINTS,
    LINE_STRIP = WebGL2RenderingContext.LINE_STRIP,
    LINE_LOOP = WebGL2RenderingContext.LINE_LOOP,
    LINES = WebGL2RenderingContext.LINES,
    TRIANGLE_STRIP = WebGL2RenderingContext.TRIANGLE_STRIP,
    TRIANGLE_FAN = WebGL2RenderingContext.TRIANGLE_FAN,
    TRIANGLES = WebGL2RenderingContext.TRIANGLES,
}

export enum AttributeElementType{
    BYTE = WebGL2RenderingContext.BYTE,
    SHORT = WebGL2RenderingContext.SHORT,
    UNSIGNED_BYTE = WebGL2RenderingContext.UNSIGNED_BYTE,
    UNSIGNED_SHORT = WebGL2RenderingContext.UNSIGNED_SHORT,
    FLOAT = WebGL2RenderingContext.FLOAT,
}

// determines if each atribute value in the buffer is a single, vec2, vec3 or vec4
export type AttributeNumComponents = 1 | 2 | 3 | 4

export enum StencilOp{
    KEEP = WebGL2RenderingContext.KEEP,
    ZERO = WebGL2RenderingContext.ZERO,
    REPLACE = WebGL2RenderingContext.REPLACE,
    INCR = WebGL2RenderingContext.INCR,
    INCR_WRAP = WebGL2RenderingContext.INCR_WRAP,
    DECR = WebGL2RenderingContext.DECR,
    DECR_WRAP = WebGL2RenderingContext.DECR_WRAP,
    INVERT = WebGL2RenderingContext.INVERT,
}

export enum StencilFunc{
    NEVER = WebGL2RenderingContext.NEVER,
    LESS = WebGL2RenderingContext.LESS,
    EQUAL = WebGL2RenderingContext.EQUAL,
    LEQUAL = WebGL2RenderingContext.LEQUAL,
    GREATER = WebGL2RenderingContext.GREATER,
    NOTEQUAL = WebGL2RenderingContext.NOTEQUAL,
    GEQUAL = WebGL2RenderingContext.GEQUAL,
    ALWAYS = WebGL2RenderingContext.ALWAYS,
}

export enum CullFace{
    BACK = WebGL2RenderingContext.BACK,
    FRONT = WebGL2RenderingContext.FRONT,
    FRONT_AND_BACK = WebGL2RenderingContext.FRONT_AND_BACK,
}

export enum FrontFace{
    CW = WebGL2RenderingContext.CW,
    CCW = WebGL2RenderingContext.CCW,
}

export enum BlendFactor{
    ZERO = WebGL2RenderingContext.ZERO,
    ONE = WebGL2RenderingContext.ONE,
    SRC_COLOR = WebGL2RenderingContext.SRC_COLOR,
    ONE_MINUS_SRC_COLOR = WebGL2RenderingContext.ONE_MINUS_SRC_COLOR,
    DST_COLOR = WebGL2RenderingContext.DST_COLOR,
    ONE_MINUS_DST_COLOR = WebGL2RenderingContext.ONE_MINUS_DST_COLOR,
    SRC_ALPHA = WebGL2RenderingContext.SRC_ALPHA,
    ONE_MINUS_SRC_ALPHA = WebGL2RenderingContext.ONE_MINUS_SRC_ALPHA,
    DST_ALPHA = WebGL2RenderingContext.DST_ALPHA,
    ONE_MINUS_DST_ALPHA = WebGL2RenderingContext.ONE_MINUS_DST_ALPHA,
    CONSTANT_COLOR = WebGL2RenderingContext.CONSTANT_COLOR,
    ONE_MINUS_CONSTANT_COLOR = WebGL2RenderingContext.ONE_MINUS_CONSTANT_COLOR,
    CONSTANT_ALPHA = WebGL2RenderingContext.CONSTANT_ALPHA,
    ONE_MINUS_CONSTANT_ALPHA = WebGL2RenderingContext.ONE_MINUS_CONSTANT_ALPHA,
    SRC_ALPHA_SATURATE = WebGL2RenderingContext.SRC_ALPHA_SATURATE,
}

export enum BlendEquation{
    FUNC_ADD = WebGL2RenderingContext.FUNC_ADD,
    FUNC_SUBTRACT = WebGL2RenderingContext.FUNC_SUBTRACT,
    FUNC_REVERSE_SUBTRACT = WebGL2RenderingContext.FUNC_REVERSE_SUBTRACT,
    MIN = WebGL2RenderingContext.MIN,
    MAX = WebGL2RenderingContext.MAX,
}

export enum DepthFunc{
    NEVER = WebGL2RenderingContext.NEVER,
    LESS = WebGL2RenderingContext.LESS,
    EQUAL = WebGL2RenderingContext.EQUAL,
    LEQUAL = WebGL2RenderingContext.LEQUAL,
    GREATER = WebGL2RenderingContext.GREATER,
    NOTEQUAL = WebGL2RenderingContext.NOTEQUAL,
    GEQUAL = WebGL2RenderingContext.GEQUAL,
    ALWAYS = WebGL2RenderingContext.ALWAYS,
}

export class CullConfig{
    public readonly face: CullFace
    public readonly frontFace: FrontFace
    public readonly enable: boolean

    constructor({face=CullFace.BACK, frontFace=FrontFace.CCW, enable=true}: {
        face?: CullFace,
        frontFace?: FrontFace,
        enable?: boolean
    }){
        this.face = face; this.frontFace = frontFace, this.enable = enable
    }

    public use(gl: WebGL2RenderingContext){
        if(this.enable){
            gl.enable(gl.CULL_FACE)
            gl.frontFace(this.frontFace)
            gl.cullFace(this.face)
        }else{
            gl.disable(gl.CULL_FACE)
        }
    }
}

export class ColorMask{
    public r: boolean;
    public g: boolean;
    public b: boolean;
    public a: boolean;

    constructor({r=true, g=true, b=true, a=true}: {r?: boolean, g?: boolean, b?: boolean, a?: boolean}){
        this.r = r; this.g = g; this.b=b; this.a = a
    }

    public use(gl: WebGL2RenderingContext){
        gl.colorMask(this.r, this.g, this.b, this.a)
    }
}

export class StencilConfig{
    public func: StencilFunc
    public ref: number
    public mask: number

    public fail: StencilOp
    public zfail: StencilOp
    public zpass: StencilOp

    public readonly enable: boolean

     //default stencil op to not touch the stencil
    constructor({
        func=StencilFunc.ALWAYS, ref=1, mask=0xFFFFFFFF, fail=StencilOp.KEEP, zfail=StencilOp.KEEP, zpass=StencilOp.KEEP, enable=true
    }: {
        func?: StencilFunc
        ref?: number
        mask?: number

        fail?: StencilOp
        zfail?: StencilOp
        zpass?: StencilOp

        enable?: boolean
    }){
        this.func=func; this.ref=ref; this.mask=mask; this.fail=fail; this.zfail=zfail; this.zpass=zpass; this.enable=enable
    }

    public use(gl: WebGL2RenderingContext){
        if(this.enable){
            gl.enable(gl.STENCIL_TEST)
            gl.stencilFunc(/*func=*/this.func, /*ref=*/this.ref, /*mask=*/this.mask)
            gl.stencilOp(/*fail=*/this.fail, /*zfail=*/this.zfail, /*zpass=*/this.zpass)
        }else{
            gl.disable(gl.STENCIL_TEST)
        }
    }
}

export class ScissorConfig{
    public readonly x: GLint
    public readonly y: GLint
    public readonly width: GLsizei
    public readonly height: GLsizei
    public readonly enable: boolean

    constructor({x, y, width, height, enable=true}:{
        x: GLint,
        y: GLint,
        width: GLsizei,
        height: GLsizei,
        enable?: boolean
    }){
        this.x = x
        this.y = y
        this.width = width
        this.height = height
        this.enable = enable
    }

    public static default(): ScissorConfig{
        return new ScissorConfig({x:0, y:0, height:0, width: 0, enable: false})
    }

    public use(gl: WebGL2RenderingContext){
        if(this.enable){
            gl.enable(gl.SCISSOR_TEST)
            gl.scissor(this.x, this.y, this.width, this.height)
        }else{
            gl.disable(gl.SCISSOR_TEST)
        }
    }
}

export class BlendingConfig{
    sfactor: BlendFactor
    dfactor: BlendFactor
    equation: BlendEquation
    color?: vec4
    enable: boolean

    constructor({
        sfactor=BlendFactor.SRC_ALPHA, dfactor=BlendFactor.ONE_MINUS_SRC_ALPHA, equation=BlendEquation.FUNC_ADD, color, enable=true
    }:{
        sfactor?: BlendFactor,
        dfactor?: BlendFactor,
        equation?: BlendEquation,
        color?: vec4,
        enable?: boolean
    }){
        this.sfactor=sfactor; this.dfactor=dfactor; this.equation=equation; this.color=color; this.enable=enable
    }

    public use(gl: WebGL2RenderingContext){
        if(this.enable){
            gl.enable(gl.BLEND)
            gl.blendFunc(this.sfactor, this.dfactor)
            gl.blendEquation(this.equation)
        }else{
            gl.disable(gl.BLEND)
        }
    }
}

export class DepthConfig{
    readonly mask: boolean
    readonly func: DepthFunc
    readonly enable: boolean


    constructor({mask=true, func=DepthFunc.LESS, enable=true} : {
        mask?: boolean,
        func?:DepthFunc,
        enable?: boolean
    }){
        this.mask=mask; this.func=func; this.enable=enable
    }

    public use(gl: WebGL2RenderingContext){
        if(this.enable){
            gl.enable(gl.DEPTH_TEST)
            gl.depthMask(this.mask)
            gl.depthFunc(this.func)
        }else{
            gl.disable(gl.DEPTH_TEST)
        }

    }
}

export class ClearConfig{
    readonly r: number
    readonly g: number
    readonly b: number
    readonly a: number

    readonly clear_color: boolean
    readonly clear_depth: boolean
    readonly clear_stencil: boolean

    constructor({r=0, g=0, b=0, a=1, clear_color=true, clear_depth=true, clear_stencil=true}: {
        r?: number,
        g?: number,
        b?: number,
        a?: number,

        clear_color?: boolean,
        clear_depth?: boolean,
        clear_stencil?: boolean,
    }){
        this.r = r
        this.g = g
        this.b = b
        this.a = a

        this.clear_color = clear_color
        this.clear_depth = clear_depth
        this.clear_stencil = clear_stencil
    }

    public use(gl: WebGL2RenderingContext){
        gl.clearColor(this.r, this.g, this.b, this.a);
        let flags = 0
        if(this.clear_color){
            flags = flags | WebGL2RenderingContext.COLOR_BUFFER_BIT
        }
        if(this.clear_depth){
            flags = flags | WebGL2RenderingContext.DEPTH_BUFFER_BIT
        }
        if(this.clear_stencil){
            flags = flags | WebGL2RenderingContext.STENCIL_BUFFER_BIT
        }
        gl.clear(flags);
    }
}

export class RenderParams{
    public colorMask: ColorMask
    public depthConfig: DepthConfig
    public stencilConfig: StencilConfig
    public scissorConfig: ScissorConfig
    public cullConfig: CullConfig
    public blendingConfig: BlendingConfig
    public clearConfig: ClearConfig

    public constructor({
        colorMask=new ColorMask({}),
        depthConfig=new DepthConfig({}),
        stencilConfig=new StencilConfig({}),
        scissorConfig=ScissorConfig.default(),
        cullConfig=new CullConfig({}),
        blendingConfig=new BlendingConfig({}),
        clearConfig=new ClearConfig({}),
    }: {
        colorMask?: ColorMask,
        depthConfig?: DepthConfig,
        stencilConfig?: StencilConfig,
        scissorConfig?: ScissorConfig,
        cullConfig?: CullConfig,
        blendingConfig?: BlendingConfig,
        clearConfig?: ClearConfig,
    }){
        this.colorMask = colorMask
        this.depthConfig = depthConfig
        this.stencilConfig = stencilConfig
        this.scissorConfig = scissorConfig
        this.cullConfig = cullConfig
        this.blendingConfig = blendingConfig
        this.clearConfig = clearConfig
    }

    public use(gl: WebGL2RenderingContext){
        this.colorMask.use(gl)
        this.depthConfig.use(gl)
        this.stencilConfig.use(gl)
        this.scissorConfig.use(gl)
        this.cullConfig.use(gl)
        this.blendingConfig.use(gl)
        this.clearConfig.use(gl)
    }
}
