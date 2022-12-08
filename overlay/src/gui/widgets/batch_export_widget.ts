import { CollapsableWidget } from "./collapsable_applet_gui";

export class BatchExportWidget{
    element: HTMLDetailsElement;

    constructor(params: {parentElement: HTMLElement}){
        this.element = new CollapsableWidget({
            display_name: "Batch Export", parentElement: params.parentElement
        }).element

    }
}