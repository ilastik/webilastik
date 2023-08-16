import { CollapsableWidget } from './collapsable_applet_gui';
import { Applet } from '../../client/applets/applet';
import { Session, IlpFeatureExtractor } from '../../client/ilastik';
import { FeatureSelectionAppletStateDto, SetFeatureExtractorsParamsDto } from '../../client/dto';
import { Button, ButtonWidget } from './input_widget';
import { FeatureExtractorSet, FeatureSelector } from './feature_selector';
import { PopupWidget } from './popup';
import { Paragraph } from './widget';

export class FeatureSelectionApplet extends Applet<{feature_extractors: IlpFeatureExtractor[]}>{
    public readonly element: HTMLElement;
    private state: FeatureExtractorSet = new FeatureExtractorSet()

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

        new Paragraph({parentElement: this.element, children: [
            new Button({parentElement: this.element, inputType: "button", text: "Select features", onClick: async () => {
                const popup = new PopupWidget("Select Image Features", true);
                const featureSelector = new FeatureSelector({parentElement: popup.element, value: this.state})
                new ButtonWidget({contents: "Ok", parentElement: featureSelector.buttonsContainer, onClick: () => {
                    this.state = featureSelector.value //mask latency
                    this.doRPC(
                        "set_feature_extractors",
                        new SetFeatureExtractorsParamsDto({
                            feature_extractors: Array.from(featureSelector.value.getFeatureExtractors()).map(e => e.toDto())
                        })
                    )
                    popup.destroy()
                }}),
                new ButtonWidget({parentElement: featureSelector.buttonsContainer, contents: "Cancel", onClick: () => popup.destroy()})
            }})
        ]})
    }

    protected onNewState(state: {feature_extractors: Array<IlpFeatureExtractor>}){
        this.state = new FeatureExtractorSet({featureExtractors: state.feature_extractors})
    }
}
