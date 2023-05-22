import {mat4, quat, vec3} from "gl-matrix";

type Space = "voxel" | "object" | "world" | "view" | "ndc";
export class Vec3<SPACE extends Space>{
    public readonly x: number;
    public readonly y: number;
    public readonly z: number;
    public constructor(public readonly raw: vec3){
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
        return new Vec3(vec3.transformMat4(vec3.create(), this.raw, mat.raw))
    }

    public scale(scalar: number): Vec3<SPACE>{
        return new Vec3(vec3.scale(vec3.create(), this.raw, scalar))
    }

    public minus(other: Vec3<SPACE>): Vec3<SPACE>{
        return new Vec3(vec3.subtract(vec3.create(), this.raw, other.raw))
    }

    public div(other: Vec3<SPACE>): Vec3<SPACE>{
        return new Vec3(vec3.div(vec3.create(), this.raw, other.raw))
    }
}

export class Mat4<FROM extends Space, TARGET extends Space>{
    public constructor(public readonly raw: mat4){
    }

    public clone(): Mat4<FROM, TARGET>{
        return new Mat4(mat4.clone(this.raw))
    }

    public static fromScaling<FROM extends Space, TARGET extends Space>(scaling: vec3): Mat4<FROM, TARGET>{
        return new Mat4(mat4.fromScaling(mat4.create(), scaling))
    }

    public inverted(): Mat4<TARGET, FROM>{
        return new Mat4(
            mat4.invert(mat4.create(), this.raw)
        )
    }
}

export class Quat<SPACE extends Space>{
    public readonly raw: quat
    public constructor(raw: quat){
        this.raw = quat.normalize(quat.create(), raw)
    }

    public static identity<SPACE extends Space>(){
        return new Quat<SPACE>(quat.create())
    }

    public getAxisAngle(): {axis: Vec3<SPACE>, angle_rads: number}{
        const rotation_axis_current = vec3.create();
        const rotation_rads = quat.getAxisAngle(rotation_axis_current, this.raw)
        return {axis: new Vec3<SPACE>(rotation_axis_current), angle_rads: rotation_rads}
    }

    public static fromAxisAngle<SPACE extends Space>(axis: Vec3<SPACE>, angle_rads: number): Quat<SPACE>{
        const new_raw = quat.setAxisAngle(quat.create(), axis.raw, angle_rads);
        return new Quat(new_raw)
    }

    public relativeToBase<TARGET extends Space>(base: Mat4<SPACE, TARGET>): Quat<TARGET>{
        const {axis, angle_rads} = this.getAxisAngle();
        const target_axis = axis.transformedWith(base);
        return Quat.fromAxisAngle(target_axis, angle_rads)
    }
}