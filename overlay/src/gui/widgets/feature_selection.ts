import { CollapsableWidget } from './collapsable_applet_gui';
import { Applet } from '../../client/applets/applet';
import { Session, IlpFeatureExtractor, FeatureClassName } from '../../client/ilastik';
import { AddFeatureExtractorsParamsDto, FeatureSelectionAppletStateDto, RemoveFeatureExtractorsParamsDto } from '../../client/dto';
import { BooleanInput } from './value_input_widget';
import { Paragraph, Table, TableData, TableHeader, TableRow } from './widget';
import { Button } from './input_widget';
import { CssClasses } from '../css_classes';

// class FeatureCheckbox<FE extends FeatureExtractor>{
//     constructor()
// }

type Scale = number;

class FeatureSelectionCheckbox extends BooleanInput{
    private _upstreamValue: boolean;

    constructor(params: {
        parentElement: HTMLElement | undefined,
        value: boolean,
        upstreamValue: boolean,
    }){
        super(params)
        this._upstreamValue = params.upstreamValue
        this.highlight()
        this.element.addEventListener("click", () => this.highlight())
    }
    public set value(val: boolean){
        this.element.checked = val
        this.highlight()
    }
    public get value(): boolean{
        return this.element.checked
    }
    public set upstreamValue(val: boolean){
        this._upstreamValue = val
        this.highlight()
    }
    private highlight(){
        this.element.style.boxShadow = this.isHighlighted() ? "0px 0px 0px 4px orange" : ""
    }
    public isHighlighted(): boolean{
        return this.value != this._upstreamValue
    }
}

export class FeatureSelectionWidget extends Applet<{feature_extractors: IlpFeatureExtractor[]}>{
    public readonly element: HTMLElement;
    private checkboxes = new Map<FeatureClassName, Map<Scale, FeatureSelectionCheckbox>>();

    public constructor({name, session, parentElement, help}: {
        name: string, session: Session, parentElement: HTMLElement, help: string[]
    }){
        super({
            name,
            session,
            deserializer: (data) => {
                let message = FeatureSelectionAppletStateDto.fromJsonValue(data)
                if(message instanceof Error){
                    throw `FIXME!! ${message.message}`
                }
                return {
                    feature_extractors: message.feature_extractors.map(msg => IlpFeatureExtractor.fromDto(msg))
                }
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Select Image Features", parentElement, help}).element
        this.element.classList.add("ItkFeatureSelectionWidget")

        const scales: Array<Scale> = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]

        const table = new Table({parentElement: this.element, cssClasses: [CssClasses.ItkTable], children: [
            new TableRow({parentElement: undefined, children: [
                new TableHeader({innerText: 'Feature / sigma', parentElement: undefined}),
                ...scales.map(scale => new TableHeader({parentElement: undefined, innerText: scale.toFixed(1).toString()}))
            ]})
        ]})

        let featureNames: Array<FeatureClassName> = [
            "Gaussian Smoothing",
            "Laplacian of Gaussian",
            "Gaussian Gradient Magnitude",
            "Difference of Gaussians",
            "Structure Tensor Eigenvalues",
            "Hessian of Gaussian Eigenvalues",
        ]

        featureNames.forEach(feature_name => {
            let scalesMap = new Map()
            this.checkboxes.set(feature_name, scalesMap)
            let tr = new TableRow({parentElement: table, children: [
                new TableData({parentElement: undefined, innerText: feature_name})
            ]})

            scales.forEach(scale => {
                if(scale == 0.3 && feature_name != "Gaussian Smoothing"){
                    new TableData({parentElement: tr})
                    return
                }
                let checkbox: FeatureSelectionCheckbox;
                new TableData({parentElement: tr, children: [
                    checkbox = new FeatureSelectionCheckbox({
                        parentElement: undefined,
                        value: false, // FIXME? Maybe initialize straight with the upstream state?
                        upstreamValue: false, //FIXME?
                    })
                ]})
                scalesMap.set(scale, checkbox)
            })
        })

        new Paragraph({parentElement: this.element, children: [
            new Button({parentElement: undefined, inputType: "button", text: "All", onClick: () => {
                for(const scalesMap of this.checkboxes.values()){
                    for(const checkbox of scalesMap.values()){
                        checkbox.value = true;
                    }
                }
            }}),
            new Button({parentElement: undefined, inputType: "button", text: "None", onClick: () => {
                for(const scalesMap of this.checkboxes.values()){
                    for(const checkbox of scalesMap.values()){
                        checkbox.value = false;
                    }
                }
            }}),
            new Button({parentElement: undefined, inputType: "button", text: "Ok", onClick: () => {
                let extractors_to_add = new Array<IlpFeatureExtractor>();
                let extractors_to_remove = new Array<IlpFeatureExtractor>();

                for(const [featureName, scalesMap] of this.checkboxes.entries()){
                    for(const [scale, checkbox] of scalesMap.entries()){
                        if(!checkbox.isHighlighted()){
                            continue
                        }
                        const featureExtractor = new IlpFeatureExtractor({ilp_scale: scale, __class__: featureName, axis_2d: "z"}) //FIXME. always 'z'
                        checkbox.value ? extractors_to_add.push(featureExtractor) : extractors_to_remove.push(featureExtractor)
                    }
                }

                if(extractors_to_add.length > 0){
                    this.doRPC(
                        "add_feature_extractors",
                        new AddFeatureExtractorsParamsDto({
                            feature_extractors: extractors_to_add.map(e => e.toDto())
                        })
                    )
                }
                if(extractors_to_remove.length > 0){
                    this.doRPC(
                        "remove_feature_extractors",
                        new RemoveFeatureExtractorsParamsDto({
                            feature_extractors: extractors_to_remove.map(e => e.toDto())
                        })
                    )
                }
            }})
        ]})
    }

    protected onNewState(state: {feature_extractors: Array<IlpFeatureExtractor>}){
        let upstreamTable = new Map<FeatureClassName, Set<Scale>>();
        for(const fe of state.feature_extractors){
            const scales = upstreamTable.get(fe.__class__) || new Set<Scale>()
            scales.add(fe.ilp_scale)
            upstreamTable.set(fe.__class__, scales)
        }

        for(const [featureName, scalesMap] of this.checkboxes.entries()){
            const upstreamScales = upstreamTable.get(featureName) || new Set()
            for(const [scale, checkbox] of scalesMap.entries()){
                checkbox.upstreamValue = upstreamScales.has(scale)
            }
        }
    }
}
