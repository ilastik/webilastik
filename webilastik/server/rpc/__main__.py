#pyright: strict

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, ForwardRef, List, Literal, Sequence, Type, Union, Mapping
from pathlib import Path
import textwrap
import ast
import sys

from webilastik.server.rpc import DataTransferObject


def from_json_val_func_name(*, py_hint: str) -> str:
    return "parse_as_" + py_hint.replace("[", "_of_").replace(
        "]", "_endof_"
    ).replace(
        " ", ""
    ).replace(
        ",", "0"
    ).replace(
        "...", "_varlen_"
    ).replace("'", "_quote_")


class Hint(ABC):
    hint_cache: ClassVar[Dict[Any, "Hint"]] = {}
    forward_hints_resolution: ClassVar[Dict[str, "Hint"]] = {}

    @classmethod
    def parse(cls, raw_hint: Any, context: str = "") -> "Hint":
        # if "StructureTensorEigenvaluesDto" in str(raw_hint):
        #     import pydevd; pydevd.settrace()
        #     print("lets goooo")

        if raw_hint in cls.hint_cache:
            return cls.hint_cache[raw_hint]

        if isinstance(raw_hint, str):
            return ForwardRefHint(raw_hint=raw_hint)
        if isinstance(raw_hint, ForwardRef):
            return Hint.parse(raw_hint.__forward_arg__, context=context + "  ")
        if DtoHint.is_dto_hint(raw_hint):
            hint =  DtoHint(raw_hint)
            Hint.forward_hints_resolution[hint.class_name] = hint
        elif PrimitiveHint.is_primitive(raw_hint):
            hint =  PrimitiveHint(raw_hint)
        elif NTuple.is_n_tuple(raw_hint):
            hint =  NTuple(raw_hint)
        elif VarLenTuple.is_varlen_tuple(raw_hint):
            hint =  VarLenTuple(raw_hint)
        elif UnionHint.is_union_hint(raw_hint):
            hint =  UnionHint(raw_hint)
        elif LiteralHint.is_literal(raw_hint=raw_hint):
            hint = LiteralHint(raw_hint=raw_hint)
        elif MappingHint.is_mapping_hint(raw_hint):
            hint = MappingHint(raw_hint)
        else:
            raise TypeError(f"Unrecognized raw type hint: {raw_hint}")

        cls.hint_cache[raw_hint] = hint
        return hint

    @property
    @abstractmethod
    def ts_hint(self) -> str:
        pass

    @property
    @abstractmethod
    def py_hint(self) -> str:
        pass

    @property
    @abstractmethod
    def py_fromJsonValue_function(self) -> str:
        pass

    @property
    @abstractmethod
    def ts_fromJsonValue_function(self) -> str:
        pass

    @abstractmethod
    def make_py_to_json_expr(self, value_expr: str) -> str:
        pass

    @abstractmethod
    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        pass

class ForwardRefHint(Hint):
    def __init__(self, *, raw_hint: "str | ForwardRef") -> None:
        self.hint_type_name = raw_hint if isinstance(raw_hint, str) else raw_hint.__forward_arg__
        super().__init__()

    @property
    def ts_hint(self) -> str:
        return Hint.forward_hints_resolution[self.hint_type_name].ts_hint

    @property
    def py_hint(self) -> str:
        return Hint.forward_hints_resolution[self.hint_type_name].py_hint

    @property
    def py_fromJsonValue_function(self) -> str:
        return Hint.forward_hints_resolution[self.hint_type_name].py_fromJsonValue_function

    @property
    def ts_fromJsonValue_function(self) -> str:
        return Hint.forward_hints_resolution[self.hint_type_name].ts_fromJsonValue_function

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return Hint.forward_hints_resolution[self.hint_type_name].make_py_to_json_expr(value_expr)

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return Hint.forward_hints_resolution[self.hint_type_name].to_ts_toJsonValue_expr(value_expr)

class MappingHint(Hint):
    key_hint: Hint
    value_hint: Hint

    def __init__(self, raw_hint: Any) -> None:
        assert MappingHint.is_mapping_hint(raw_hint)
        self.key_hint = Hint.parse(raw_hint=raw_hint.__args__[0])
        self.value_hint = Hint.parse(raw_hint=raw_hint.__args__[1])
        assert raw_hint.__args__[0] == str, "Mappings with keys other than strings are not supported yet"
        super().__init__()

    @property
    def ts_hint(self) -> str:
        return f"{{ [key: {self.key_hint.ts_hint}]: {self.value_hint.ts_hint} }}"

    @property
    def py_hint(self) -> str:
        return f"Mapping[{self.key_hint.py_hint}, {self.value_hint.py_hint}]"

    @property
    def py_fromJsonValue_function(self) -> str:
        return "\n".join([
           f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue) -> "{self.py_hint} | MessageParsingError":',
            "    from collections.abc import Mapping as AbcMapping",
            "    if not isinstance(value, AbcMapping):",
           f"       return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as a {self.py_hint}\")",
           f"    out: Dict[{self.value_hint.py_hint}, {self.value_hint.py_hint}] = {{}}",
            "    for key, val in value.items():",
           f"        parsed_key = {from_json_val_func_name(py_hint=self.key_hint.py_hint)}(key)",
            "        if isinstance(parsed_key, MessageParsingError):",
            "            return parsed_key",
           f"        parsed_val = {from_json_val_func_name(py_hint=self.value_hint.py_hint)}(val)",
            "        if isinstance(parsed_val, MessageParsingError):",
            "            return parsed_val",
            "        out[parsed_key] = parsed_val",
            "    return out",
        ])

    @property
    def ts_fromJsonValue_function(self) -> str:
        return "\n".join([
           f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
            "    const valueObj = ensureJsonObject(value);",
            "    if(valueObj instanceof MessageParsingError){",
           f"        return valueObj",
            "    }",
           f"    const out: {self.ts_hint} = {{}}",
            "    for(let key in valueObj){",
           f"        const parsed_key = {from_json_val_func_name(py_hint=self.key_hint.py_hint)}(key)",
            "        if(parsed_key instanceof MessageParsingError){",
            "            return parsed_key",
            "        }",
            "        const val = valueObj[key]",
           f"        const parsed_val = {from_json_val_func_name(py_hint=self.value_hint.py_hint)}(val)",
            "        if(parsed_val instanceof MessageParsingError){",
            "            return parsed_val",
            "        }",
            "        out[parsed_key] = parsed_val",
            "    }",
            "    return out",
           f"}}"
            ])

    @staticmethod
    def is_mapping_hint(raw_hint: Any) -> bool:
        some_dummy_mapping_hint = Mapping[str, int]
        return raw_hint.__class__ == some_dummy_mapping_hint.__class__

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return (
            "{" +
                self.key_hint.make_py_to_json_expr('key') + ":" + self.value_hint.make_py_to_json_expr('value') +
                f" for key, value in {value_expr}.items()" +
            "}"
        )

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return "\n".join([
            f"((value: {self.ts_hint}): JsonObject => {{",
            f"    const out: {{ [key: {self.key_hint.ts_hint}]: {self.value_hint.ts_hint} }} = {{}};",
            "    for(let key in value){",
            "        out[key] = value[key];",
            "    }",
            "    return out;",
            f"}})({value_expr})",
        ])

def literal_value_to_code(lit_value: 'int | bool | float | str | None') -> str:
    return f"'{lit_value}'" if isinstance(lit_value, str) else str(lit_value)

class LiteralHint(Hint):
    lit_value_hints: Mapping["int | str | float | bool | None", 'Hint']

    @staticmethod
    def is_literal(*, raw_hint: Any) -> bool:
        some_dummy_literal_hint = Literal["a"]
        if raw_hint.__class__ != some_dummy_literal_hint.__class__:
            return False
        assert all(isinstance(val, (int, float, str, type(None), bool)) for val in raw_hint.__args__)
        return True

    def __init__(self, raw_hint: Any) -> None:
        assert LiteralHint.is_literal(raw_hint=raw_hint)
        self.raw_hint_args: Sequence[Any] = raw_hint.__args__
        self.lit_value_hints = {value: Hint.parse(value.__class__) for value in raw_hint.__args__}
        super().__init__()


    @property
    def ts_hint(self) -> str:
        return " | ".join(literal_value_to_code(arg) for arg in self.raw_hint_args)

    @property
    def py_hint(self) -> str:
        return "Literal[" + ", ".join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in self.raw_hint_args) + "]"

    @property
    def py_fromJsonValue_function(self) -> str:
        out: List[str] = [
                f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue) -> "{self.py_hint} | MessageParsingError":',
        ]
        for val_idx, (val, hint) in enumerate(self.lit_value_hints.items()):
            out += [
                f"    tmp_{val_idx} = {from_json_val_func_name(py_hint=hint.py_hint)}(value)",
                f"    if not isinstance(tmp_{val_idx}, MessageParsingError) and tmp_{val_idx} == {literal_value_to_code(val)}:",
                f"        return tmp_{val_idx}",
            ]

        out += [
                f"    return MessageParsingError(f\"Could not parse {{value}} as {self.py_hint}\")",
        ]

        return "\n".join(out)

    @property
    def ts_fromJsonValue_function(self) -> str:
        out: List[str] = [
                f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
        ]
        for val_idx, (val, hint) in enumerate(self.lit_value_hints.items()):
            out += [
                f"    const tmp_{val_idx} = {from_json_val_func_name(py_hint=hint.py_hint)}(value)",
                f"    if(!(tmp_{val_idx} instanceof MessageParsingError) && tmp_{val_idx} === {literal_value_to_code(val)}){{",
                f"        return tmp_{val_idx}",
                f"    }}",
            ]

        out += [
                f"    return new MessageParsingError(`Could not parse ${{value}} as {self.ts_hint}`)",
                f"}}",
        ]
        return "\n".join(out)

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return value_expr

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return value_expr


class DtoHint(Hint):
    message_generator_type: Type['DataTransferObject']
    field_annotations: Mapping[str, Hint]

    @staticmethod
    def is_dto_hint(hint: Any) -> bool:
        return hint.__class__ == type and issubclass(hint, DataTransferObject)

    def __init__(self, hint: Any) -> None:
        assert DtoHint.is_dto_hint(hint)
        self.message_generator_type: Type['DataTransferObject'] = hint
        self.field_annotations = {
            field_name: Hint.parse(raw_hint)
            for klass in reversed(hint.__mro__)
            for field_name, raw_hint in getattr(klass, "__annotations__", {}).items()
        }
        self.tag_key = self.message_generator_type.tag_key()
        self.tag_value = self.message_generator_type.tag_value()
        self.tag_value_ts = "undefined" if self.tag_value is None else self.tag_value
        self.class_name = self.message_generator_type.__name__
        super().__init__()

    @property
    def ts_hint(self) -> str:
        return self.message_generator_type.__name__

    @property
    def py_hint(self) -> str:
        return self.message_generator_type.__name__

    @property
    def py_fromJsonValue_function(self) -> str:
        out: List[str] = [
                f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue) -> "{self.py_hint} | MessageParsingError":',
                 "    from collections.abc import Mapping",
                 "    if not isinstance(value, Mapping):",
                f"        return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as {self.class_name}\")",
        ]
        if self.tag_value is not None:
            out += [
                f"    if value.get('{self.tag_key}') != '{self.tag_value}':",
                f"        return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as {self.class_name}\")",
            ]
        for field_name, hint in self.field_annotations.items():
            out += [
                f"    tmp_{field_name} = {from_json_val_func_name(py_hint=hint.py_hint)}(value.get('{field_name}'))",
                f"    if isinstance(tmp_{field_name}, MessageParsingError):",
                f"        return tmp_{field_name}",
            ]
        out += [
                f"    return {self.class_name}(",
              *[f'        {field_name}=tmp_{field_name},' for field_name in self.field_annotations.keys()],
                "    )",
                ""
        ]
        return "\n".join(out)

    @property
    def ts_fromJsonValue_function(self) -> str:
        out: List[str] = [
               f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
                "    const valueObject = ensureJsonObject(value);",
                "    if(valueObject instanceof MessageParsingError){",
                "        return valueObject;",
                "    }",
        ]
        if self.tag_value is not None:
            out += [
               f"    if (valueObject['{self.tag_key}'] != '{self.tag_value_ts}') {{",
               f"        return new MessageParsingError(`Could not deserialize ${{JSON.stringify(valueObject)}} as a {self.class_name}`);",
               f"    }}"
            ]
        for field_name, hint in self.field_annotations.items():
            out += [
               f"    const temp_{field_name} = {from_json_val_func_name(py_hint=hint.py_hint)}(valueObject.{field_name})",
               f"    if(temp_{field_name} instanceof MessageParsingError){{",
               f"        return temp_{field_name};",
               f"    }}",
            ]
        out += [
               f"    return new {self.class_name}({{",
             *[f"        {field_name}: temp_{field_name}," for field_name in self.field_annotations.keys()],
               f"    }})",
               f"}}",
               f"",
        ]
        return "\n".join(out)

    @property
    def ts_class_code(self) -> str:
        return"\n".join([
            f"// Automatically generated via {DataTransferObject.__qualname__} for {self.message_generator_type.__qualname__}",
            "// Do not edit!",
            f"export class {self.class_name} {{",

            *[f"    public {field_name}: {hint.ts_hint};" for field_name, hint in self.field_annotations.items()],

                "    constructor(_params: {",
            *[f'        {field_name}: {hint.ts_hint},' for field_name, hint in self.field_annotations.items()],
                "    }) {",
            *[f'        this.{field_name} = _params.{field_name};' for field_name in self.field_annotations.keys()],
                "    }",

                "    public toJsonValue(): JsonObject{",
                "        return {",
            f"            '{self.tag_key}': '{self.tag_value}'," if self.tag_value is not None else "",
            *[f"            {field_name}: " + hint.to_ts_toJsonValue_expr(f"this.{field_name}") + "," for field_name, hint in self.field_annotations.items()],
                "        }",
                "    }",

            f"    public static fromJsonValue(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
            f"        return {from_json_val_func_name(py_hint=self.py_hint)}(value)",
            f"    }}",
            f"}}"
        ])

    @property
    def py_json_methods(self) -> str:
        return "\n".join([
            "    def to_json_value(self) -> JsonObject:",
            "        return {",
           f"            '{self.tag_key}': '{self.tag_value}'," if self.tag_value is not None else "",
         *[f"            '{field_name}': {hint.make_py_to_json_expr('self.' + field_name)}," for field_name, hint in self.field_annotations.items()],
            "        }",
            "",
            "    @classmethod",
           f'    def from_json_value(cls, value: JsonValue) -> "{self.py_hint} | MessageParsingError":',
           f"        return {from_json_val_func_name(py_hint=self.py_hint)}(value)",
           f"",
        ])

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"{value_expr}.to_json_value()"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"{value_expr}.toJsonValue()"

class PrimitiveHint(Hint):
    hint_type: "Type[int] | Type[float] | Type[bool] | Type[str] | None | Type[None]"
    def __init__(self, hint: Any) -> None:
        assert PrimitiveHint.is_primitive(hint)
        self.hint_type = hint
        super().__init__()

    @property
    def ts_hint(self) -> str:
        return {int: "number", float: "number", str: "string", bool: "boolean", None: "undefined", type(None): "undefined"}[self.hint_type]

    @property
    def py_hint(self) -> str:
        return 'None' if self.hint_type in (None, type(None)) else self.hint_type.__name__

    @property
    def py_fromJsonValue_function(self) -> str:
        return "\n".join([
           f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue)  -> "{self.py_hint} | MessageParsingError":',
           f"    if isinstance(value, {'type(None)' if self.hint_type in (None, type(None)) else self.hint_type.__name__}):",
            "        return value",
            "    if isinstance(value, int):" if self.hint_type == float else "",
            "        return float(value);" if self.hint_type == float else "",
           f"    return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as {self.py_hint}\")",
            "",
        ])

    @property
    def ts_fromJsonValue_function(self) -> str:
        out: List[str] = [
                    f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
        ]
        if self.hint_type == int or self.hint_type == float:
            out += [f"    return ensureJsonNumber(value)"]
        elif self.hint_type == str:
            out += [f"    return ensureJsonString(value)"]
        elif self.hint_type == bool:
            out += [f"    return ensureJsonBoolean(value)"]
        elif self.hint_type is None or self.hint_type == type(None):
            out += [f"    return ensureJsonUndefined(value)"]
        else:
            raise Exception(f"Should be unreachable")
        out += [    f"}}"]
        return "\n".join(out)

    @staticmethod
    def is_primitive(hint_type: Any) -> bool:
        return hint_type in (int, float, bool, str, None, type(None))

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return value_expr

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return value_expr

class TupleHint(Hint):
    @staticmethod
    def is_tuple_hint(hint: Any) -> bool:
        if hint.__class__ == type and hint.__name__ == "tuple":
            return True
        if hint.__class__.__name__ == "_GenericAlias" and hint.__origin__ == tuple:
            return True
        return False

class NTuple(TupleHint):
    """Represents tuple a type-hint with all items defined, like Tuple[int, str]"""

    generic_args: Sequence[Hint]
    def __init__(self, hint: Any) -> None:
        assert NTuple.is_n_tuple(hint)
        self.generic_args = [Hint.parse(a) for a  in hint.__args__]
        super().__init__()

    @property
    def ts_hint(self) -> str:
        return "[" + ",".join(arg.ts_hint for arg in self.generic_args) + "]"

    @property
    def py_hint(self) -> str:
        return f"Tuple[{  ', '.join(arg.py_hint for arg in self.generic_args)  }]"

    @property
    def py_fromJsonValue_function(self) -> str:
        out: List[str] = [
               f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue)  -> "{self.py_hint} | MessageParsingError":',
               f"    if not isinstance(value, (list, tuple)) or len(value) < {len(self.generic_args)}:",
               f"        return MessageParsingError(f\"Could not parse {self.py_hint} from {{json.dumps(value)}}\")",
        ]
        for arg_index, arg in enumerate(self.generic_args):
            out += [
               f"    tmp_{arg_index} = {from_json_val_func_name(py_hint=arg.py_hint)}(value[{arg_index}])",
               f"    if isinstance(tmp_{arg_index}, MessageParsingError):",
               f"        return tmp_{arg_index}",
            ]
        out += [
                "    return (",
             *[f"        tmp_{temp_idx}," for temp_idx in range(len(self.generic_args))],
                "    )",
                "",
        ]
        return "\n".join(out)

    @property
    def ts_fromJsonValue_function(self) -> str:
        out: List[str] = [
               f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
                "    const arr = ensureJsonArray(value); if(arr instanceof MessageParsingError){return arr}",
        ]
        for arg_index, arg in enumerate(self.generic_args):
            out += [
                f"    const temp_{arg_index} = {from_json_val_func_name(py_hint=arg.py_hint)}(arr[{arg_index}]);",
                f"    if(temp_{arg_index} instanceof MessageParsingError){{",
                f"        return temp_{arg_index}",
                f"    }}",
            ]
        out += [ "    return ["]
        out += [f"        temp_{arg_index}," for arg_index, _ in enumerate(self.generic_args)]
        out += [ "    ]"]
        out += [f"}}"]

        return "\n".join(out)

    @staticmethod
    def is_n_tuple(hint: Any) -> bool:
        return TupleHint.is_tuple_hint(hint) and (... not in hint.__args__)

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return "(" + ",".join(
            arg.make_py_to_json_expr(f"{value_expr}[{arg_index}]")
            for arg_index, arg in enumerate(self.generic_args)
        ) + ",)"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return ("[" +
            ",\n".join(
                hint.to_ts_toJsonValue_expr(f"{value_expr}[{hint_idx}]")
                for hint_idx, hint in enumerate(self.generic_args)
            ) +
        "]")

class VarLenTuple(TupleHint):
    """Represents a type-hint like Tuple[T, ...]"""

    element_type: Hint

    def __init__(self, hint: Any) -> None:
        assert VarLenTuple.is_varlen_tuple(hint)
        self.element_type = Hint.parse(hint.__args__[0])

        super().__init__()

    @property
    def py_hint(self) -> str:
        return f"Tuple[{self.element_type.py_hint}, ...]"

    @property
    def ts_hint(self) -> str:
        return f"Array<{self.element_type.ts_hint}>"

    @property
    def py_fromJsonValue_function(self) -> str:
        return "\n".join([
           f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue)  -> "{self.py_hint} | MessageParsingError":',
            "    if not isinstance(value, (list, tuple)):",
           f"        return MessageParsingError(f\"Could not parse {self.py_hint} from {{json.dumps(value)}}\")",
           f"    items: List[{self.element_type.py_hint}] = []",
           f"    for item in value:",
           f"        parsed = {from_json_val_func_name(py_hint=self.element_type.py_hint)}(item)",
           f"        if isinstance(parsed, MessageParsingError):",
            "            return parsed",
            "        items.append(parsed)",
            "    return tuple(items) ",
            "",
        ])

    @property
    def ts_fromJsonValue_function(self) -> str:
        return "\n".join([
           f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
            "    const arr = ensureJsonArray(value);",
            "    if(arr instanceof MessageParsingError){",
            "        return arr",
            "    }",
           f"    const out: {self.ts_hint} = []",
            "    for(let item of arr){",
           f"        let parsed_item = {from_json_val_func_name(py_hint=self.element_type.py_hint)}(item);",
            "        if(parsed_item instanceof MessageParsingError){",
            "            return parsed_item;",
            "        }",
            "        out.push(parsed_item);",
            "    }",
            "    return out;",
           f"}}",
        ])

    @staticmethod
    def is_varlen_tuple(hint: Any) -> bool:
        return TupleHint.is_tuple_hint(hint) and len(hint.__args__) == 2 and hint.__args__[-1] == ...

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"tuple({self.element_type.make_py_to_json_expr('item')} for item in {value_expr})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"{value_expr}.map(item => {self.element_type.to_ts_toJsonValue_expr('item')})"

class UnionHint(Hint):
    union_args: Sequence[Hint]
    def __init__(self, raw_hint: Any) -> None:
        assert UnionHint.is_union_hint(raw_hint)
        self.union_args = [Hint.parse(arg) for arg in raw_hint.__args__]
        super().__init__()

    @property
    def py_hint(self) -> str:
        return f"Union[{', '.join(arg.py_hint for arg in self.union_args)}]"

    @property
    def ts_hint(self) -> str:
        return " | ".join(arg.ts_hint for arg in self.union_args)

    @property
    def py_fromJsonValue_function(self) -> str:
        out: List[str] = [
                f'def {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue) -> "{self.py_hint} | MessageParsingError":',
        ]
        for arg_index, arg in enumerate(self.union_args):
            out += [
                f"    parsed_option_{arg_index} = {from_json_val_func_name(py_hint=arg.py_hint)}(value)",
                f"    if not isinstance(parsed_option_{arg_index}, MessageParsingError):",
                f"        return parsed_option_{arg_index}",
            ]
        out += [
                f"    return MessageParsingError(f\"Could not parse {{json.dumps(value)}} into {self.py_hint}\")",
                 "",
        ]
        return "\n".join(out)

    @property
    def ts_fromJsonValue_function(self) -> str:
        out: List[str] = [
                f"export function {from_json_val_func_name(py_hint=self.py_hint)}(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
        ]
        for arg_index, arg in enumerate(self.union_args):
            out += [
                f"    const parsed_option_{arg_index} = {from_json_val_func_name(py_hint=arg.py_hint)}(value)",
                f"    if(!(parsed_option_{arg_index} instanceof MessageParsingError)){{",
                f"        return parsed_option_{arg_index};",
                f"    }}",
            ]
        out += [
                f"    return new MessageParsingError(`Could not parse ${{JSON.stringify(value)}} into {self.ts_hint}`)",
                f"}}",
        ]
        return "\n".join(out)

    @classmethod
    def is_union_hint(cls, raw_hint: Any) -> bool:
        some_dummy_union = Union[int, str]
        return raw_hint.__class__ == some_dummy_union.__class__

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"convert_to_json_value({value_expr})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"toJsonValue({value_expr})"


PROJECT_DIR = Path(__file__).parent.parent.parent.parent

GENERATED_TS_FILE_PATH = PROJECT_DIR / "overlay/src/client/dto.ts"
GENERATED_TS_FILE_PATH.unlink(missing_ok=True)
GENERATED_TS_FILE = open(GENERATED_TS_FILE_PATH, "w")
_ = GENERATED_TS_FILE.write("""
    import {JsonObject, toJsonValue, JsonValue, isJsonableObject, JsonArray, isJsonableArray} from "../util/serialization"

    export class MessageParsingError extends Error{
        public readonly __class_name__ = "MessageParsingError"
    }

    export function ensureJsonUndefined(value: JsonValue): undefined | MessageParsingError{
        if(value !== undefined && value !== null){ //FIXME? null AND undefined?
            return new MessageParsingError(`Expected undefined/null, found ${JSON.stringify(value)}`)
        }
        return undefined
    }

    export function ensureJsonBoolean(value: JsonValue): boolean | MessageParsingError{
        if(typeof(value) !== "boolean"){
            return new MessageParsingError(`Expected boolean, found ${JSON.stringify(value)}`)
        }
        return value
    }

    export function ensureJsonNumber(value: JsonValue): number | MessageParsingError{
        if(typeof(value) !== "number"){
            return new MessageParsingError(`Expected number, found ${JSON.stringify(value)}`)
        }
        return value
    }

    export function ensureJsonString(value: JsonValue): string | MessageParsingError{
        if(typeof(value) !== "string"){
            return new MessageParsingError(`Expected string, found ${JSON.stringify(value)}`)
        }
        return value
    }

    export function ensureJsonObject(value: JsonValue): JsonObject | MessageParsingError{
        if(!isJsonableObject(value)){
            return new MessageParsingError(`Expected JSON object, found this: ${JSON.stringify(value)}`)
        }
        return value
    }

    export function ensureJsonArray(value: JsonValue): JsonArray | MessageParsingError{
        if(!isJsonableArray(value)){
            return new MessageParsingError(`Expected JSON array, found this: ${JSON.stringify(value)}`)
        }
        return value
    }
\n""")

GENERATED_PY_FILE_PATH = Path(__file__).parent / "dto.py"
GENERATED_PY_FILE_PATH.unlink(missing_ok=True)
GENERATED_PY_FILE = open(GENERATED_PY_FILE_PATH, "w")
_ = GENERATED_PY_FILE.write(textwrap.dedent(f"""
    # pyright: strict

    # Automatically generated via {__file__}.
    # Edit the template file instead of this one!

    import json
    from typing import List, Dict

    from ndstructs.point5D import Point5D, Shape5D, Interval5D

    from webilastik.serialization.json_serialization import (
        JsonObject, JsonValue, convert_to_json_value
    )
    from webilastik.server.rpc import DataTransferObject, MessageParsingError

"""))

source = open(Path(__file__).parent / "dto.template.py").read()
exec(source)
root = ast.parse(source)

ast_to_hint: Dict[ast.ClassDef, DtoHint] = {}
for item in root.body:
    if not isinstance(item, ast.ClassDef):
        continue
    klass: Type[Any] = sys.modules[__name__].__dict__[item.name]
    if not issubclass(klass, DataTransferObject):
        continue
    dto_hint = Hint.parse(klass)
    assert isinstance(dto_hint, DtoHint)
    ast_to_hint[item] = dto_hint

for item in root.body:
    if not isinstance(item, ast.ClassDef):
        _ = GENERATED_PY_FILE.write((ast.get_source_segment(source, item) or "") + "\n\n")
        continue
    hint = ast_to_hint[item]

    for decorator in item.decorator_list:
        _ = GENERATED_PY_FILE.write(f"@" + (ast.get_source_segment(source, decorator) or "") + "\n")
    _ = GENERATED_PY_FILE.write(ast.get_source_segment(source, item) or "")

    _ = GENERATED_PY_FILE.write("\n")
    _ = GENERATED_PY_FILE.write(hint.py_json_methods)

for hint in Hint.hint_cache.values():
    # if isinstance(hint, DtoHint) and hint.class_name == "StructureTensorEigenvaluesDto":
    #     import pydevd; pydevd.settrace()
    #     print("gogogo")
    _ = GENERATED_PY_FILE.write("\n")
    _ = GENERATED_PY_FILE.write(hint.py_fromJsonValue_function)
    _ = GENERATED_PY_FILE.write("\n")

    _ = GENERATED_TS_FILE.write("\n")
    _ = GENERATED_TS_FILE.write(hint.ts_fromJsonValue_function)
    _ = GENERATED_TS_FILE.write("\n")

    if isinstance(hint, DtoHint):
        _ = GENERATED_TS_FILE.write(hint.ts_class_code)
        _ = GENERATED_TS_FILE.write("\n")

GENERATED_PY_FILE.close()
GENERATED_TS_FILE.close()