import { mat4, vec3 } from 'gl-matrix'
import { BrushRenderer } from './brush_renderer'
import { OrthoCamera } from './camera'
import { ClearConfig, RenderParams, ScissorConfig, ViewportConfig } from '../../../gl/gl'
import { coverContents, removeElement } from '../../../util/misc'
import { ViewportGeometry } from '../../../drivers/viewer_driver'
import { IBrushStrokeHandler, BrushStroke } from './brush_stroke'
import { Color, FsDataSource } from '../../../client/ilastik'
import { Mat4, Quat, Vec3 } from '../../../util/ooglmatrix'
import { Viewer } from '../../../viewer/viewer'

export class OverlayViewport{
    public readonly gl: WebGL2RenderingContext
    public readonly canvas: HTMLCanvasElement
    public height: GLint
    public width: GLint
    public y: GLint
    public x: GLint
    public readonly viewport_dev_to_canvas_dev: Mat4<"viewport_device_coords", "canvas_device_coords">
    canvas_dev_to_viewport_dev: Mat4<"canvas_device_coords", "viewport_device_coords">
    // private readonly position: Vec3<"canvas_device_coords">;
    // private readonly scale: Vec3<"canvas_device_coords">;

    public constructor(params: {
        datasource: FsDataSource,
        brush_stroke_handler: IBrushStrokeHandler,
        gl: WebGL2RenderingContext,
        x: GLint,
        y: GLint,
        width: GLint,
        height: GLint,
    }){
        this.gl = params.gl
        this.canvas = this.gl.canvas as HTMLCanvasElement

        this.x = params.x
        this.y = params.y
        this.width = params.width
        this.height = params.height

        this.viewport_dev_to_canvas_dev = Mat4.fromTranslation({
            from: "viewport_device_coords",
            translation: new Vec3(vec3.fromValues(this.x, this.y, 0), "canvas_device_coords"),
        })
        this.canvas_dev_to_viewport_dev = this.viewport_dev_to_canvas_dev.inverted()

        const viewport_dev_to_ndc = Mat4.fromRotationTranslationScale({
            from: "viewport_device_coords",
            rotation: Quat.identity("viewport_device_coords"),
            translation: new Vec3(
                vec3.fromValues(this.width / 2, this.height / 2, 0), "viewport_device_coords"
            ),
        })
    }

    public makeGlobalToLocalTransform(): Mat4<"canvas_device_coords", "viewport_device_coords">{
        const local_to_global =
        return local_to_global.inverted()
    }

    public makeGlobalToNdcTransform(): Mat4<"canvas_device_coords", "ndc">{
        const global_to_local = this.makeGlobalToLocalTransform();
        const global_to_centered_local = global_to_local.mul(
            Mat4.fromRotationTranslationScale({
                from: "viewport_device_coords",
                rotation: Quat.identity("viewport_device_coords"),
                translation: new Vec3(vec3.fromValues(

                ))
            })
        )

        // Mat4.fromScaling(vec3.fromValues())


        const normalizing_matrix = Mat4.fromScaling<"canvas_device_coords", "ndc">( //FIXME! check original impl
            vec3.fromValues(1 / this.width, 1 / this.height, 1),
            "canvas_device_coords",
            "ndc",
        )
        mat4.multiply

    }

    public getCamera(params: {
        zoomInWorldUnitsPerPixel: number,
        cameraPose_w: {position: Vec3<"world">, orientation: Quat<"world">},
    }): OrthoCamera{
        // - near and far have to be such that a voxel in any orientation would fit between them;
        const world_units_per_pixel = params.zoomInWorldUnitsPerPixel;
        // const voxel_diagonal_length = vec3.length(mat4.getScaling(vec3.create(), this.viewport_driver.getVoxelToWorldMatrix()))
        const viewport_width_w = this.geometry.width * world_units_per_pixel;
        const viewport_height_w = this.geometry.height * world_units_per_pixel;
        const camera_pose_w = params.cameraPose_w
        return new OrthoCamera({
            left: -viewport_width_w / 2,
            right: viewport_width_w / 2,
            near: -1000,//-voxel_diagonal_length,
            far: 1000,//voxel_diagonal_length,
            bottom: -viewport_height_w / 2,
            top: viewport_height_w / 2,
            position: camera_pose_w.position.raw,
            orientation: camera_pose_w.orientation.raw,
        })
    }

    public getMouseDomElementPosition(params: {canvasMouseEvent: MouseEvent}): Vec3<"dom_element_pixels">{
        let ev = params.canvasMouseEvent;
        return new Vec3(vec3.fromValues(ev.offsetX, ev.offsetY, 0), "dom_element_pixels")
    }

    public getMouseNdcPosition(params: {canvasMouseEvent: MouseEvent}): Vec3<"ndc"> | undefined{
        let ev = params.canvasMouseEvent
        let offsetY = ev.offsetY//gl viewport +y points up, but mouse events have +y pointing down

        let position_ndc = vec3.fromValues(
            (ev.offsetX - (this.geometry.width / 2)) / (this.geometry.width / 2),
           -(ev.offsetY - (this.geometry.height / 2)) / (this.geometry.height / 2), //gl viewport +y points up, but mouse events have +y pointing down
            0, //Assume slicing plane is in the MIDDLE of clip space
        )
        // console.log(`ev.offsetY: ${ev.offsetY}`)
        // console.log(`ClipPosition: ${vecToString(position_c)}`)
        return new Vec3(position_ndc, "ndc")
    }

    public getMouseWorldPosition(ev: MouseEvent): Vec3<"world">{
        let position_ndc = this.getMouseNdcPosition(ev)
        let position: Vec3<"world"> = position_ndc.transformedWith(this.getCamera().getClipToWorld())
        // console.log(`WorldPosition: ${vecToString(position.raw)}`)
        return position
    }

    public getMouseVoxelPosition(ev: MouseEvent): Vec3<"voxel">{
        const world_to_voxel = this.viewportDriver.getVoxelToWorldMatrix({voxelSizeInNm: this.datasource.spatial_resolution}).inverted()
        let position_w: Vec3<"world"> = this.getMouseWorldPosition(ev)
        let position_voxel = position_w.transformedWith(world_to_voxel)
        // console.log(`DataPosition(nm): ${vecToString(position_voxel)} ======================`)
        return position_voxel
    }

    public render = (brushStrokes: Array<[Color, BrushStroke[]]>, renderer: BrushRenderer) => {
        renderer.render({
            brush_strokes: brushStrokes,
            camera: this.getCamera(),
            voxelToWorld: this.viewportDriver.getVoxelToWorldMatrix({voxelSizeInNm: this.datasource.spatial_resolution}),
            renderParams: new RenderParams({
                viewportConfig: new ViewportConfig({

                })
                scissorConfig: new ScissorConfig({
                    x: viewport_geometry.left,
                    y: viewport_geometry.bottom,
                    height: viewport_geometry.height,
                    width: viewport_geometry.width,
                }),
                clearConfig: new ClearConfig({
                    a: 0.0,
                }),
            })
        })
    }

    public destroy(){
        removeElement(this.element)
    }
}

export class BrushingOverlay{asdasd
    public readonly datasource: FsDataSource
    public readonly viewer: Viewer
    public readonly element: HTMLCanvasElement
    private readonly brush_stroke_handler: IBrushStrokeHandler
    public readonly gl: WebGL2RenderingContext

    private viewports: Array<OverlayViewport> = []
    private brushing_enabled: boolean = false

    public constructor(params: {
        datasource: FsDataSource,
        viewer: Viewer,
        brush_stroke_handler: IBrushStrokeHandler,
        gl: WebGL2RenderingContext
    }){
        this.datasource = datasource
        this.viewer = viewer
        this.brush_stroke_handler = brush_stroke_handler
        this.gl = gl
        this.element = gl.canvas as HTMLCanvasElement;
        this.viewports = viewport_drivers.map((viewport_driver) => {
            const viewport = new OverlayViewport({datasource, brush_stroke_handler: this.brush_stroke_handler, viewport_driver, gl: this.gl})
            viewport.setBrushingEnabled(this.brushing_enabled)
            return viewport
        })



        // this.element.addEventListener("mousedown", (mouseDownEvent: MouseEvent) => {
        //     let currentBrushStroke = brush_stroke_handler.handleNewBrushStroke({
        //         start_position: this.getMouseVoxelPosition(mouseDownEvent),
        //         camera_orientation: Quat.identity<"voxel">()//FIXME!!! viewport_driver.getCameraPose_uvw().orientation_uvw,
        //     })

        //     let scribbleHandler = (mouseMoveEvent: MouseEvent) => {
        //         currentBrushStroke.interpolate_until_point_uvw(this.getMouseVoxelPosition(mouseMoveEvent))
        //     }

        //     let handlerCleanup = () => {
        //         this.element.removeEventListener("mousemove", scribbleHandler)
        //         document.removeEventListener("mouseup", handlerCleanup)
        //         brush_stroke_handler.handleFinishedBrushStroke(currentBrushStroke)
        //     }
        //     this.element.addEventListener("mousemove", scribbleHandler)
        //     document.addEventListener("mouseup", handlerCleanup)
        // })
    }

    public refresh = () => {
        let viewportDrivers = this.viewer.getViewportDrivers();
        this.viewports = viewportDrivers.map((viewport_driver) => {
            const viewport = new OverlayViewport({datasource, brush_stroke_handler: this.brush_stroke_handler, viewport_driver, gl: this.gl})
            viewport.setBrushingEnabled(this.brushing_enabled)
            return viewport
        })
    }

    public setBrushingEnabled(enabled: boolean){\
        if(enabled){
            this.element.style.pointerEvents = "auto"
            this.element.classList.add("ItkPencilCursor")

        }else{
            this.element.style.pointerEvents = "none"
            this.element.classList.remove("ItkPencilCursor")
        }
        this.brushing_enabled = enabled
    }

    public render = (brushStrokes: Array<[Color, BrushStroke[]]>, renderer: BrushRenderer) => {
        coverContents({target: this.trackedElement, overlay: this.element})
        this.element.width = this.element.scrollWidth
        this.element.height = this.element.scrollHeight
        this.viewports.forEach((viewport) => {
            viewport.render(brushStrokes, renderer)
        })
    }

    public destroy(){
        this.viewports.forEach(viewport => viewport.destroy())
    }
}
