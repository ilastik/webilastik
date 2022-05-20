export class HashMap<K, V, HK extends string | number>{
    private registry = new Map<HK, [K, V]>();
    public readonly hash_function: (key: K) => HK;
    constructor({entries=[], hash_function}: {entries?: Array<[K, V]>, hash_function: (key: K) => HK}){
        this.hash_function = hash_function
        entries.forEach(entry => this.registry.set(hash_function(entry[0]), entry))
    }

    public set(key: K, value: V){
        return this.registry.set(this.hash_function(key), [key, value])
    }

    public get(key: K): V | undefined{
        let value =  this.registry.get(this.hash_function(key))
        if(value === undefined){
            return value
        }
        return value[1]
    }

    public has(key: K): boolean{
        return this.registry.has(this.hash_function(key))
    }

    public clear(){
        this.registry.clear()
    }

    public delete(key: K): boolean{
        return this.registry.delete(this.hash_function(key))
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
