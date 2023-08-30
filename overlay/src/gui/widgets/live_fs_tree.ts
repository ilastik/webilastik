import { ListFsDirRequest } from "../../client/dto";
import { Filesystem, Session } from "../../client/ilastik";
import { createElement, createImage, removeElement } from "../../util/misc";
import { Path, Url } from "../../util/parsed_url";
import { FsFileWidget, FsFolderWidget } from "./fs_tree";
import { ContainerWidget, Div } from "./widget";

export class LiveFsTree{
    fs: Filesystem;
    element: Div;
    root: FsFolderWidget;
    session: Session;
    constructor(params: {fs: Filesystem, dirPath?: Path, session: Session, parentElement: ContainerWidget<any>}){
        this.fs = params.fs
        this.session = params.session
        this.element = new Div({parentElement: params.parentElement})

        const onOpen = async (folderWidget: FsFolderWidget) => {
            folderWidget.clear()
            let loadingGif = createImage({src: "/public/images/loading.gif", parentElement: folderWidget.element})
            const items_result = await this.session.listFsDir(new ListFsDirRequest({
                fs: this.fs.toDto(),
                path: folderWidget.path.raw
            }))
            removeElement(loadingGif)
            if(items_result instanceof Error){
                createElement({tagName: "p", parentElement: folderWidget.element, innerText: "Failed retrieving folder contents"})
                return
            }
            for(const dir of items_result.directories){
                let dir_path = Path.parse(dir)
                folderWidget.addChildFolder({name: dir_path.name, onOpen: onOpen})
            }
            for(const file of items_result.files){
                let file_path = Path.parse(file)
                folderWidget.addChildFile(file_path.name)
            }
        }

        let dirPath = params.dirPath || Path.root
        this.root = new FsFolderWidget({parent: this.element, path: dirPath, onOpen})
        this.root.open(true)
    }

    public getSelectedNodes(): Array<FsFileWidget | FsFolderWidget>{
        const selected_nodes = this.root.getDownstreamSelections()
        if(this.root.selected){
            selected_nodes.unshift(this.root)
        }
        return selected_nodes
    }
    public getSelectedPaths(): Array<Path>{
        return this.getSelectedNodes().map(node => node.path)
    }
    public getSelectedUrls(): Array<Url>{
        return this.getSelectedPaths().map(path => this.fs.getUrl(path))
    }
}