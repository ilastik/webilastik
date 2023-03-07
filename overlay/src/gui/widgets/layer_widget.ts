import { Color, FsDataSource, Session } from "../../client/ilastik";
import { INativeView, IPredictionsView, IRawDataView, IViewerDriver } from "../../drivers/viewer_driver";
import { Button } from "./input_widget";
import { ToggleVisibilityButton } from "./toggle_visibility_button";
import { BooleanInput, RangeInput } from "./value_input_widget";
import { ContainerWidget, Div, Label, Paragraph, Span } from "./widget";

class LayerWidget<VIEW extends INativeView>{
    public readonly nativeView: VIEW;

    public readonly element: Div;
    private readonly visibilityInput: BooleanInput;
    private readonly opacitySlider: any;

    public constructor(params: {
        parentElement: ContainerWidget<any> | undefined,
        isVisible: boolean,
        nativeView: VIEW,
    }){
        this.nativeView = params.nativeView

        this.element = new Div({parentElement: params.parentElement})

        new Label({parentElement: this.element, innerText: "👁️ "})
        this.visibilityInput = new BooleanInput({
            parentElement: this.element,
            value: params.isVisible,
            onClick: () => {
                this.nativeView.reconfigure({isVisible: this.visibilityInput.value})
            }
        })

        new ToggleVisibilityButton({
            parentElement: this.element,
            text: "⚙",
            subject: new Div({
                parentElement: this.element,
                children: [
                    new Label({parentElement: undefined, innerText: "opacity: "}),
                    this.opacitySlider = new RangeInput({parentElement: undefined, min: 0, max: 1, value: 0.5, step: 0.05, onChange: () => {
                        this.nativeView.reconfigure({opacity: this.opacitySlider.value})
                    }})
                ]
            })
        })
    }

    public get isVisible(): boolean{
        return this.visibilityInput.value
    }

    public destroy(){
        this.nativeView.close()
    }
}

export class PixelClassificationLaneWidget{
    private element: Div;
    private predictionsWidget: LayerWidget<IPredictionsView> | undefined = undefined
    private driver: IViewerDriver;
    private rawDataWidget: LayerWidget<IRawDataView>;
    private readonly visibilityInput: BooleanInput;

    private constructor(params: {
        parentElement: ContainerWidget<any>,
        name: string,
        rawDataNativeView: IRawDataView,
        driver: IViewerDriver,
        isVisible: boolean,
        onDestroyed: () => void,
        onVisibilityChanged: () => void,
    }){
        this.element = new Div({parentElement: params.parentElement, children: [
            new Paragraph({parentElement: undefined, children: [
                new Span({parentElement: undefined, innerText: params.name})
            ]}),
            new Button({inputType: "button", text: "✖", parentElement: undefined, onClick: () => {
                this.destroy()
                params.onDestroyed()
            }}),
            this.visibilityInput = new BooleanInput({
                parentElement: undefined,
                value: params.isVisible,
                onClick: () => {
                    this.setVisible(this.visibilityInput.value)
                    params.onVisibilityChanged()
                }
            })
        ]})

        this.rawDataWidget = new LayerWidget({
            isVisible: true,
            nativeView: params.rawDataNativeView,
            parentElement: this.element,
        })

        this.driver = params.driver
        this.setVisible(params.isVisible)
    }

    public destroy(){
        this.rawDataWidget.destroy()
        this.predictionsWidget?.destroy()
    }

    public get isVisible(): boolean{
        return this.visibilityInput.value
    }
    public get rawData(): FsDataSource{
        return this.rawDataWidget.nativeView.datasource
    }

    public setVisible(isVisible: boolean){
        if(isVisible){
            this.rawDataWidget.nativeView.reconfigure({isVisible: this.rawDataWidget.isVisible})
            this.predictionsWidget?.nativeView.reconfigure({isVisible: this.rawDataWidget.isVisible})
        }else{
            this.rawDataWidget.nativeView.reconfigure({isVisible: false})
            this.predictionsWidget?.nativeView.reconfigure({isVisible: false})
        }
        this.visibilityInput.value = isVisible
    }

    public static create(params: {
        session: Session,
        driver: IViewerDriver,
        parentElement: ContainerWidget<any>,
        rawData: FsDataSource,
        isVisible: boolean,
        name: string,
        onDestroyed: () => void,
        onVisibilityChanged: () => void,
    }): PixelClassificationLaneWidget | Error{
        let rawDataNativeViewResult = params.driver.openDataSource({
            session: params.session,
            datasource: params.rawData,
            isVisible: params.isVisible,
            name: `raw_data__${params.rawData.url.name}`
        })
        if(rawDataNativeViewResult instanceof Error){
            return rawDataNativeViewResult
        }
        return new PixelClassificationLaneWidget({
            driver: params.driver,
            parentElement: params.parentElement,
            name: params.name,
            rawDataNativeView: rawDataNativeViewResult,
            isVisible: params.isVisible,
            onDestroyed: params.onDestroyed,
            onVisibilityChanged: params.onVisibilityChanged,
        })
    }

    public refreshPredictions(params: {
        session: Session, classifierGeneration: number, channelColors: Color[]
    }): Error | undefined{
        if(this.predictionsWidget){
            this.predictionsWidget.nativeView.reconfigure({
                source: {classifierGeneration: params.classifierGeneration, session: params.session},
                channelColors: params.channelColors
            })
            return
        }
        const predictionsNativeViewResult = this.driver.openPixelPredictions({
            session: params.session,
            channelColors: params.channelColors,
            classifierGeneration: params.classifierGeneration,
            isVisible: true,
            name: `predictions_for_${this.rawDataWidget.nativeView.datasource.url.name}`,
            opacity: 0.5,
            rawData: this.rawDataWidget.nativeView.datasource,
        })
        if(predictionsNativeViewResult instanceof Error){
            return predictionsNativeViewResult
        }
        this.predictionsWidget = new LayerWidget({
            isVisible: true,
            nativeView: predictionsNativeViewResult,
            parentElement: this.element,
        })
        return undefined
    }

    public closePredictions(){
        this.predictionsWidget?.destroy()
        this.predictionsWidget = undefined
    }
}