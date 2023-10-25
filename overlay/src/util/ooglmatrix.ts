import {mat4, quat, vec3} from "gl-matrix";
import { ViewportGeometry } from "../drivers/viewer_driver";

type Space = | 
    "voxel" | //coord represent indices into the raw data
    "object" |
    "world" |
    "view" |
    "ndc" |
    "dom_element_pixels" | //origin ad top-left, +x is right, +y is down
    "canvas_device_coords" | //(0,0) is lower left of the canvas, +y is up, +x is right
    "viewport_device_coords" | //(0,0) is lower left of the canvas, +y is up, +x is right
    "browser_viewport_pixels";

export class Vec3<SPACE extends Space>{
    public readonly x: number;
    public readonly y: number;
    public readonly z: number;
    public constructor(
        public readonly raw: vec3,
        public readonly space: SPACE,
    ){
        this.x = raw[0];
        this.y = raw[1];
        this.z = raw[2];
    }

    public getMaxAbsCoord(): number{
        return Math.max(
            Math.abs(this.x), Math.abs(this.y), Math.abs(this.z)
        )
    }

    public transformedWith<TARGET extends Space>(mat: Mat4<SPACE, TARGET>): Vec3<TARGET>{
        return new Vec3(
            vec3.transformMat4(vec3.create(), this.raw, mat.raw),
            mat.target
        )
    }

    public scale(scalar: number): Vec3<SPACE>{
        return new Vec3(
            vec3.scale(vec3.create(), this.raw, scalar),
            this.space
        )
    }

    public minus(other: Vec3<SPACE>): Vec3<SPACE>{
        return new Vec3(
            vec3.subtract(vec3.create(), this.raw, other.raw),
            this.space,
        )
    }

    public div(other: Vec3<SPACE>): Vec3<SPACE>{
        return new Vec3(
            vec3.div(vec3.create(), this.raw, other.raw),
            this.space
        )
    }
}

export class Mat4<FROM extends Space, TARGET extends Space>{
    public constructor(
        public readonly raw: mat4,
        public readonly from: FROM,
        public readonly target: TARGET,
    ){
    }

    public clone(): Mat4<FROM, TARGET>{
        return new Mat4(mat4.clone(this.raw), this.from, this.target)
    }

    public static fromScaling<FROM extends Space, TARGET extends Space>(
        scaling: vec3, from: FROM, target: TARGET,
    ): Mat4<FROM, TARGET>{
        return new Mat4(mat4.fromScaling(mat4.create(), scaling), from, target)
    }

    public static fromTranslation<FROM extends Space, TARGET extends Space>(params: {
        from: FROM,
        translation: Vec3<TARGET>,
    }): Mat4<FROM, TARGET>{
        return new Mat4(
            mat4.fromTranslation(
                mat4.create(),
                params.translation.raw,
            ),
            params.from,
            params.translation.space,
        )
    }

    public static fromRotationTranslationScale<FROM extends Space, TARGET extends Space>(params: {
        from: FROM,
        rotation: Quat<TARGET>,
        translation: Vec3<TARGET>,
        scaling: vec3,
    }): Mat4<FROM, TARGET>{
        return new Mat4(
            mat4.fromRotationTranslationScale(
                mat4.create(),
                params.rotation.raw,
                params.translation.raw,
                params.scaling
            ),
            params.from,
            params.translation.space,
        )
    }

    public inverted(): Mat4<TARGET, FROM>{
        return new Mat4(
            mat4.invert(mat4.create(), this.raw), this.target, this.from
        )
    }

    public static domElementToNdc(params: {
        element: HTMLElement,
        viewportGeomewtry: ViewportGeometry,
    }): Mat4<"dom_element", "viewport_pixels">{
        let viewportPose = {
            position: new Vec3(vec3.fromValues(1,2,3), "ndc")
        }

        return Mat4.fromRotationTranslationScale({
            from: "dom_element",
            rotation: Quat.identity("ndc"),
            translation: new Vec3<"ndc">(
                vec3.fromValues(0, params.element.scrollHeight, 0),
                "ndc"
            ),
            scaling: vec3.fromValues(1, -1, 1),
        })
    }

    public mul<NEW_TARGET extends Space>(other: Mat4<TARGET, NEW_TARGET>): Mat4<FROM, NEW_TARGET>{
        return new Mat4(mat4.multiply(mat4.create(), this.raw, other.raw), this.from, other.target)
    }
}

export class Quat<SPACE extends Space>{
    public readonly raw: quat
    public constructor(raw: quat, public readonly space: SPACE){
        this.raw = quat.normalize(quat.create(), raw)
    }

    public static identity<SPACE extends Space>(space: SPACE){
        return new Quat<SPACE>(quat.create(), space)
    }

    public getAxisAngle(): {axis: Vec3<SPACE>, angle_rads: number}{
        const rotation_axis_current = vec3.create();
        const rotation_rads = quat.getAxisAngle(rotation_axis_current, this.raw)
        return {axis: new Vec3<SPACE>(rotation_axis_current, this.space), angle_rads: rotation_rads}
    }

    public static fromAxisAngle<SPACE extends Space>(axis: Vec3<SPACE>, angle_rads: number): Quat<SPACE>{
        const new_raw = quat.setAxisAngle(quat.create(), axis.raw, angle_rads);
        return new Quat(new_raw, axis.space)
    }

    public relativeToBase<TARGET extends Space>(base: Mat4<SPACE, TARGET>): Quat<TARGET>{
        const {axis, angle_rads} = this.getAxisAngle();
        const target_axis = axis.transformedWith(base);
        return Quat.fromAxisAngle(target_axis, angle_rads)
    }
}
