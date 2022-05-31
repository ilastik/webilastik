export class HashMap<K extends {hashValue: HK}, V, HK extends string | number>{
    private registry = new Map<HK, [K, V]>();
    constructor(){
    }

    public set(key: K, value: V){
        return this.registry.set(key.hashValue, [key, value])
    }

    public get(key: K): V | undefined{
        let value =  this.registry.get(key.hashValue)
        if(value === undefined){
            return value
        }
        return value[1]
    }

    public getOrCreate(key: K, default_value: V): V{
        if(!this.has(key)){
            this.set(key, default_value)
            return default_value
        }
        return this.get(key)!
    }

    public has(key: K): boolean{
        return this.registry.has(key.hashValue)
    }

    public clear(){
        this.registry.clear()
    }

    public delete(key: K): boolean{
        return this.registry.delete(key.hashValue)
    }

    public keys(): Array<K>{
        return Array.from(this.registry.values()).map(([key, _]) => key)
    }

    public values(): Array<V>{
        return Array.from(this.registry.values()).map(([_, value]) => value)
    }

    public entries(): Array<[K, V]>{
        return Array.from(this.registry.values())
    }
}
