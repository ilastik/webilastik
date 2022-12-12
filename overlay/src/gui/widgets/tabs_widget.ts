import { createElement } from "../../util/misc";
import { CssClasses } from "../css_classes";


export class TabsWidget<WIDGET extends {element: HTMLElement}>{
    public readonly element: HTMLDivElement;
    private tabLabelWidgets: Map<string, HTMLLabelElement>;
    private tabBodyWidgets: Map<string, WIDGET>;
    private tabLabelWidgetsContainer: HTMLDivElement;
    private tabBodyWidgetsContainer: HTMLDivElement;

    constructor(params: {
        parentElement: HTMLElement,
        tabBodyWidgets: Map<string, WIDGET>,
    }){
        this.tabBodyWidgets = params.tabBodyWidgets
        this.tabLabelWidgets = new Map<string, HTMLLabelElement>()

        this.element = createElement({tagName: "div", parentElement: params.parentElement})
        this.tabLabelWidgetsContainer = createElement({
            tagName: "div", parentElement: this.element, cssClasses: [CssClasses.ItkTabLabelWidgetsContainer]
        })
        this.tabBodyWidgetsContainer = createElement({
            tagName: "div", parentElement: this.element, cssClasses: [CssClasses.ItkTabBodyContainer]
        })

        for(const [labelText, tabBodyWidget] of this.tabBodyWidgets.entries()){
            this.tabBodyWidgetsContainer.appendChild(tabBodyWidget.element)

            this.tabLabelWidgets.set(labelText, createElement({
                tagName: "label",
                parentElement: this.tabLabelWidgetsContainer,
                innerText: labelText,
                cssClasses: [CssClasses.ItkTabLabel],
                onClick: (_, labelWidget) => {
                    for(const widget of this.tabBodyWidgets.values()){
                        widget.element.style.display = "none"
                    }
                    for(const widget of this.tabLabelWidgets.values()){
                        widget.classList.remove(CssClasses.ItkActiveTabLabel)
                    }
                    labelWidget.style.display = ""
                    labelWidget.classList.add(CssClasses.ItkActiveTabLabel)
                    tabBodyWidget.element.style.display = ""
                }
            }))
        }
        createElement({tagName: "span", parentElement: this.tabLabelWidgetsContainer, cssClasses: [CssClasses.ItkTabLabelTrailer]})

        for(const t of this.tabLabelWidgets.values()){
            t.click();
            break;
        }
    }
}
