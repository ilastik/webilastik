import { createElement, createInput } from '../../util/misc';
import * as itk from '../../client/ilastik'
import { CollapsableWidget } from './collapsable_applet_gui';
import { Applet } from '../../client/applets/applet';

// class FeatureCheckbox<FE extends itk.FeatureExtractor>{
//     constructor()
// }

export class FeatureSelectionWidget extends Applet<itk.FeatureExtractor[]>{
    public readonly element: HTMLElement;
    private selected_features: Array<itk.FeatureExtractor> = [];
    private feature_to_checkbox: Map<itk.FeatureExtractor, HTMLInputElement>

    public constructor({name, session, parentElement}: {
        name: string, session: itk.Session, parentElement: HTMLElement
    }){
        super({
            name,
            session,
            deserializer: itk.FeatureExtractor.fromJsonArray,
            onNewState: (new_state) => this.onNewState(new_state)
        })
        this.element = new CollapsableWidget({display_name: "Select Image Features", parentElement}).element
        this.element.classList.add("ItkFeatureSelectionWidget")
        this.feature_to_checkbox = new Map<itk.FeatureExtractor, HTMLInputElement>()
        const table = createElement({tagName: 'table', parentElement: this.element})
        const column_values = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]

        var tr = createElement({tagName: 'tr', parentElement: table})
        createElement({tagName: 'th', innerHTML: 'Feature / sigma', parentElement: tr})
        column_values.forEach(scale => createElement({tagName: 'th', innerHTML: scale.toFixed(1), parentElement: tr}))

        let createFeatureTr = <FE extends itk.FeatureExtractor>(
            extractor_name: string,
            extractor_from_scale: (scale: number) => FE,
        ) => {
            let tr = createElement({tagName: 'tr', parentElement: table});
            createElement({tagName: 'td', innerHTML: extractor_name, parentElement: tr});
            for(let scale of column_values){
                let td = createElement({tagName: 'td', parentElement: tr});
                let extractor = extractor_from_scale(scale)
                if(!(extractor instanceof itk.GaussianSmoothing) && scale == 0.3){
                    continue
                }
                let checkbox = createInput({inputType: 'checkbox', parentElement: td, onClick: (e) => {
                    let cb = <HTMLInputElement>e.target
                    if(cb.checked){
                        this.selected_features.push(extractor)
                    }else{
                        this.selected_features = this.selected_features.filter((fe) => {return !fe.equals(extractor)})
                    }
                }})
                this.feature_to_checkbox.set(extractor_from_scale(scale), checkbox)
            }
        }

        createFeatureTr("Gaussian Smoothing", (scale) => new itk.GaussianSmoothing({sigma: scale}))
        createFeatureTr("Laplacian Of Gaussian", (scale) => new itk.LaplacianOfGaussian({scale: scale}))
        createFeatureTr("Gaussian Gradient Magnitude", (scale) => new itk.GaussianGradientMagnitude({sigma: scale}));
        createFeatureTr("Difference Of Gaussians", (scale) => new itk.DifferenceOfGaussians({sigma0: scale, sigma1: scale * 0.66}))
        createFeatureTr("Structure Tensor Eigenvalues", (scale) => new itk.StructureTensorEigenvalues({innerScale: scale, outerScale: 0.5 * scale}));
        createFeatureTr("Hessian Of Gaussian Eigenvalues", (scale) => new itk.HessianOfGaussianEigenvalues({scale: scale}));

        createInput({inputType: "button", parentElement: this.element, value: "All", onClick: (e) => {
            let button = <HTMLInputElement>e.target;
            this.element.querySelectorAll("input[type=checkbox]").forEach((checkbox) => {
                let cb = <HTMLInputElement>checkbox
                if((button.value == "All" && !cb.checked) || (button.value == "None" && cb.checked)){
                    cb.click()
                }
            })
            button.value = button.value == "All" ? "None" : "All"
        }})

        createInput({inputType: 'button', parentElement: this.element, value: 'Ok', onClick: async () => {
            this.updateUpstreamState(this.selected_features)
        }})
    }

    protected onNewState(features: Array<itk.FeatureExtractor>){
        this.selected_features = []
        this.feature_to_checkbox.forEach((checkbox, feature) => {
            checkbox.checked = false
            for(let i=0; i<features.length; i++){
                if(feature.equals(features[i])){
                    checkbox.click()
                }
            }
        })
    }
}
