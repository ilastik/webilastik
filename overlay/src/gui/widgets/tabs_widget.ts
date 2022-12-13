import { createElement } from "../../util/misc";
import { CssClasses } from "../css_classes";


export class TabsWidget<WIDGET extends {readonly element: HTMLElement}>{
    public readonly element: HTMLDivElement;
    private tabLabelWidgets: Map<string, HTMLLabelElement>;
    private tabBodyWidgets: Map<string, WIDGET>;
    private tabLabelWidgetsContainer: HTMLDivElement;
    private tabBodyWidgetsContainer: HTMLDivElement;
    private _current: {label: string, widget: WIDGET};

    constructor(params: {
        parentElement: HTMLElement,
        tabBodyWidgets: Map<string, WIDGET>,
        onSwitch?: (label: string, activeWidget: WIDGET, allWidgets: Array<WIDGET>) => void,
    }){
        this.tabBodyWidgets = params.tabBodyWidgets
        this.tabLabelWidgets = new Map<string, HTMLLabelElement>()

        const entries = Array.from(params.tabBodyWidgets.entries());
        this._current = {label: entries[0][0], widget: entries[0][1]}

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
                    this._current = {label: labelText, widget: tabBodyWidget}

                    if(params.onSwitch){
                        params.onSwitch(labelText, tabBodyWidget, Array.from(this.tabBodyWidgets.values()))
                    }
                }
            }))
        }
        createElement({tagName: "span", parentElement: this.tabLabelWidgetsContainer, cssClasses: [CssClasses.ItkTabLabelTrailer]})

        for(const t of this.tabLabelWidgets.values()){
            t.click();
            break;
        }
    }

    public get current(): {label: string, widget: WIDGET}{
        return this._current
    }

    public getTabBodyWidgets(): Array<WIDGET>{
        return Array.from(this.tabBodyWidgets.values())
    }
}
