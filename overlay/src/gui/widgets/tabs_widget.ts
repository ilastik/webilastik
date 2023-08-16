import { CssClasses } from "../css_classes";
import { Div, Label, Widget } from "./widget";


export class TabsWidget<LABEL extends string, WIDGET extends Widget<any>>{
    public readonly element: Div;
    private tabLabelWidgets: Map<LABEL, Label>;
    private tabBodyWidgets: Map<LABEL, WIDGET>;
    private tabLabelWidgetsContainer: Div;
    private tabBodyWidgetsContainer: Div;
    private _current: {label: LABEL, widget: WIDGET};

    constructor(params: {
        parentElement: HTMLElement | undefined,
        tabBodyWidgets: Map<LABEL, WIDGET>,
        onSwitch?: (label: LABEL, activeWidget: WIDGET, allWidgets: Array<WIDGET>) => void,
    }){
        this.tabBodyWidgets = params.tabBodyWidgets
        this.tabLabelWidgets = new Map<LABEL, Label>()

        const entries = Array.from(params.tabBodyWidgets.entries());
        this._current = {label: entries[0][0], widget: entries[0][1]}

        this.element = new Div({parentElement: params.parentElement, cssClasses: [CssClasses.ItkTabsWidget], children: [
            this.tabLabelWidgetsContainer = new Div({parentElement: undefined, cssClasses: [CssClasses.ItkTabLabelWidgetsContainer]}),
            this.tabBodyWidgetsContainer = new Div({parentElement: undefined, cssClasses: [CssClasses.ItkTabBodyContainer]}),
        ]})

        for(const [labelText, tabBodyWidget] of this.tabBodyWidgets.entries()){
            this.tabBodyWidgetsContainer.element.appendChild(tabBodyWidget.element)

            let labelWidget = new Label({
                parentElement: this.tabLabelWidgetsContainer,
                innerText: labelText,
                cssClasses: [CssClasses.ItkTabLabel],
                onClick: () => {
                    for(const widget of this.tabBodyWidgets.values()){
                        widget.show(false)
                    }
                    for(const widget of this.tabLabelWidgets.values()){
                        widget.removeCssClass(CssClasses.ItkActiveTabLabel)
                    }
                    labelWidget.show(true)
                    labelWidget.addCssClass(CssClasses.ItkActiveTabLabel)
                    tabBodyWidget.show(true)
                    this._current = {label: labelText, widget: tabBodyWidget}

                    if(params.onSwitch){
                        params.onSwitch(labelText, tabBodyWidget, Array.from(this.tabBodyWidgets.values()))
                    }
                }
            })
            this.tabLabelWidgets.set(labelText, labelWidget)
            new Label({parentElement: this.tabLabelWidgetsContainer, innerText: "", cssClasses: [CssClasses.ItkTabLabelSpacer]})
        }

        for(const t of this.tabLabelWidgets.values()){
            t.click();
            break;
        }
    }

    public get current(): {label: LABEL, widget: WIDGET}{
        return this._current
    }

    public getTabBodyWidgets(): Array<WIDGET>{
        return Array.from(this.tabBodyWidgets.values())
    }
}
