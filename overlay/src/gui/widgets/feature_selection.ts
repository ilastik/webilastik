import { createElement, createInput } from '../../util/misc';
import { CollapsableWidget } from './collapsable_applet_gui';
import { Applet } from '../../client/applets/applet';
import { Session, IlpFeatureExtractor, FeatureClassName } from '../../client/ilastik';
import { ensureJsonObject } from '../../util/serialization';

// class FeatureCheckbox<FE extends FeatureExtractor>{
//     constructor()
// }

type Scale = number;

class FeatureSelectionCheckbox{
    public readonly element: HTMLInputElement;
    public readonly featureExtractor: IlpFeatureExtractor;
    public lastUpstreamState: boolean
    constructor({parentElement, featureExtractor, lastUpstreamState, onClick}: {
        parentElement: HTMLElement,
        featureExtractor: IlpFeatureExtractor,
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

    public getStagedChanges(): {action: "add" | "remove" | "nothing", featureExtractor: IlpFeatureExtractor}{
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

export class FeatureSelectionWidget extends Applet<{feature_extractors: IlpFeatureExtractor[]}>{
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
                    feature_extractors: IlpFeatureExtractor.fromJsonArray(value_obj["feature_extractors"])
                }
            },
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Select Image Features", parentElement, help}).element
        this.element.classList.add("ItkFeatureSelectionWidget")

        const scales: Array<Scale> = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]
        const feature_extractor_creators = new Map<string, FeatureClassName>([
            ["Gaussian Smoothing", 'IlpGaussianSmoothing'],
            ["Laplacian Of Gaussian", "IlpLaplacianOfGaussian"],
            ["Gaussian Gradient Magnitude", "IlpGaussianGradientMagnitude"],
            ["Difference Of Gaussians", "IlpDifferenceOfGaussians"],
            ["Structure Tensor Eigenvalues", "IlpStructureTensorEigenvalues"],
            ["Hessian Of Gaussian Eigenvalues", "IlpHessianOfGaussianEigenvalues"]
        ])

        const table = createElement({tagName: 'table', parentElement: this.element})

        let header_row = createElement({tagName: 'tr', parentElement: table})
        createElement({tagName: 'th', innerHTML: 'Feature / sigma', parentElement: header_row})
        scales.forEach(scale => createElement({tagName: "th", parentElement: header_row, innerHTML: scale.toFixed(1)}))

        feature_extractor_creators.forEach((class_name, label) => {
            let tr = createElement({tagName: "tr", parentElement: table})
            createElement({tagName: "td", parentElement: tr, innerHTML: label})
            scales.forEach(scale => {
                this.checkboxes.push(new FeatureSelectionCheckbox({
                    parentElement: createElement({tagName: "td", parentElement: tr}),
                    featureExtractor: new IlpFeatureExtractor({ilp_scale: scale, axis_2d: "z", __class__: class_name}),
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
            let extractors_to_add = new Array<IlpFeatureExtractor>();
            let extractors_to_remove = new Array<IlpFeatureExtractor>();
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

    protected onNewState(state: {feature_extractors: Array<IlpFeatureExtractor>}){
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
