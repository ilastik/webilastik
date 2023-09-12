import { mat4, quat, vec3 } from "gl-matrix"
import { FirstPersonCamera } from "./gui/widgets/brushing_overlay/controls"
import { Canvas } from "./gui/widgets/widget"
import { Mat4 } from "./util/ooglmatrix"
import { TexturedBoxRenderer } from "./gui/widgets/brushing_overlay/textured_box_renderer"
import { ClearConfig, RenderParams } from "./gl/gl"

export {}

document.addEventListener("DOMContentLoaded", () => {
    const canvas = new Canvas({
        parentElement: document.body, height: 400, width: 600, inlineCss: {border: "solid 2px green"}
    })
    const context = canvas.getContext();
    if(context instanceof Error){
        alert(`Could not get webgl2 context`);
        return
    }
    const camera = new FirstPersonCamera({
        near: -30,
        far: 30,
        left:   -canvas.element.scrollWidth / 2 / 50,
        right:   canvas.element.scrollWidth / 2 / 50,
        bottom: -canvas.element.scrollHeight / 2 / 50,
        top:     canvas.element.scrollHeight / 2 / 50,
        position: vec3.fromValues(-0.09431380033493042, 0.7441552877426147, 0.6029132008552551),
        orientation: quat.fromValues(0.26481613516807556, -0.27481603622436523, -0.07902452349662781, 0.9209254384040833)
    })
    const renderer = new TexturedBoxRenderer({
        gl: context,
        highlightCrossSection: true,
        onlyCrossSection: false
    })


    const render = () => {
        window.requestAnimationFrame(render)
        renderer.render({
            objectToWorld: new Mat4(mat4.create()),
            camera: camera,
            renderParams: new RenderParams({
                clearConfig: new ClearConfig({
                    r: 0, g: 0, b: 0, a: 1,
                }),
            })
        })
    }
    render()
})