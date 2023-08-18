import { getNowString } from "./misc"
import { Path } from "./parsed_url"

export type ReplacementParams = {
    inputPath: Path,
    itemIndex: number,
    resultType: "simple segmentation" | "pixel probabilities",
    extension: "n5" | "precomputed" | "dzi" | "dzip",
}

export abstract class ExportPatternComponent{
    public abstract getValue(params: ReplacementParams): string;
}

export class DatasetNameComponent extends ExportPatternComponent{
    public static readonly key = "name";
    public readonly key = "name";
    public getValue(params: ReplacementParams): string {
        return params.inputPath.stem
    }
}

export class ParentDirNameComponent extends ExportPatternComponent{
    public static readonly key = "parent_dir_name"
    public readonly key = "parent_dir_name"
    public getValue(params: ReplacementParams): string {
        return params.inputPath.parent.name
    }
}

export class ParentDirPathComponent extends ExportPatternComponent{
    public static readonly key = "parent_dir_path"
    public readonly key = "parent_dir_path"
    public getValue(params: ReplacementParams): string {
        return params.inputPath.parent.toString()
    }
}

export class ItemIndexComponent extends ExportPatternComponent{
    public static readonly key = "item_index"
    public readonly key = "item_index"
    public getValue(params: ReplacementParams): string {
        return params.itemIndex.toString()
    }
}

export class OutputTypeComponent extends ExportPatternComponent{
    public static readonly key = "output_type"
    public readonly key = "output_type"
    public getValue(params: ReplacementParams): string { return params.resultType.replace(" ", "-") }
}

export class TimestampComponent extends ExportPatternComponent{
    public static readonly key = "timestamp"
    public readonly key = "timestamp"
    public getValue(_params: ReplacementParams): string { return getNowString() }
}

export class ExtensionComponent extends ExportPatternComponent{
    public static readonly key = "extension"
    public readonly key = "extension"
    public getValue(params: ReplacementParams): string { return params.extension }
}

const componentKeys = [
    DatasetNameComponent.key,
    ParentDirNameComponent.key,
    ParentDirPathComponent.key,
    ItemIndexComponent.key,
    OutputTypeComponent.key,
    TimestampComponent.key,
    ExtensionComponent.key,
] as const;

type ComponentKey = (typeof componentKeys)[number]

const componentKeyMap = {
    [DatasetNameComponent.key]: DatasetNameComponent,
    [ParentDirNameComponent.key]: ParentDirNameComponent,
    [ParentDirPathComponent.key]: ParentDirPathComponent,
    [ItemIndexComponent.key]: ItemIndexComponent,
    [OutputTypeComponent.key]: OutputTypeComponent,
    [TimestampComponent.key]: TimestampComponent,
    [ExtensionComponent.key]: ExtensionComponent,
} as const;

type ComponentVariant = InstanceType<(typeof componentKeyMap)[ComponentKey]> | string


export class ExportPattern{
    constructor(public components: Array<ComponentVariant>){
    }

    public static parse(pattern: string): ExportPattern | Error{
        let components = new Array<ComponentVariant>();

        let componentStart = 0;
        literalLoop: for(let i=0; i<pattern.length; i++){
            const char = pattern[i]
            if(char == "}"){
                return new Error(`Unexpected '}' char ${i} in pattern ${pattern}`)
            }
            if(char != "{"){
                continue
            }
            components.push(pattern.slice(componentStart, i))
            componentStart = i = i + 1; //skip opening brace
            keyLoop: for(; i < pattern.length; i++){
                const char = pattern[i]
                if(char == "}"){
                    let slice = pattern.slice(componentStart, i)
                    const key = componentKeys.find(k => k === slice) //this is here for type-safety only
                    if(!key){
                        return new Error(
                            `Bad key '{${slice}}' in pattern ${pattern}. Valid keys are ${componentKeys.join(', ')}`
                        )
                    }
                    components.push(new componentKeyMap[key]())
                    componentStart = i + 1; //skip closing brace
                    continue literalLoop;
                }
                if(char == "{"){
                    return new Error(`Unexpected '{' at char ${i}`)
                }
            }
            return new Error(`Unexpected end of pattern before '}'`)
        }
        if(componentStart < pattern.length){
            components.push(pattern.slice(componentStart))
        }
        if(components.length == 0){
            return new Error(`Could not parse any component out of pattern ${pattern}`)
        }
        return new ExportPattern(components)
    }

    public expanded(params: ReplacementParams): Path{
        const expandedComponents = this.components.map(cmp => {
            return typeof cmp == "string" ? cmp : cmp.getValue(params)
        })
        return Path.parse(expandedComponents.join(""))
    }
    public toString(): string{
        return this.components.map(comp => {
            return typeof comp == "string" ? comp : `{${comp.key}}`
        }).join("")
    }
}