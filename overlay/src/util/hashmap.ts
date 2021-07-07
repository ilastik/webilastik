export class HashMap<K, V>{
    private registry = new Map<string, [K, V]>();
    public readonly hash_function: (key: K) => string;
    constructor({entries=[], hash_function}: {entries?: Array<[K, V]>, hash_function: (key: K) => string}){
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
}
