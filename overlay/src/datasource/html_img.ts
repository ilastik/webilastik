import { vec3 } from "gl-matrix";
import { SkimageDataSource } from "../client/ilastik";
import { Url } from "../util/parsed_url";
import { IDataScale, IMultiscaleDataSource } from "./datasource";

export class HtmlImgSource implements IMultiscaleDataSource{
    constructor(public readonly url: Url){
        if(!HtmlImgSource.accepts(url)){
            throw Error(`Url ${url.double_protocol_raw} is not valid for a HTML img`)
        }
    }

    public static accepts(url: Url): boolean{
        return url.datascheme === undefined && (url.protocol == "http" || url.protocol =="https")
    }

    public get scales(): Array<IDataScale>{
        const ilastik_datasource = new SkimageDataSource({
            filesystem: this.url.updatedWith({path: "/"}),
            path: this.url.path,
        })
        return [
            {
                resolution: ilastik_datasource.spatial_resolution,
                toDisplayString: () => ilastik_datasource.getDisplayString(),
                toStrippedMultiscaleDataSource: async () => {return this},
                toIlastikDataSource: () => ilastik_datasource,
            }
        ]
    }

    public findScale(resolution: vec3): IDataScale | undefined{
        if(vec3.equals(vec3.fromValues(1,1,1), resolution)){
            return this.scales[0]
        }
        return undefined
    }
}
