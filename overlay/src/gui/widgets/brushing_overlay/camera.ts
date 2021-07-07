import { mat3, mat4, quat, ReadonlyVec3, vec3 } from "gl-matrix";

export const forward_c = vec3.fromValues( 0,  0, -1);
export const    left_c = vec3.fromValues(-1,  0,  0);
export const      up_c = vec3.fromValues( 0,  1,  0);


export abstract class Camera{
    position_w: vec3 = vec3.create()
    orientation: quat = quat.create()

    view_to_clip: mat4 = mat4.create()
    world_to_view: mat4 = mat4.create()
    view_to_world: mat4 = mat4.create()
    world_to_clip: mat4 = mat4.create()
    clip_to_world: mat4 = mat4.create()

    public constructor({position, orientation}: {
        position?: vec3,
        orientation?: quat,
    }){
        if(position !== undefined){
            vec3.copy(this.position_w, position)
        }
        if(orientation !== undefined){
            quat.copy(this.orientation, orientation)
        }
        this.refreshMatrices()
    }

    protected refreshMatrices(){
        mat4.fromRotationTranslation(this.view_to_world, this.orientation, this.position_w)
        mat4.invert(this.world_to_view, this.view_to_world)
        mat4.multiply(this.world_to_clip, this.view_to_clip, this.world_to_view)
        mat4.invert(this.clip_to_world, this.world_to_clip)
    }

    public reorient(orientation: quat){
        quat.copy(this.orientation, orientation)
        this.refreshMatrices()
    }

    public moveTo(position: vec3){
        vec3.copy(this.position_w, position)
        this.refreshMatrices()
    }

    public snapTo(position: vec3, orientation: quat){
        this.moveTo(position)
        this.reorient(orientation)
    }

    public moveInViewSpace(delta_v: ReadonlyVec3){
        let delta_w = vec3.create(); vec3.transformQuat(delta_w, delta_v, this.orientation);
        vec3.add(this.position_w, this.position_w, delta_w)
        this.refreshMatrices()
    }

    public lookAt({target_w, up_w=vec3.fromValues(0,1,0), position_w}: {
        target_w: vec3, up_w: vec3, position_w: vec3
    }){
        let world_to_view = mat4.create(); mat4.lookAt(
            /*out=*/world_to_view,
            /*eye=*/position_w,
            /*center=*/target_w,
            /*up=*/up_w
        )
        let view_to_world = mat4.create(); mat4.invert(view_to_world, world_to_view);
        let rotation_matrix = mat3.create(); mat3.fromMat4(rotation_matrix, view_to_world);
        quat.fromMat3(this.orientation, rotation_matrix); quat.normalize(this.orientation, this.orientation)
        vec3.copy(this.position_w, position_w)
        this.refreshMatrices()
    }

    public tiltUp(angle_rads: number){
        quat.rotateX(this.orientation, this.orientation, angle_rads)
        quat.normalize(this.orientation, this.orientation)
        this.refreshMatrices()
    }

    public rotateLeft(angle_rads: number){
        quat.rotateY(this.orientation, this.orientation, angle_rads)
        quat.normalize(this.orientation, this.orientation)
        this.refreshMatrices()
    }
}

// export class PerspectiveCamera extends Camera{
//     fovy: number
//     aspect: number
//     near: number
//     far: number
//     constructor({fovy=1, aspect=1, near=0.1, far=1000, position,  orientation}: {
//         fovy?: number,
//         aspect?: number,
//         near?: number,
//         far?: number,
//         position?: vec3,
//         orientation?: quat
//     }){
//         let view_to_clip = mat4.create(); mat4.perspective(view_to_clip, fovy, aspect, near, far)
//         super({position, orientation, view_to_clip})
//     }

//     protected refreshViewToClip(): mat4{
//         return mat4.perspective(this.view_to_clip, fovy, aspect, near, far)
//     }
// }

export class OrthoCamera extends Camera{
    constructor({left, right, bottom, top, near, far, position,  orientation}: {
        left: number,
        right: number,
        bottom: number,
        top: number,
        near: number,
        far: number,
        position?: vec3,
        orientation?: quat
    }){
        super({position, orientation})
        this.reconfigure({left, right, bottom, top, near, far})
    }

    public reconfigure({left, right, bottom, top, near, far, position, orientation}: {
        left: number,
        right: number,
        bottom: number,
        top: number,
        near: number,
        far: number,
        position?: vec3,
        orientation?: quat,
    }){
        vec3.copy(this.position_w, position || this.position_w)
        quat.copy(this.orientation, orientation || this.orientation)
        mat4.ortho(this.view_to_clip, left, right, bottom, top, near, far)
        this.refreshMatrices()
    }
}
