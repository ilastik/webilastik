import { IViewerDriver } from "../.."

export class DataSelectionWidget{
    public readonly viewer_driver: IViewerDriver
    public constructor({viewer_driver}: {
        viewer_driver: IViewerDriver
    }){
        this.viewer_driver = viewer_driver
    }

    // public displayState(event_payload: any){
    // }
}
