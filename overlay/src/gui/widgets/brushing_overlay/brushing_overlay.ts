import { vec3 } from 'gl-matrix'
import { BrushRenderer } from './brush_renderer'
// import { BrushShaderProgram } from './brush_stroke'
import { OrthoCamera } from './camera'
// import { PerspectiveCamera } from './camera'
import { ClearConfig, RenderParams, ScissorConfig } from '../../../gl/gl'
import { coverContents, insertAfter, removeElement } from '../../../util/misc'
import { IViewportDriver } from '../../../drivers/viewer_driver'
import { IBrushStrokeHandler, BrushStroke } from './brush_stroke'
import { Color, FsDataSource } from '../../../client/ilastik'
import { Quat, Vec3 } from '../../../util/ooglmatrix'


export class OverlayViewport{
    public readonly gl: WebGL2RenderingContext
    public readonly canvas: HTMLCanvasElement
    public readonly viewport_driver: IViewportDriver
    public readonly element: HTMLElement
    public readonly datasource: FsDataSource

    public constructor({
        datasource,
        viewport_driver,
        brush_stroke_handler,
        gl,
    }: {
        datasource: FsDataSource,
        viewport_driver: IViewportDriver,
        brush_stroke_handler: IBrushStrokeHandler,
        gl: WebGL2RenderingContext,
    }){
        this.datasource = datasource
        this.viewport_driver = viewport_driver
        this.gl = gl
        this.canvas = this.gl.canvas as HTMLCanvasElement
        this.element = document.createElement("div")
        this.element.classList.add("OverlayViewport")


        document.body.lastElementChild
        const injection_params = viewport_driver.getInjectionParams ? viewport_driver.getInjectionParams() : {
            precedingElement: undefined,
            zIndex: undefined,
        }
        insertAfter({
            new_element: this.element,
            reference: injection_params.precedingElement || document.body.lastElementChild as HTMLElement
        })
        this.element.style.zIndex = injection_params.zIndex || "auto"

        if((window as any)["ilastik_debug"]){
            let colors = ["red", "green", "blue", "orange", "purple", "lime", "olive", "navy"]
            this.element.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)]
            this.element.style.filter = "opacity(0.3)"
        }

        this.element.addEventListener("mousedown", (mouseDownEvent: MouseEvent) => {
            let currentBrushStroke = brush_stroke_handler.handleNewBrushStroke({
                start_position: this.getMouseVoxelPosition(mouseDownEvent),
                camera_orientation: Quat.identity<"voxel">()//FIXME!!! viewport_driver.getCameraPose_uvw().orientation_uvw,
            })

            let scribbleHandler = (mouseMoveEvent: MouseEvent) => {
                currentBrushStroke.interpolate_until_point_uvw(this.getMouseVoxelPosition(mouseMoveEvent))
            }

            let handlerCleanup = () => {
                this.element.removeEventListener("mousemove", scribbleHandler)
                document.removeEventListener("mouseup", handlerCleanup)
                brush_stroke_handler.handleFinishedBrushStroke(currentBrushStroke)
            }
            this.element.addEventListener("mousemove", scribbleHandler)
            document.addEventListener("mouseup", handlerCleanup)
        })
    }

    public setBrushingEnabled(enabled: boolean){
        if(enabled){
            this.element.style.pointerEvents = "auto"
            this.element.classList.add("ItkPencilCursor")

        }else{
            this.element.style.pointerEvents = "none"
            this.element.classList.remove("ItkPencilCursor")
        }
    }

    public getCamera(): OrthoCamera{
        // - near and far have to be such that a voxel in any orientation would fit between them;
        const world_units_per_pixel = this.viewport_driver.getZoomInWorldUnitsPerPixel()
        // const voxel_diagonal_length = vec3.length(mat4.getScaling(vec3.create(), this.viewport_driver.getVoxelToWorldMatrix()))
        const viewport_width_w = this.element.scrollWidth * world_units_per_pixel;
        const viewport_height_w = this.element.scrollHeight * world_units_per_pixel;
        const camera_pose_w = this.viewport_driver.getCameraPose()
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

    public getMouseNdcPosition(ev: MouseEvent): Vec3<"ndc">{
        let position_ndc = vec3.fromValues(
            (ev.offsetX - (this.element.scrollWidth / 2)) / (this.element.scrollWidth / 2),
           -(ev.offsetY - (this.element.scrollHeight / 2)) / (this.element.scrollHeight / 2), //gl viewport +y points up, but mouse events have +y pointing down
            0, //Assume slicing plane is in the MIDDLE of clip space
        )
        // console.log(`ev.offsetY: ${ev.offsetY}`)
        // console.log(`ClipPosition: ${vecToString(position_c)}`)
        return new Vec3(position_ndc)
    }

    public getMouseWorldPosition(ev: MouseEvent): Vec3<"world">{
        let position_ndc = this.getMouseNdcPosition(ev)
        let position: Vec3<"world"> = position_ndc.transformedWith(this.getCamera().getClipToWorld())
        // console.log(`WorldPosition: ${vecToString(position.raw)}`)
        return position
    }

    public getMouseVoxelPosition(ev: MouseEvent): Vec3<"voxel">{
        const world_to_voxel = this.viewport_driver.getVoxelToWorldMatrix({voxelSizeInNm: this.datasource.spatial_resolution}).inverted()
        let position_w: Vec3<"world"> = this.getMouseWorldPosition(ev)
        let position_voxel = position_w.transformedWith(world_to_voxel)
        // console.log(`DataPosition(nm): ${vecToString(position_voxel)} ======================`)
        return position_voxel
    }

    public render = (brushStrokes: Array<[Color, BrushStroke[]]>, renderer: BrushRenderer) => {
        const viewport_geometry = this.viewport_driver.getGeometry()
        coverContents({
            target: this.canvas,
            overlay: this.element,
            offsetLeft: viewport_geometry.left,
            offsetBottom: viewport_geometry.bottom,
            height: viewport_geometry.height,
            width: viewport_geometry.width,
        })
        this.gl.viewport(
            viewport_geometry.left,
            viewport_geometry.bottom,
            viewport_geometry.width,
            viewport_geometry.height
        ); //FIXME: shuold aspect play a role here?

        renderer.render({
            brush_strokes: brushStrokes,
            camera: this.getCamera(),
            voxelToWorld: this.viewport_driver.getVoxelToWorldMatrix({voxelSizeInNm: this.datasource.spatial_resolution}),
            renderParams: new RenderParams({
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

export class BrushingOverlay{
    public readonly datasource: FsDataSource
    public readonly trackedElement: HTMLElement
    public readonly element: HTMLCanvasElement
    private readonly brush_stroke_handler: IBrushStrokeHandler
    public readonly gl: WebGL2RenderingContext

    private viewports: Array<OverlayViewport> = []
    private brushing_enabled: boolean = false

    public constructor({
        datasource,
        trackedElement,
        viewport_drivers,
        brush_stroke_handler,
        gl,
    }: {
        datasource: FsDataSource,
        trackedElement: HTMLElement,
        viewport_drivers: Array<IViewportDriver>,
        brush_stroke_handler: IBrushStrokeHandler,
        gl: WebGL2RenderingContext
    }){
        this.datasource = datasource
        this.trackedElement = trackedElement;
        this.brush_stroke_handler = brush_stroke_handler
        this.gl = gl
        this.element = gl.canvas as HTMLCanvasElement;
        this.viewports = viewport_drivers.map((viewport_driver) => {
            const viewport = new OverlayViewport({datasource, brush_stroke_handler: this.brush_stroke_handler, viewport_driver, gl: this.gl})
            viewport.setBrushingEnabled(this.brushing_enabled)
            return viewport
        })
    }

    public setBrushingEnabled(enabled: boolean){
        this.brushing_enabled = enabled
        this.viewports.forEach(viewport => viewport.setBrushingEnabled(enabled))
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
