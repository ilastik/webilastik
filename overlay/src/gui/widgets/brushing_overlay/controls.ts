import { quat, vec3 } from "gl-matrix";
import { forward_c, left_c, up_c, OrthoCamera } from "./camera";

export class FirstPersonCamera extends OrthoCamera{
    private forward = 0;
    private backward = 0;
    private left = 0;
    private right = 0;
    private up = 0;
    private down = 0;

    private rotating_left = 0
    private rotating_right = 0
    private rotating_up = 0
    private rotating_down = 0

    public constructor(ortho_params: {
        left: number,
        right: number,
        bottom: number,
        top: number,
        near: number,
        far: number,
        position?: vec3,
        orientation?: quat,
    }){
        super(ortho_params)
        document.addEventListener("keydown", (ev) => {

            switch(ev.code){
                case "KeyW":
                    this.forward = 1
                    break
                case "KeyS":
                    this.backward = 1
                    break
                case "KeyA":
                    this.left = 1
                    break
                case "KeyD":
                    this.right = 1
                    break
                case "KeyQ":
                    this.up = 1
                    break
                case "KeyE":
                    this.down = 1
                    break
                default:
                    return
            }
            let forward_velocity = vec3.scale(vec3.create(), forward_c, this.forward - this.backward);
            let left_velocity = vec3.scale(vec3.create(), left_c, this.left - this.right);
            let up_velocity = vec3.scale(vec3.create(), up_c, this.up - this.down);
            let resultant_velocity = vec3.normalize(vec3.create(), vec3.fromValues(
                forward_velocity[0] + left_velocity[0] + up_velocity[0],
                forward_velocity[1] + left_velocity[1] + up_velocity[1],
                forward_velocity[2] + left_velocity[2] + up_velocity[2],
            ));
            console.log(`Adjusting camera by ${vec3.str(resultant_velocity)}`)
            this.moveInViewSpace(vec3.scale(vec3.create(), resultant_velocity, 0.01))
        })

        document.addEventListener("keydown", (ev) => {
            switch(ev.code){
                case "ArrowUp":
                    this.rotating_up = 1
                    break
                case "ArrowDown":
                    this.rotating_down = 1
                    break
                case "ArrowLeft":
                    this.rotating_left = 1
                    break
                case "ArrowRight":
                    this.rotating_right = 1
                    break
                default:
                    return
            }
            console.log(`ROTATING camera! ${Date.now()}`)
            this.tiltUp((this.rotating_up - this.rotating_down) * 0.001)
            this.rotateLeft((this.rotating_left - this.rotating_right) * 0.001)
        })

        document.addEventListener("keyup", (ev) => {
            switch(ev.code){
                case "KeyW":
                    this.forward = 0
                    break
                case "KeyS":
                    this.backward = 0
                    break
                case "KeyA":
                    this.left = 0
                    break
                case "KeyD":
                    this.right = 0
                    break


                case "KeyQ":
                    this.up = 0
                    break
                case "KeyE":
                    this.down = 0
                    break


                case "ArrowUp":
                    this.rotating_up = 0
                    break
                case "ArrowDown":
                    this.rotating_down = 0
                    break
                case "ArrowLeft":
                    this.rotating_left = 0
                    break
                case "ArrowRight":
                    this.rotating_right = 0
                    break
                default:
                    return
            }
        })
    }
}
