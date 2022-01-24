import { createElement, createInput } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { Applet } from '../../client/applets/applet';
import { DifferenceOfGaussians, FeatureExtractor, GaussianGradientMagnitude, GaussianSmoothing, HessianOfGaussianEigenvalues, LaplacianOfGaussian, Session, StructureTensorEigenvalues } from '../../client/ilastik';
import { ensureJsonObject } from '../../util/serialization';

// class FeatureCheckbox<FE extends FeatureExtractor>{
//     constructor()
// }

type Scale = number;

class FeatureSelectionCheckbox{
    public readonly element: HTMLInputElement;
    public readonly featureExtractor: FeatureExtractor;
    public lastUpstreamState: boolean
    constructor({parentElement, featureExtractor, lastUpstreamState, onClick}: {
        parentElement: HTMLElement,
        featureExtractor: FeatureExtractor,
        lastUpstreamState: boolean,
        onClick?: (feature_checkbox: FeatureSelectionCheckbox) => void,
    }){
        this.featureExtractor = featureExtractor
        this.lastUpstreamState = lastUpstreamState
        this.element = createInput({inputType: "checkbox", parentElement, onClick: () => {
            this.updateHighlight()
            if(onClick){
                onClick(this)
            }
        }})
        this.element.checked = lastUpstreamState
    }

    public setLastUpstreamState(checked: boolean){
        this.lastUpstreamState = checked
        this.updateHighlight()
    }

    public setChecked(checked: boolean){
        this.element.checked = checked
        this.updateHighlight()
    }

    public getStagedChanges(): {action: "add" | "remove" | "nothing", featureExtractor: FeatureExtractor}{
        let action: "add" | "remove" | "nothing" = "nothing"
        if(this.element.checked != this.lastUpstreamState){
            action = this.element.checked ? 'add' : 'remove'
        }
        return {
            action,
            featureExtractor: this.featureExtractor
        }
    }

    private updateHighlight(){
        let uncommited_changes = this.element.checked != this.lastUpstreamState
        this.element.style.boxShadow = uncommited_changes ? "0px 0px 0px 4px orange" : ""
    }
}

export class FeatureSelectionWidget extends Applet<{feature_extractors: FeatureExtractor[]}>{
    public readonly element: HTMLElement;
    private checkboxes = new Array<FeatureSelectionCheckbox>();

    public constructor({name, session, parentElement, help}: {
        name: string, session: Session, parentElement: HTMLElement, help: string[]
    }){
        super({
            name,
            session,
            deserializer: (data) => {
                let value_obj = ensureJsonObject(data)
                return {
                    feature_extractors: FeatureExtractor.fromJsonArray(value_obj["feature_extractors"])
                }
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Select Image Features", parentElement, help}).element
        this.element.classList.add("ItkFeatureSelectionWidget")

        const scales: Array<Scale> = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]
        const feature_extractor_creators = new Map<string, (scale: Scale) => FeatureExtractor>([
            ["Gaussian Smoothing", (scale) => new GaussianSmoothing({sigma: scale})],
            ["Laplacian Of Gaussian", (scale) => new LaplacianOfGaussian({scale: scale})],
            ["Gaussian Gradient Magnitude", (scale) => new GaussianGradientMagnitude({sigma: scale})],
            ["Difference Of Gaussians", (scale) => new DifferenceOfGaussians({sigma0: scale, sigma1: scale * 0.66})],
            ["Structure Tensor Eigenvalues", (scale) => new StructureTensorEigenvalues({innerScale: scale, outerScale: 0.5 * scale})],
            ["Hessian Of Gaussian Eigenvalues", (scale) => new HessianOfGaussianEigenvalues({scale: scale})]
        ])

        const table = createElement({tagName: 'table', parentElement: this.element})

        let header_row = createElement({tagName: 'tr', parentElement: table})
        createElement({tagName: 'th', innerHTML: 'Feature / sigma', parentElement: header_row})
        scales.forEach(scale => createElement({tagName: "th", parentElement: header_row, innerHTML: scale.toFixed(1)}))

        feature_extractor_creators.forEach((creator, label) => {
            let tr = createElement({tagName: "tr", parentElement: table})
            createElement({tagName: "td", parentElement: tr, innerHTML: label})
            scales.forEach(scale => {
                this.checkboxes.push(new FeatureSelectionCheckbox({
                    parentElement: createElement({tagName: "td", parentElement: tr}),
                    featureExtractor: creator(scale),
                    lastUpstreamState: false, // FIXME? Maybe initialize straight with the upstream state?
                }))
            })
        })

        createInput({inputType: "button", parentElement: this.element, value: "All", onClick: () => {
            this.checkboxes.filter(cb => !cb.element.checked).forEach(cb => cb.element.click())
        }})
        createInput({inputType: "button", parentElement: this.element, value: "None", onClick: () => {
            this.checkboxes.filter(cb => cb.element.checked).forEach(cb => cb.element.click())
        }})
        createInput({inputType: 'button', parentElement: this.element, value: 'Ok', onClick: async () => {
            let extractors_to_add = new Array<FeatureExtractor>();
            let extractors_to_remove = new Array<FeatureExtractor>();
            for(let cb of this.checkboxes){
                let changes = cb.getStagedChanges()
                if(changes.action == "add"){
                    extractors_to_add.push(changes.featureExtractor)
                }else if(changes.action == "remove"){
                    extractors_to_remove.push(changes.featureExtractor)
                }
            }
            if(extractors_to_add.length > 0){
                this.doRPC("add_feature_extractors", {feature_extractors: extractors_to_add})
            }
            if(extractors_to_remove.length > 0){
                this.doRPC("remove_feature_extractors", {feature_extractors: extractors_to_remove})
            }
        }})
    }

    protected onNewState(state: {feature_extractors: Array<FeatureExtractor>}){
        for(let cb of this.checkboxes){
            cb.setLastUpstreamState(false)
            cb.setChecked(false)
            for(let fe of state.feature_extractors){
                if(cb.featureExtractor.equals(fe)){
                    cb.setLastUpstreamState(true)
                    cb.setChecked(true)
                    break
                }
            }
        }
    }
}
