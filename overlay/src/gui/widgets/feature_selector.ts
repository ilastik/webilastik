import { FeatureClassName, IlpFeatureExtractor } from "../../client/ilastik"
import { CssClasses } from "../css_classes"
import { Button, CheckboxWidget } from "./input_widget"
import { Div, Paragraph, Table, TableData, TableHeader, TableRow } from "./widget"

type FeatureSelectionCheckbox = CheckboxWidget<IlpFeatureExtractor>

export class FeatureExtractorSet{
    private featureExtractors: Map<FeatureClassName, Map<number, IlpFeatureExtractor>>
    constructor(params?: {featureExtractors: Array<IlpFeatureExtractor>}){
        this.featureExtractors = new Map()

        params?.featureExtractors.forEach(fe => {
            this.add(fe);
        })
    }
    public contains(extractor: IlpFeatureExtractor): boolean{
        return this.featureExtractors.get(extractor.__class__)?.get(extractor.ilp_scale) !== undefined
    }
    public remove(extractor: IlpFeatureExtractor){
        this.featureExtractors.get(extractor.__class__)?.delete(extractor.ilp_scale)
    }
    public add(extractor: IlpFeatureExtractor){
        let scales = this.featureExtractors.get(extractor.__class__) || new Map<number, IlpFeatureExtractor>()
        scales.set(extractor.ilp_scale, extractor)
        this.featureExtractors.set(extractor.__class__, scales)
    }
    public get featureNames(): Array<string>{
        return Array.from(this.featureExtractors.keys())
    }
    public *getFeatureExtractors(): Generator<IlpFeatureExtractor, void, void>{
        for(let featureGroup of this.featureExtractors.values()){
            for(let featureExtractor of featureGroup.values()){
                yield featureExtractor
            }
        }
    }
    public getScales(): Array<number>{
        var scaleSet = new Set(Array.from(this.getFeatureExtractors()).map(fe => fe.ilp_scale))
        return Array.from(scaleSet).sort((a, b) => a - b)
    }
}

export const featureNames = [
    "Gaussian Smoothing",
    "Laplacian of Gaussian",
    "Gaussian Gradient Magnitude",
    "Difference of Gaussians",
    "Structure Tensor Eigenvalues",
    "Hessian of Gaussian Eigenvalues",
] as const;

export class FeatureSelector{
    public readonly element: Div
    private baseScales: Array<number>
    private checkboxes: Map<FeatureClassName, Map<number, FeatureSelectionCheckbox>>
    checkboxesContainer: Paragraph
    public readonly buttonsContainer: Paragraph

    public get value(): FeatureExtractorSet{
        let out = new FeatureExtractorSet()
        for(let group of this.checkboxes.values()){
            for(let checkbox of group.values()){
                const value = checkbox.value
                if(value){
                    out.add(value)
                }
            }
        }
        return out
    }

    public set value(val: FeatureExtractorSet){
        this.checkboxes = new Map()
        this.checkboxesContainer.clear()

        let scalesSet: Set<number> = new Set(this.baseScales)
        val.getScales().forEach(s => scalesSet.add(s))
        let scales = Array.from(scalesSet).sort((a, b) => a - b)

        new TableRow({parentElement: this.checkboxesContainer, children: [
            new TableHeader({innerText: 'Feature / sigma', parentElement: undefined}),
            ...scales.map(scale => new TableHeader({parentElement: undefined, innerText: scale.toFixed(1).toString()}))
        ]})

        featureNames.forEach(feature_name => {
            let tr = new TableRow({parentElement: this.checkboxesContainer, children: [
                new TableData({parentElement: undefined, innerText: feature_name})
            ]})
            const checkboxLine = new Map<number, FeatureSelectionCheckbox>()
            this.checkboxes.set(feature_name, checkboxLine)

            scales.forEach(scale => {
                const featureExtractor = new IlpFeatureExtractor({
                    ilp_scale: scale,
                    axis_2d: "z", //FIXME
                    __class__: feature_name,
                });
                let td = new TableData({parentElement: tr});
                let checked = val.contains(featureExtractor);
                if(scale == 0.3 && feature_name != "Gaussian Smoothing" && !checked){
                    return
                }
                checkboxLine.set(scale, new CheckboxWidget({
                    parentElement: td,
                    valueWhenChecked: featureExtractor,
                    checked,
                }))
            })
        })
    }

    constructor(params: {
        parentElement: HTMLElement,
        baseScales?: Array<number>,
        value?: FeatureExtractorSet,
    }){
        this.element = new Div({parentElement: params.parentElement})
        this.checkboxes = new Map()
        this.baseScales = params.baseScales || [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0];
        this.checkboxesContainer = new Table({parentElement: this.element, cssClasses: [CssClasses.ItkTable]})
        this.buttonsContainer = new Paragraph({parentElement: this.element, children: [
            new Button({parentElement: undefined, inputType: "button", text: "All", onClick: () => {
                for(const scalesMap of this.checkboxes.values()){
                    for(const checkbox of scalesMap.values()){
                        checkbox.checked = true;
                    }
                }
            }}),
            new Button({parentElement: undefined, inputType: "button", text: "None", onClick: () => {
                for(const scalesMap of this.checkboxes.values()){
                    for(const checkbox of scalesMap.values()){
                        checkbox.checked = false;
                    }
                }
            }})
        ]})
        this.value = params.value || new FeatureExtractorSet()
    }
}