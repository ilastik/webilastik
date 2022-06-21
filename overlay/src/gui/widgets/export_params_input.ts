import { DataSource, FsDataSink, Session } from "../../client/ilastik";
import { DataSourceInput } from "./datasource_input";
import { PrecomputedChunksScale_DataSink_Input } from "./precomputed_chunks_scale_datasink_input";


export class PixelPredictionsExportParamsInput{
    private readonly datasinkInput: PrecomputedChunksScale_DataSink_Input;
    private numberOfPixelClasses: number | undefined;
    private readonly datasourceInput: DataSourceInput;

    constructor(params: {
        parentElement: HTMLElement,
        session: Session,
    }){
        this.datasourceInput = DataSourceInput.createLabeled({
            legend: "Input:",
            parentElement: params.parentElement,
            onChanged: () => this.updateDatasink(),
            session: params.session,
        })

        this.datasinkInput = PrecomputedChunksScale_DataSink_Input.createLabeled({
            legend: "Output:",
            parentElement: params.parentElement,
            encoding: "raw",
            dataType: "float32",
            disableShape: true,
            disableTileShape: true,
            disableDataType: true,
            disableEncoding: true,
        })
    }

    private updateDatasink(){
        let ds = this.datasourceInput.value
        if(ds && this.numberOfPixelClasses){
            this.datasinkInput.setParameters({
                shape: ds.shape.updated({c: this.numberOfPixelClasses}),
                tileShape: ds.tile_shape.updated({c: this.numberOfPixelClasses}),
                resolution: ds.spatial_resolution,
            })
        }
    }

    public setParams(params: {
        datasourceSuggestions?: DataSource[],
        datasource?: DataSource,
        numberOfPixelClasses?: number,
    }){
        if("datasourceSuggestions" in params){
            this.datasourceInput.setSuggestions(params.datasourceSuggestions)
        }
        if("datasource" in params){
            this.datasourceInput.value = params.datasource
        }
        if(params.numberOfPixelClasses){
            this.numberOfPixelClasses = params.numberOfPixelClasses
        }
        this.updateDatasink()
    }

    public get value(): {datasource: DataSource, datasink: FsDataSink} | undefined{
        let datasource = this.datasourceInput.value
        let datasink = this.datasinkInput.value
        if(!datasource || !datasink){
            return undefined
        }
        return {datasource, datasink}
    }
}


export class SimpleSegmentationExportParamsInput{
    private readonly templateDatasinkInput: PrecomputedChunksScale_DataSink_Input;
    private numberOfPixelClasses: number | undefined;
    private readonly datasourceInput: DataSourceInput;

    constructor(params: {
        parentElement: HTMLElement,
        session: Session,
    }){
        this.datasourceInput = DataSourceInput.createLabeled({
            legend: "Input:",
            parentElement: params.parentElement,
            onChanged: () => this.updateDatasink(),
            session: params.session,
        })

        this.templateDatasinkInput = PrecomputedChunksScale_DataSink_Input.createLabeled({
            legend: "Output:",
            parentElement: params.parentElement,
            encoding: "raw",
            dataType: "uint8",
            disableShape: true,
            disableTileShape: true,
            disableDataType: true,
            disableEncoding: true,
        })
    }

    private updateDatasink(){
        let ds = this.datasourceInput.value
        if(ds && this.numberOfPixelClasses){
            this.templateDatasinkInput.setParameters({
                shape: ds.shape.updated({c: 3}),
                tileShape: ds.tile_shape.updated({c: 3}),
                resolution: ds.spatial_resolution,
            })
        }
    }

    public setParams(params: {
        datasourceSuggestions?: DataSource[],
        datasource?: DataSource,
        numberOfPixelClasses?: number,
    }){
        if("datasourceSuggestions" in params){
            this.datasourceInput.setSuggestions(params.datasourceSuggestions)
        }
        if("datasource" in params){
            this.datasourceInput.value = params.datasource
        }
        if(params.numberOfPixelClasses){
            this.numberOfPixelClasses = params.numberOfPixelClasses
        }
        this.updateDatasink()
    }

    public get value(): {datasource: DataSource, datasinks: Array<FsDataSink>} | undefined{

        let datasource = this.datasourceInput.value
        let templateSink = this.templateDatasinkInput.value
        if(!datasource || !templateSink || !this.numberOfPixelClasses){
            return undefined
        }
        let datasinks = new Array<FsDataSink>()
        for(let i=0; i<this.numberOfPixelClasses; i++){
            datasinks.push(
                templateSink.updatedWith({info_dir: templateSink.info_dir.joinPath(`class_${i}`)})
            )
        }
        return {datasource, datasinks}
    }
}

