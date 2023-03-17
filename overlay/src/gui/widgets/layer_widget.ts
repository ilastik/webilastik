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

    //colors by Sasha Trubetskoy: https://sashamaps.net/docs/resources/20-colors/
    public static readonly colorMap = [
        new Color({r: 230, g: 25, b: 75}),
        new Color({r: 60, g: 180, b: 75}),
        new Color({r: 255, g: 225, b: 25}),
        new Color({r: 0, g: 130, b: 200}),
        new Color({r: 245, g: 130, b: 48}),
        new Color({r: 145, g: 30, b: 180}),
        new Color({r: 70, g: 240, b: 240}),
        new Color({r: 240, g: 50, b: 230}),
        new Color({r: 210, g: 245, b: 60}),
        new Color({r: 250, g: 190, b: 212}),
        new Color({r: 0, g: 128, b: 128}),
        new Color({r: 220, g: 190, b: 255}),
        new Color({r: 170, g: 110, b: 40}),
        new Color({r: 255, g: 250, b: 200}),
        new Color({r: 128, g: 0, b: 0}),
        new Color({r: 170, g: 255, b: 195}),
        new Color({r: 128, g: 128, b: 0}),
        new Color({r: 255, g: 215, b: 180}),
        new Color({r: 0, g: 0, b: 128}),
        new Color({r: 128, g: 128, b: 128}),
        new Color({r: 255, g: 255, b: 255}),
        new Color({r: 0, g: 0, b: 0}),
    ]

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
        let channelColors: Color[]
        if(params.datasource.shape.c == 3){
            channelColors = [
                new Color({r: 255, g: 0, b: 0}), new Color({r: 0, g: 255, b: 0}), new Color({r: 0, g: 0, b: 255}),
            ]
        }else if(params.datasource.shape.c == 1){
            channelColors = [new Color({r: 255, g: 255, b: 255})]
        }else{
            channelColors = this.colorMap.slice(0, params.datasource.shape.c)
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
    public channelColors: Color[]

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
        channelColors?: Color[],
    }){
        this.channelColors = params.channelColors || this.channelColors
        this._classifierGeneration = params.source?.classifierGeneration || this._classifierGeneration
        let url: Url | undefined = params.source && params.source.session.sessionUrl
            .updatedWith({datascheme: "precomputed"})
            .joinPath(`predictions/raw_data=${this.rawData.toBase64()}/generation=${params.source.classifierGeneration}`)
        return this.nativeView.reconfigure({...params, url})
    }
}

export class PredictionsParams{
    public readonly classifierGeneration: number
    public readonly channelColors: Color[]
    public constructor(params: {classifierGeneration: number, channelColors: Color[]}){
        this.classifierGeneration = params.classifierGeneration
        this.channelColors = params.channelColors
    }

    public hasSameColorsAs(other: PredictionsParams | PredictionsLayerWidget){
        return this.channelColors.length == other.channelColors.length &&
            this.channelColors.every((color, idx) => color.equals(other.channelColors[idx]))
    }

    public equals(other: PredictionsParams | PredictionsLayerWidget): boolean{
        return this.classifierGeneration == other.classifierGeneration && this.hasSameColorsAs(other)
    }

    public supersedes(old: PredictionsParams | PredictionsLayerWidget): boolean{
        if(this.classifierGeneration > old.classifierGeneration){
            return true
        }
        if(this.classifierGeneration < old.classifierGeneration){
            return false
        }
        return !this.hasSameColorsAs(old)
    }
}

export class PixelClassificationLaneWidget{
    private element: Div;
    private rawDataWidget: RawDataLayerWidget;
    private driver: IViewerDriver;
    private readonly visibilityInput: ToggleButton;

    private _predictionsWidget: PredictionsLayerWidget | undefined | PredictionsParams = undefined
    private get predictionsWidget(): PredictionsLayerWidget | undefined{
        if(this._predictionsWidget instanceof PredictionsLayerWidget){
            return this._predictionsWidget
        }
        return undefined
    }

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
            this.predictionsWidget?.nativeView.reconfigure({isVisible: this.predictionsWidget.isVisible})
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
        const predictionParams = new PredictionsParams(params)
        const predictionsSnapshot = this._predictionsWidget

        if(predictionsSnapshot !== undefined && !predictionParams.supersedes(predictionsSnapshot)){
            return
        }

        if(predictionsSnapshot instanceof PredictionsLayerWidget){
            predictionsSnapshot.reconfigure({
                source: {classifierGeneration: params.classifierGeneration, session: params.session},
                channelColors: params.channelColors
            })
            return
        }

        this._predictionsWidget = predictionParams
        const predictionsLayerWidget = await PredictionsLayerWidget.create({
            parentElement: this.element, //FIXME?
            session: params.session,
            channelColors: params.channelColors,
            classifierGeneration: params.classifierGeneration,
            rawData: this.rawData,
            driver: this.driver,
            isVisible: this.isVisible
        })
        //check if we've been called while we were awaiting
        if(this._predictionsWidget !== predictionParams){
            if(!(predictionsLayerWidget instanceof Error)){
                predictionsLayerWidget.destroy()
            }
            return undefined
        }

        if(predictionsLayerWidget instanceof Error){
            this._predictionsWidget = undefined
            return
        }
        this._predictionsWidget = predictionsLayerWidget
        this.setVisible(this.isVisible)
        return undefined
    }

    public closePredictions(){
        this.predictionsWidget?.destroy()
        this._predictionsWidget = undefined
    }
}