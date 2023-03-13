import { Color, FsDataSource, PrecomputedChunksDataSource, Session } from "../../client/ilastik";
import { INativeView, IViewerDriver } from "../../drivers/viewer_driver";
import { uuidv4 } from "../../util/misc";
import { Url } from "../../util/parsed_url";
import { CssClasses } from "../css_classes";
import { Button } from "./input_widget";
import { ToggleButton } from "./value_input_widget";
import { ContainerWidget, Div, Label, Paragraph, Span } from "./widget";

class LayerWidget{
    public readonly nativeView: INativeView;

    public readonly element: Div;
    private readonly visibilityInput: ToggleButton;
    // private readonly opacitySlider: RangeInput;

    public constructor(params: {
        parentElement: ContainerWidget<any> | undefined,
        nativeView: INativeView,
        name: string,
    }){
        this.nativeView = params.nativeView

        this.element = new Div({parentElement: params.parentElement, cssClasses: [CssClasses.ItkLaneLayerWidget]})

        new Label({parentElement: this.element, innerText: params.name})
        this.visibilityInput = new ToggleButton({
            text: "👁️",
            parentElement: this.element,
            value: true,
            onClick: () => {
                this.nativeView.reconfigure({isVisible: this.visibilityInput.value})
            }
        })

        // new ToggleVisibilityButton({
        //     parentElement: this.element,
        //     text: "⚙",
        //     subject: new Div({
        //         parentElement: this.element,
        //         children: [
        //             new Label({parentElement: undefined, innerText: "opacity: "}),
        //             this.opacitySlider = new RangeInput({parentElement: undefined, min: 0, max: 1, value: 0.5, step: 0.05, onChange: () => {
        //                 this.nativeView.reconfigure({opacity: this.opacitySlider.value})
        //             }})
        //         ]
        //     })
        // })
    }

    public enableVisibilityControls(enable: boolean){
        this.visibilityInput.disabled = !enable
    }

    public get isVisible(): boolean{
        return this.visibilityInput.value
    }

    public destroy(){
        this.nativeView.close()
        this.element.destroy()
    }
}

export class RawDataLayerWidget extends LayerWidget{
    public readonly datasource: PrecomputedChunksDataSource;

    constructor(params: {
        parentElement: ContainerWidget<any> | undefined,
        datasource: PrecomputedChunksDataSource,
        opacity: number,
        nativeView: INativeView,
    }){
        super({...params, name: "Raw Data"})
        this.datasource = params.datasource
    }

    public static async create(params: {
        parentElement: ContainerWidget<any> | undefined,
        driver: IViewerDriver,
        session: Session,
        datasource: PrecomputedChunksDataSource,
    }): Promise<RawDataLayerWidget | Error>{
        const opacity = 1
        let channelColors: Color[] = []
        if(params.datasource.shape.c == 3){
            channelColors = [
                new Color({r: 255, g: 0, b: 0}), new Color({r: 0, g: 255, b: 0}), new Color({r: 0, g: 0, b: 255}),
            ]
        }else{
            channelColors = []
            for(let i=0; i<params.datasource.shape.c; i++){
                channelColors.push(new Color({r: 255, g: 255, b: 255})) //FIXME
            }
        }
        const nativeView = await params.driver.openUrl({
            isVisible: true,
            name: `raw_${params.datasource.url.name}_${uuidv4()}`,
            url: params.datasource.getStrippedUrl(params.session),
            channelColors,
            opacity,
        })
        if(nativeView instanceof Error){
            return nativeView
        }
        return new RawDataLayerWidget({
            ...params,
            opacity,
            nativeView,
        })
    }

    public reconfigure(params: {
        isVisible?: boolean,
        channelColors?: Color[],
        opacity?: number
    }){
        return this.nativeView.reconfigure({
            isVisible: params.isVisible,
            channelColors: params.channelColors,
            opacity: params.opacity,
        })
    }
}

export class PredictionsLayerWidget extends LayerWidget{
    readonly rawData: FsDataSource;
    private _classifierGeneration: number;
    private channelColors: Color[]


    constructor(params: {
        parentElement: ContainerWidget<any>,
        rawData: FsDataSource,
        classifierGeneration: number,
        channelColors: Color[],
        opacity: number,
        nativeView: INativeView,
    }){
        super({...params, name: "Pixel Predictions"})
        this.rawData = params.rawData
        this._classifierGeneration = params.classifierGeneration
        this.channelColors = params.channelColors
    }

    public static async create(params: {
        parentElement: ContainerWidget<any>,
        driver: IViewerDriver,
        session: Session,
        rawData: FsDataSource,
        classifierGeneration: number,
        channelColors: Color[],
        isVisible: boolean,
    }): Promise<PredictionsLayerWidget | Error>{
        const opacity = 0.5
        const nativeView = await params.driver.openUrl({
            url: params.session.sessionUrl
                .updatedWith({datascheme: "precomputed"})
                .joinPath(`predictions/raw_data=${params.rawData.toBase64()}/generation=${params.classifierGeneration}`),
            channelColors: params.channelColors,
            opacity,
            isVisible: params.isVisible,
            name: `preds_for_${params.rawData.url.name}__${params.classifierGeneration}`
        })
        if(nativeView instanceof Error){
            return nativeView
        }
        return new PredictionsLayerWidget({
            opacity,
            nativeView,
            channelColors: params.channelColors,
            classifierGeneration: params.classifierGeneration,
            parentElement: params.parentElement,
            rawData: params.rawData,
        })
    }

    public get classifierGeneration(): number{
        return this._classifierGeneration
    }

    public reconfigure(params: {
        source?: {session: Session, classifierGeneration: number},
        // isVisible?: boolean | undefined,
        channelColors?: Color[],
        // opacity?: number
    }){
        if(params.source && params.source.classifierGeneration < this._classifierGeneration){
            return
        }

        // let isVisible = params.isVisible === undefined ? this.isVisible : params.isVisible
        let channelColors = params.channelColors || this.channelColors
        // let opacity = params.opacity === undefined ? this.opacity : params.opacity

        if(
            // isVisible === this.isVisible &&
            channelColors.length == this.channelColors.length &&
            channelColors.every((color, idx) => color.equals(this.channelColors[idx]))
        ){
            return
        }
        this.channelColors = channelColors

        this._classifierGeneration = params.source?.classifierGeneration || this._classifierGeneration
        let url: Url | undefined = params.source && params.source.session.sessionUrl
            .updatedWith({datascheme: "precomputed"})
            .joinPath(`predictions/raw_data=${this.rawData.toBase64()}/generation=${params.source.classifierGeneration}`)
        return this.nativeView.reconfigure({...params, url})
    }
}

export class PixelClassificationLaneWidget{
    private element: Div;
    private predictionsWidget: PredictionsLayerWidget | undefined = undefined
    private rawDataWidget: RawDataLayerWidget;
    private driver: IViewerDriver;
    private readonly visibilityInput: ToggleButton;

    private constructor(params: {
        parentElement: ContainerWidget<any>,
        name: string,
        rawDataWidget: RawDataLayerWidget,
        driver: IViewerDriver,
        isVisible: boolean,
        onDestroyed: (lane: PixelClassificationLaneWidget) => void,
        onVisibilityChanged: (lane: PixelClassificationLaneWidget) => void,
    }){
        this.element = new Div({parentElement: params.parentElement, cssClasses: [CssClasses.ItkLaneWidget], children: [
            new Paragraph({parentElement: undefined, children: [
                new Span({parentElement: undefined, innerText: params.name}),
                this.visibilityInput = new ToggleButton({
                    parentElement: undefined,
                    text: "👁️",
                    value: params.isVisible,
                    onClick: () => {
                        this.setVisible(this.visibilityInput.value)
                        params.onVisibilityChanged(this)
                    }
                }),
                new Button({inputType: "button", text: "✖", parentElement: undefined, onClick: () => {
                    this.destroy()
                    params.onDestroyed(this)
                }}),
            ]}),

        ]})



        this.rawDataWidget = params.rawDataWidget
        this.element.appendChild(params.rawDataWidget.element) //FIXME?

        this.driver = params.driver
        this.setVisible(params.isVisible)
    }

    public static async create(params: {
        session: Session,
        driver: IViewerDriver,
        parentElement: ContainerWidget<any>,
        rawData: FsDataSource,
        isVisible: boolean,
        name: string,
        onDestroyed: (lane: PixelClassificationLaneWidget) => void,
        onVisibilityChanged: (lane: PixelClassificationLaneWidget) => void,
    }): Promise<PixelClassificationLaneWidget | Error>{
        if(!(params.rawData instanceof PrecomputedChunksDataSource)){
            return new Error(`Unsupported datasource type `) //FIXME: maybe driver sould determine this
        }
        let rawDataWidget = await RawDataLayerWidget.create({
            datasource: params.rawData,
            driver: params.driver,
            parentElement: undefined,
            session: params.session,
        })
        if(rawDataWidget instanceof Error){
            return rawDataWidget
        }
        return new PixelClassificationLaneWidget({
            driver: params.driver,
            isVisible: params.isVisible,
            name: params.name,
            onDestroyed: params.onDestroyed,
            onVisibilityChanged: params.onVisibilityChanged,
            parentElement: params.parentElement,
            rawDataWidget,
        })
    }

    public destroy(){
        this.rawDataWidget.destroy()
        this.predictionsWidget?.destroy()
        this.element.destroy()
    }

    public get isVisible(): boolean{
        return this.visibilityInput.value
    }
    public get rawData(): FsDataSource{
        return this.rawDataWidget.datasource
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
        this.rawDataWidget.enableVisibilityControls(isVisible)
        this.predictionsWidget?.enableVisibilityControls(isVisible)
    }

    public async refreshPredictions(params: {
        session: Session, classifierGeneration: number, channelColors: Color[]
    }): Promise<Error | undefined>{
        const predictionsSnapshot = this.predictionsWidget
        if(predictionsSnapshot instanceof PredictionsLayerWidget){
            predictionsSnapshot.reconfigure({
                source: {classifierGeneration: params.classifierGeneration, session: params.session},
                channelColors: params.channelColors
            })
            return
        }
        const predictionsLayerWidget = await PredictionsLayerWidget.create({
            parentElement: this.element, //FIXME?
            session: params.session,
            channelColors: params.channelColors,
            classifierGeneration: params.classifierGeneration,
            rawData: this.rawData,
            driver: this.driver,
            isVisible: this.isVisible
        })
        if(predictionsLayerWidget instanceof Error){
            return predictionsLayerWidget //FIXME: then what?
        }
        //check if we've been called while we were awaiting
        if(this.predictionsWidget instanceof PredictionsLayerWidget){
            if(this.predictionsWidget.classifierGeneration > predictionsLayerWidget.classifierGeneration){
                predictionsLayerWidget.destroy()
                return undefined
            }else{
                this.predictionsWidget.destroy()
            }
        }
        this.predictionsWidget = predictionsLayerWidget
        this.setVisible(this.isVisible)
        return undefined
    }

    public closePredictions(){
        this.predictionsWidget?.destroy()
        this.predictionsWidget = undefined
    }
}