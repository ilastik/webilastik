#pyright: strict

import itertools
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Literal, Sequence, Type, Union, Mapping
from pathlib import Path
import textwrap
import ast
import sys

from webilastik.server.rpc import DataTransferObject

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


def make_serialization_function_name(*, prefix: str, py_hint: str) -> str:
    return "parse_as_" + py_hint.replace("[", "_of_").replace(
        "]", "_endof_"
    ).replace(
        " ", ""
    ).replace(
        ",", "0"
    ).replace(
        "...", "_varlen_"
    ).replace("'", "_quote_")

class PyFromJsonValueFunction:
    def __init__(self, *, py_hint: str, code: str) -> None:
        super().__init__()
        self.name = make_serialization_function_name(prefix="parse_as_", py_hint=py_hint)
        self.full_code = (
            f"def {self.name}(value: JsonValue) -> \"{py_hint} | MessageParsingError\":" + "\n" +
            textwrap.indent(textwrap.dedent(code), prefix="    ") + "\n"
        )

    def __str__(self) -> str:
        return self.full_code

class TsFromJsonValueFunction:
    def __init__(self, *, py_hint: str, ts_hint: str, code: str) -> None:
        super().__init__()
        self.name = make_serialization_function_name(prefix="parse_as_", py_hint=py_hint)
        self.full_code = (
            f"export function {self.name}(value: JsonValue): {ts_hint} | MessageParsingError{{" + "\n" +
                textwrap.indent(textwrap.dedent(code), prefix="    ") + "\n" +
            f"}}"
        )

    def __str__(self) -> str:
        return self.full_code

class Hint(ABC):
    hint_cache: ClassVar[Dict[Any, "Hint"]] = {}


    @classmethod
    def parse(cls, raw_hint: Any, context: str = "") -> "Hint":
        if raw_hint in cls.hint_cache:
            return cls.hint_cache[raw_hint]

        if DtoHint.is_dto_hint(raw_hint):
            hint =  DtoHint(raw_hint)
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

        _ = GENERATED_TS_FILE.write(hint.ts_fromJsonValue_function.full_code)
        _ = GENERATED_TS_FILE.write("\n")

        _ = GENERATED_PY_FILE.write(hint.py_fromJsonValue_function.full_code)
        _ = GENERATED_PY_FILE.write("\n")

        cls.hint_cache[raw_hint] = hint
        return hint

    def __init__(
        self,
        *,
        ts_hint: str,
        py_hint: str,
        py_fromJsonValue_code: str,
        ts_fromJsonValue_code: str,
    ) -> None:
        super().__init__()
        self.ts_hint = ts_hint
        self.py_hint = py_hint
        self.py_fromJsonValue_function = PyFromJsonValueFunction(py_hint=py_hint, code=py_fromJsonValue_code)
        self.ts_fromJsonValue_function = TsFromJsonValueFunction(py_hint=py_hint, ts_hint=ts_hint, code=ts_fromJsonValue_code)

    @abstractmethod
    def make_py_to_json_expr(self, value_expr: str) -> str:
        pass

    @abstractmethod
    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        pass

class MappingHint(Hint):
    key_hint: Hint
    value_hint: Hint

    def __init__(self, raw_hint: Any) -> None:
        assert MappingHint.is_mapping_hint(raw_hint)
        self.key_hint = Hint.parse(raw_hint=raw_hint.__args__[0])
        self.value_hint = Hint.parse(raw_hint=raw_hint.__args__[1])
        assert raw_hint.__args__[0] == str, "Mappings with keys other than strings are not supported yet"
        py_hint = f"Mapping[{self.key_hint.py_hint}, {self.value_hint.py_hint}]"
        ts_hint = f"{{ [key: {self.key_hint.ts_hint}]: {self.value_hint.ts_hint} }}"
        super().__init__(
            ts_hint=ts_hint,
            py_hint=py_hint,
            py_fromJsonValue_code="\n".join([
                "from collections.abc import Mapping as AbcMapping",
                "if not isinstance(value, AbcMapping):",
            f"    return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as a {py_hint}\")",
            f"out: Dict[{self.value_hint.py_hint}, {self.value_hint.py_hint}] = {{}}",
                "for key, val in value.items():",
            f"    parsed_key = {self.key_hint.py_fromJsonValue_function.name}(key)",
                "    if isinstance(parsed_key, MessageParsingError):",
                "        return parsed_key",
            f"    parsed_val = {self.value_hint.py_fromJsonValue_function.name}(val)",
                "    if isinstance(parsed_val, MessageParsingError):",
                "        return parsed_val",
                "    out[parsed_key] = parsed_val",
                "return out",
            ]),
            ts_fromJsonValue_code="\n".join([
                "const valueObj = ensureJsonObject(value);"
                "if(valueObj instanceof MessageParsingError){",
            f"    return valueObj",
                "}",
            f"const out: {ts_hint} = {{}}",
                "for(let key in valueObj){",
            f"    const parsed_key = {self.key_hint.ts_fromJsonValue_function.name}(key)",
                "    if(parsed_key instanceof MessageParsingError){",
                "        return parsed_key",
                "    }",
                "    const val = valueObj[key]",
            f"    const parsed_val = {self.value_hint.ts_fromJsonValue_function.name}(val)",
                "    if(parsed_val instanceof MessageParsingError){",
                "        return parsed_val",
                "    }",
                "    out[parsed_key] = parsed_val",
                "}",
                "return out",
            ]),
        )
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
            f"    const out: {{ [key: {self.key_hint.ts_hint}]: {self.value_hint.ts_hint} }} = {{}};"
            "    for(let key in value){"
            "        out[key] = value[key];"
            "    }"
            "    return out;"
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
        self.lit_value_hints = {value: Hint.parse(value.__class__) for value in raw_hint.__args__}
        ts_hint = " | ".join(literal_value_to_code(arg) for arg in raw_hint.__args__)
        py_hint = "Literal[" + ", ".join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in raw_hint.__args__) + "]"
        super().__init__(
            ts_hint=ts_hint,
            py_hint=py_hint,
            py_fromJsonValue_code="\n".join([
                *list(itertools.chain(*(
                    [
                        f"tmp_{val_idx} = {hint.py_fromJsonValue_function.name}(value)",
                        f"if not isinstance(tmp_{val_idx}, MessageParsingError) and tmp_{val_idx} == {literal_value_to_code(val)}:",
                        f"    return tmp_{val_idx}",
                    ]
                    for val_idx, (val, hint) in enumerate(self.lit_value_hints.items())
                ))),
                f"return MessageParsingError(f\"Could not parse {{value}} as {py_hint}\")"
            ]),
            ts_fromJsonValue_code="\n".join([
                *list(itertools.chain(*(
                    [
                        f"const tmp_{val_idx} = {hint.ts_fromJsonValue_function.name}(value)",
                        f"if(!(tmp_{val_idx} instanceof MessageParsingError) && tmp_{val_idx} === {literal_value_to_code(val)}){{",
                        f"    return tmp_{val_idx}",
                        f"}}",
                    ]
                    for val_idx, (val, hint) in enumerate(self.lit_value_hints.items())
                ))),
                f"return new MessageParsingError(`Could not parse ${{value}} as {ts_hint}`)"
            ]),
        )

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
        tag_key = self.message_generator_type.tag_key()
        tag_value = self.message_generator_type.tag_value()
        tag_value_ts = "undefined" if tag_value is None else tag_value
        class_name = self.message_generator_type.__name__
        super().__init__(
            ts_hint=self.message_generator_type.__name__,
            py_hint=self.message_generator_type.__name__,
            py_fromJsonValue_code="\n".join([
                "from collections.abc import Mapping",
                "if not isinstance(value, Mapping):",
                f"    return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as {class_name}\")",

                *([
                    f"if value.get('{tag_key}') != '{tag_value}':",
                    f"    return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as {class_name}\")",
                ] if tag_value is not None else []),
                *list(itertools.chain(*(
                    [
                        f"tmp_{field_name} =  {hint.py_fromJsonValue_function.name}(value.get('{field_name}'))",
                        f"if isinstance(tmp_{field_name}, MessageParsingError):",
                        f"    return tmp_{field_name}",
                    ]
                    for field_name, hint in self.field_annotations.items()
                ))),
                f"return {class_name}(",
                    *[f'{field_name}=tmp_{field_name},' for field_name in self.field_annotations.keys()],
                ")"
            ]),
            ts_fromJsonValue_code="\n".join([
                "const valueObject = ensureJsonObject(value);",
                "if(valueObject instanceof MessageParsingError){",
                "    return valueObject;",
                "}",
               *([
                    f"if (valueObject['{tag_key}'] != '{tag_value_ts}') {{",
                    f"    return new MessageParsingError(`Could not deserialize ${{JSON.stringify(valueObject)}} as a {class_name}`);",
                    f"}}"
               ] if tag_value is not None else []),
                *list(itertools.chain(*(
                    [
                    f"const temp_{field_name} = {hint.ts_fromJsonValue_function.name}(valueObject.{field_name})",
                    f"if(temp_{field_name} instanceof MessageParsingError){{ return temp_{field_name}; }}",
                    ]
                    for field_name, hint in self.field_annotations.items()
                ))),
            f"return new {class_name}({{",
            *[f"    {field_name}: temp_{field_name}," for field_name in self.field_annotations.keys()],
            f"}})",
            ])
        )

        # if "Url" in str(self.message_generator_type):
        #     import pydevd; pydevd.settrace()
        #     print("all right... lets see")

        self.ts_class_code = "\n".join([
        f"// Automatically generated via {DataTransferObject.__qualname__} for {self.message_generator_type.__qualname__}",
            "// Do not edit!",
        f"export class {class_name} {{",

        *[f"    public {field_name}: {hint.ts_hint};" for field_name, hint in self.field_annotations.items()],

            "    constructor(_params: {",
        *[f'        {field_name}: {hint.ts_hint},' for field_name, hint in self.field_annotations.items()],
            "    }) {",
        *[f'        this.{field_name} = _params.{field_name};' for field_name in self.field_annotations.keys()],
            "    }",

            "    public toJsonValue(): JsonObject{",
            "        return {",
           f"            '{tag_key}': '{tag_value}'," if tag_value is not None else "",
        *[f"            {field_name}: " + hint.to_ts_toJsonValue_expr(f"this.{field_name}") + "," for field_name, hint in self.field_annotations.items()],
            "        }",
            "    }",

        f"    public static fromJsonValue(value: JsonValue): {self.ts_hint} | MessageParsingError{{",
        f"        return {self.ts_fromJsonValue_function.name}(value)"
        f"    }}",

        f"}}"
        ])

        self.py_json_methods: str = "\n".join([
            "    def to_json_value(self) -> JsonObject:",
            "        return {",
           f"            '{tag_key}': '{tag_value}'," if tag_value is not None else "",
        *[f"            '{field_name}': {hint.make_py_to_json_expr('self.' + field_name)}," for field_name, hint in self.field_annotations.items()],
            "        }",
            "",
            "    @classmethod",
        f"    def from_json_value(cls, value: JsonValue) -> '{self.py_hint} | MessageParsingError':",
        f"        return {self.py_fromJsonValue_function.name}(value)",
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
        py_hint='None' if self.hint_type in (None, type(None)) else self.hint_type.__name__

        if self.hint_type == int or self.hint_type == float:
            ts_fromJsonValue_code = f"return ensureJsonNumber(value)"
        elif self.hint_type == str:
            ts_fromJsonValue_code = f"return ensureJsonString(value)"
        elif self.hint_type == bool:
            ts_fromJsonValue_code = f"return ensureJsonBoolean(value)"
        elif self.hint_type is None or self.hint_type == type(None):
            ts_fromJsonValue_code = f"return ensureJsonUndefined(value)"
        else:
            raise Exception(f"Should be unreachable")
        super().__init__(
            ts_hint={int: "number", float: "number", str: "string", bool: "boolean", None: "undefined", type(None): "undefined"}[self.hint_type],
            py_hint=py_hint,
            py_fromJsonValue_code="\n".join([
                f"if isinstance(value, {'type(None)' if self.hint_type in (None, type(None)) else self.hint_type.__name__}):",
                "    return value",
                "if isinstance(value, int): return float(value);" if self.hint_type == float else "",
                f"return MessageParsingError(f\"Could not parse {{json.dumps(value)}} as {py_hint}\")",
            ]),
            ts_fromJsonValue_code=ts_fromJsonValue_code,
        )

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
        py_hint = f"Tuple[{  ', '.join(arg.py_hint for arg in self.generic_args)  }]"
        super().__init__(
            ts_hint="[" + ",".join(arg.ts_hint for arg in self.generic_args) + "]",
            py_hint=py_hint,
            py_fromJsonValue_code="\n".join([
                f"if not isinstance(value, (list, tuple)) or len(value) < {len(self.generic_args)}:",
                f"    return MessageParsingError(f\"Could not parse {py_hint} from {{json.dumps(value)}}\")",
                *list(itertools.chain(*(
                    [
                        f"tmp_{arg_index} = {arg.py_fromJsonValue_function.name}(value[{arg_index}])",
                        f"if isinstance(tmp_{arg_index}, MessageParsingError):",
                        f"    return tmp_{arg_index}",
                    ]
                    for arg_index, arg in enumerate(self.generic_args)
                ))),
                "return (",
                    *[f"tmp_{temp_idx}," for temp_idx in range(len(self.generic_args))],
                ")",
            ]),
            ts_fromJsonValue_code="\n".join([
                "const arr = ensureJsonArray(value); if(arr instanceof MessageParsingError){return arr}",
                *list(itertools.chain(*(
                    [
                        f"const temp_{arg_index} = {arg.ts_fromJsonValue_function.name}(arr[{arg_index}]);",
                        f"if(temp_{arg_index} instanceof MessageParsingError){{return temp_{arg_index}}}",
                    ]
                    for arg_index, arg in enumerate(self.generic_args)
                ))),
                "return [" + ", ".join(f"temp_{arg_index}" for arg_index, _ in enumerate(self.generic_args)) + "];"
            ]),
        )

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
        py_hint=f"Tuple[{self.element_type.py_hint}, ...]"
        ts_hint=f"Array<{self.element_type.ts_hint}>"
        super().__init__(
            py_hint=py_hint,
            ts_hint=ts_hint,
            py_fromJsonValue_code="\n".join([
                "if not isinstance(value, (list, tuple)):",
                f"    return MessageParsingError(f\"Could not parse {py_hint} from {{json.dumps(value)}}\")",
                f"items: List[{self.element_type.py_hint}] = []",
                f"for item in value:",
                f"    parsed = {self.element_type.py_fromJsonValue_function.name}(item)",
                f"    if isinstance(parsed, MessageParsingError):",
                "        return parsed",
                "    items.append(parsed)",
                "return tuple(items) ",
            ]),
            ts_fromJsonValue_code="\n".join([
                "const arr = ensureJsonArray(value);",
                "if(arr instanceof MessageParsingError){"
                "    return arr",
                "}",
            f"const out: {ts_hint} = []",
                "for(let item of arr){",
            f"    let parsed_item = {self.element_type.ts_fromJsonValue_function.name}(item);",
                "    if(parsed_item instanceof MessageParsingError){"
                "        return parsed_item;"
                "    }",
                "    out.push(parsed_item);",
                "}",
                "return out;",
            ]),
        )

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
        py_hint = f"Union[{', '.join(arg.py_hint for arg in self.union_args)}]"
        ts_hint=" | ".join(arg.ts_hint for arg in self.union_args)
        super().__init__(
            py_hint=py_hint,
            ts_hint=ts_hint,
            py_fromJsonValue_code="\n".join([
                *list(itertools.chain(*(
                    [
                        f"parsed_option_{arg_index} = {arg.py_fromJsonValue_function.name}(value)",
                        f"if not isinstance(parsed_option_{arg_index}, MessageParsingError):",
                        f"    return parsed_option_{arg_index}",
                    ]
                    for arg_index, arg in enumerate(self.union_args)
                ))),
                f"return MessageParsingError(f\"Could not parse {{json.dumps(value)}} into {py_hint}\")"
            ]),
            ts_fromJsonValue_code="\n".join([
                *list(itertools.chain(*(
                    [
                        f"const parsed_option_{arg_index} = {arg.ts_fromJsonValue_function.name}(value)",
                        f"if(!(parsed_option_{arg_index} instanceof MessageParsingError)){{",
                        f"    return parsed_option_{arg_index};",
                        f"}}"
                    ]
                    for arg_index, arg in enumerate(self.union_args)
                ))),
                f"return new MessageParsingError(`Could not parse ${{JSON.stringify(value)}} into {ts_hint}`)"
            ])
        )

    @classmethod
    def is_union_hint(cls, raw_hint: Any) -> bool:
        some_dummy_union = Union[int, str]
        return raw_hint.__class__ == some_dummy_union.__class__

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"convert_to_json_value({value_expr})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"toJsonValue({value_expr})"


source = open(Path(__file__).parent / "dto.template.py").read()
exec(source)
root = ast.parse(source)

for item in root.body:
    if not isinstance(item, ast.ClassDef):
        _ = GENERATED_PY_FILE.write((ast.get_source_segment(source, item) or "") + "\n\n")
        continue

    klass: Type[Any] = sys.modules[__name__].__dict__[item.name]
    if not issubclass(klass, DataTransferObject):
        continue

    hint = Hint.parse(klass)
    assert isinstance(hint, DtoHint)
    for decorator in item.decorator_list:
        _ = GENERATED_PY_FILE.write(f"@" + (ast.get_source_segment(source, decorator) or "") + "\n")
    _ = GENERATED_PY_FILE.write(ast.get_source_segment(source, item) or "")
    _ = GENERATED_PY_FILE.write("\n\n")

    _ = GENERATED_PY_FILE.write(hint.py_json_methods)
    _ = GENERATED_PY_FILE.write("\n\n")

    _ = GENERATED_TS_FILE.write(hint.ts_class_code)
    _ = GENERATED_TS_FILE.write("\n\n")

