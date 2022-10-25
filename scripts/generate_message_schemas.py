import inspect
import sys
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Sequence, Type, Tuple, Union, List
from pathlib import Path
from dataclasses import dataclass
import textwrap
from collections.abc import Mapping
import re
from ndstructs.point5D import itertools


from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString, toJsonValue

GENERATED_TS_FILE_PATH = Path(__file__).parent.parent / "overlay/src/client/message_schema.ts"
GENERATED_TS_FILE_PATH.unlink(missing_ok=True)
GENERATED_TS_FILE = open(GENERATED_TS_FILE_PATH, "w")
_ = GENERATED_TS_FILE.write("""
    import {
        ensureJsonNumber, ensureJsonString, ensureJsonUndefined, ensureJsonArray, ensureJsonObject, JsonValue, JsonObject, toJsonValue
    } from "../util/safe_serialization";
\n""")

GENERATED_PY_FILE_PATH = Path(__file__).parent.parent / "webilastik/server/message_schema.py"
GENERATED_PY_FILE_PATH.unlink(missing_ok=True)
GENERATED_PY_FILE = open(GENERATED_PY_FILE_PATH, "w")
_ = GENERATED_PY_FILE.write(textwrap.dedent(f"""
    # pyright: strict

    # Automatically generated via {Path(__file__).name}. Do not edit!

    from dataclasses import dataclass
    from typing import Tuple, Optional, Union, List
    import json

    from webilastik.serialization.json_serialization import (
        JsonObject, JsonValue, convert_to_json_value
    )

    class MessageGenerator:
        pass

    class MessageParsingError(Exception):
        pass
"""))


class PyFromJsonValueFunction:
    def __init__(self, *, py_hint: str, code: str) -> None:
        super().__init__()
        regex = re.compile("|".join([r"\[", r"\]", r"\.", ",", " "]))
        self.name = "parse_as_" + regex.sub('_', py_hint)
        self.full_code = (
            f"def {self.name}(value: JsonValue) -> '{py_hint} | MessageParsingError':" + "\n" +
            textwrap.indent(textwrap.dedent(code), prefix="    ") + "\n"
        )

    def __str__(self) -> str:
        return self.full_code

class Hint(ABC):
    hint_cache: ClassVar[Dict[Any, "Hint"]] = {}


    @classmethod
    def parse(cls, raw_hint: Any, context: str = "") -> "Hint":
        print(f"===>>> Parsing {raw_hint} ({context})")
        if raw_hint in cls.hint_cache:
            return cls.hint_cache[raw_hint]

        if MessageSchemaHint.is_message_schema_hint(raw_hint):
            hint =  MessageSchemaHint(raw_hint)
            _ = GENERATED_TS_FILE.write(hint.ts_class_code)
            _ = GENERATED_TS_FILE.write("\n")

            _ = GENERATED_PY_FILE.write(hint.py_class_code)
            _ = GENERATED_PY_FILE.write("\n")
        elif PrimitiveHint.is_primitive(raw_hint):
            hint =  PrimitiveHint(raw_hint)
        elif NTuple.is_n_tuple(raw_hint):
            hint =  NTuple(raw_hint)
        elif VarLenTuple.is_varlen_tuple(raw_hint):
            hint =  VarLenTuple(raw_hint)
        elif UnionHint.is_union_hint(raw_hint):
            hint =  UnionHint(raw_hint)
        else:
            raise TypeError(f"Unrecognized raw type hint: {raw_hint}")

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
    ) -> None:
        super().__init__()
        self.ts_hint = ts_hint
        self.py_hint = py_hint
        self.py_fromJsonValue_function = PyFromJsonValueFunction(py_hint=py_hint, code=py_fromJsonValue_code)


    @abstractmethod
    def make_py_to_json_expr(self, value_expr: str) -> str:
        pass

    @abstractmethod
    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        pass

    @abstractmethod
    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        pass


class MessageSchemaHint(Hint):
    message_generator_type: Type['MessageGenerator']
    field_annotations: Mapping[str, Hint]

    @staticmethod
    def is_message_schema_hint(hint: Any) -> bool:
        return hint.__class__ == type and issubclass(hint, MessageGenerator)

    def __init__(self, hint: Any) -> None:
        assert MessageSchemaHint.is_message_schema_hint(hint)
        self.message_generator_type = hint
        self.field_annotations = {
            field_name: Hint.parse(raw_hint)
            for klass in reversed(hint.__mro__)
            for field_name, raw_hint in getattr(klass, "__annotations__", {}).items()
        }
        super().__init__(
            ts_hint=self.message_generator_type.__name__,
            py_hint=self.message_generator_type.__name__,
            py_fromJsonValue_code="\n".join([
                "from collections.abc import Mapping",
                "if not isinstance(value, Mapping):",
                f"    return MessageParsingError(f'Could not parse {{json.dumps(value)}} as {self.message_generator_type.__name__}')",
                *list(itertools.chain(*(
                    [
                        f"tmp_{field_name} =  {hint.py_fromJsonValue_function.name}(value.get('{field_name}'))",
                        f"if isinstance(tmp_{field_name}, MessageParsingError):",
                        f"    return tmp_{field_name}",
                    ]
                    for field_name, hint in self.field_annotations.items()
                ))),
                f"return {self.message_generator_type.__name__}(",
                    *[f'{field_name}=tmp_{field_name},' for field_name in self.field_annotations.keys()],
                ")"
            ])
        )

        self.ts_class_code = "\n".join([
           f"// Automatically generated via {MessageGenerator.__qualname__} for {self.message_generator_type.__qualname__}",
            "// Do not edit!",
           f"export class {self.message_generator_type.__name__} {{",

         *[f"    public {field_name}: {hint.ts_hint};" for field_name, hint in self.field_annotations.items()],

            "    constructor(params: {",
         *[f'        {field_name}: {hint.ts_hint},' for field_name, hint in self.field_annotations.items()],
            "    }) {",
         *[f'        this.{field_name} = params.{field_name};' for field_name in self.field_annotations.keys()],
            "    }",

           f"    public static fromJsonValue(value: JsonValue): {self.ts_hint} | Error{{",
            "        const valueObject = ensureJsonObject(value);",
            "        if(valueObject instanceof Error){",
            "            return valueObject;",
            "        }",
            *list(itertools.chain(*(
                    [
                      f"const temp_{field_name} = {hint.to_ts_fromJsonValue_expr(f'valueObject.{field_name}')}",
                      f"if(temp_{field_name} instanceof Error){{ return temp_{field_name}; }}",
                    ]
                    for field_name, hint in self.field_annotations.items()
            ))),
            "        return new this({",
         *[f"            {field_name}: temp_{field_name}," for field_name in self.field_annotations.keys()],
            "        })",
           f"}}",

            "    public toJsonValue(): JsonObject{",
            "        return {",
         *[f"            {field_name}: " + hint.to_ts_toJsonValue_expr(f"this.{field_name}") + "," for field_name, hint in self.field_annotations.items()],
            "        }",
            "    }",
            f"}}"
        ])

        self.py_class_code: str = "\n".join([
           f"# Automatically generated via {MessageGenerator.__qualname__} for {self.message_generator_type.__qualname__}",
            "# Do not edit!",
            inspect.getsource(self.message_generator_type),
            "    def to_json_value(self) -> JsonObject:",
            "        return {",
         *[f"            '{field_name}': {hint.make_py_to_json_expr('self.' + field_name)}," for field_name, hint in self.field_annotations.items()],
            "        }",
            "",
            "    @classmethod",
           f"    def from_json_value(cls, value: JsonValue) -> '{self.py_hint} | MessageParsingError':",
           f"        return {self.py_fromJsonValue_function.name}(value)",
        ])

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"{value_expr}.to_json_value()"

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        return f"{self.message_generator_type.__name__}.fromJsonValue({json_value_expr})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"{value_expr}.toJsonValue()"

class PrimitiveHint(Hint):
    hint_type: "Type[int] | Type[float] | Type[bool] | Type[str] | None | Type[None]"
    def __init__(self, hint: Any) -> None:
        assert PrimitiveHint.is_primitive(hint)
        self.hint_type = hint
        py_hint='None' if self.hint_type in (None, type(None)) else self.hint_type.__name__
        super().__init__(
            ts_hint={int: "number", float: "number", str: "string", None: "undefined", type(None): "undefined"}[self.hint_type],
            py_hint=py_hint,
            py_fromJsonValue_code="\n".join([
                f"if isinstance(value, {'type(None)' if self.hint_type in (None, type(None)) else self.hint_type.__name__}):",
                    "    return value",
                f"return MessageParsingError(f'Could not parse {{json.dumps(value)}} as {py_hint}')",
            ])
        )

    @staticmethod
    def is_primitive(hint_type: Any) -> bool:
        return hint_type in (int, float, bool, str, None, type(None))

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return value_expr

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        if self.hint_type == int or self.hint_type == float:
            return f"ensureJsonNumber({json_value_expr})"
        if self.hint_type == str:
            return f"ensureJsonString({json_value_expr})"
        if self.hint_type == bool:
            return f"ensureJsonBoolean({json_value_expr})"
        if self.hint_type is None or self.hint_type == type(None):
            return f"ensureJsonUndefined({json_value_expr})"
        #FIXME
        raise Exception(f"Should be unreachable")

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
                f"    return MessageParsingError(f'Could not parse {py_hint} from {{json.dumps(value)}}')",
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
            ])
        )

    @staticmethod
    def is_n_tuple(hint: Any) -> bool:
        return TupleHint.is_tuple_hint(hint) and (... not in hint.__args__)

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        return "\n".join([
           f"((value: JsonValue): {self.ts_hint} | Error => {{",
            "    const arr = ensureJsonArray(value); if(arr instanceof Error){return arr}",
            *list(itertools.chain(*(
                [
                  f"const temp_{arg_index} = " + arg.to_ts_fromJsonValue_expr(f"arr[{arg_index}]") + ";",
                  f"if(temp_{arg_index} instanceof Error){{return temp_{arg_index}}}",
                ]
                for arg_index, arg in enumerate(self.generic_args)
            ))),
            "    return [" + ", ".join(f"temp_{arg_index}" for arg_index, _ in enumerate(self.generic_args)) + "];"
          f"}}) ({json_value_expr})",
        ])

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
        super().__init__(
            py_hint=f"Tuple[{self.element_type.py_hint}, ...]",
            ts_hint=f"Array<{self.element_type.ts_hint}>",
            py_fromJsonValue_code="\n".join([
                 "if not isinstance(value, (list, tuple)):",
                f"    return MessageParsingError(f'Could not parse {py_hint} from {{json.dumps(value)}}')",
                f"items: List[{self.element_type.py_hint}] = []",
                f"for item in value:",
                f"    parsed = {self.element_type.py_fromJsonValue_function.name}(item)",
                f"    if isinstance(parsed, MessageParsingError):",
                 "        return parsed",
                 "    items.append(parsed)",
                 "return tuple(items) ",
            ])
        )

    @staticmethod
    def is_varlen_tuple(hint: Any) -> bool:
        return TupleHint.is_tuple_hint(hint) and len(hint.__args__) == 2 and hint.__args__[-1] == ...

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"tuple({self.element_type.make_py_to_json_expr('item')} for item in {value_expr})"

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        return "\n".join([
            f"((value: JsonValue): {self.ts_hint} | Error => {{",
             "    const arr = ensureJsonArray(value);",
             "    if(arr instanceof Error){"
             "        return arr",
             "    }",
            f"    const out: {self.ts_hint} = []",
             "    for(let item of arr){",
            f"        let parsed_item = {self.element_type.to_ts_fromJsonValue_expr('item')};",
             "        if(parsed_item instanceof Error){"
             "            return parsed_item;"
             "        }",
             "        out.push(parsed_item);",
             "    }",
             "    return out;",
            f"}}) ({json_value_expr})"
        ])
        return f"ensureJsonArray({json_value_expr}).map(item => {self.element_type.to_ts_fromJsonValue_expr('item')})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"{value_expr}.map(item => {self.element_type.to_ts_toJsonValue_expr('item')})"

class UnionHint(Hint):
    union_args: Sequence[Hint]
    def __init__(self, raw_hint: Any) -> None:
        assert UnionHint.is_union_hint(raw_hint)
        self.union_args = [Hint.parse(arg) for arg in raw_hint.__args__]
        py_hint = f"Union[{', '.join(arg.py_hint for arg in self.union_args)}]"
        super().__init__(
            ts_hint=" | ".join(arg.ts_hint for arg in self.union_args),
            py_hint=py_hint,
            py_fromJsonValue_code="\n".join([
                *list(itertools.chain(*(
                    [
                        f"parsed_option_{arg_index} = {arg.py_fromJsonValue_function.name}(value)",
                        f"if not isinstance(parsed_option_{arg_index}, MessageParsingError):",
                        f"    return parsed_option_{arg_index}",
                    ]
                    for arg_index, arg in enumerate(self.union_args)
                ))),
                f"return MessageParsingError(f'Could not parse {{json.dumps(value)}} into {py_hint}')"
            ])
        )

    @classmethod
    def is_union_hint(cls, raw_hint: Any) -> bool:
        some_dummy_union = Union[int, str]
        return raw_hint.__class__ == some_dummy_union.__class__

    def make_py_to_json_expr(self, value_expr: str) -> str:
        return f"convert_to_json_value({value_expr})"

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        return "\n".join([
            f"((value: JsonValue): {self.ts_hint} | Error => {{",

            *list(itertools.chain(*(
                [
                    f"const parsed_option_{arg_index} = {arg.to_ts_fromJsonValue_expr('value')}",
                    f"if(!(parsed_option_{arg_index} instanceof Error)){{",
                    f"    return parsed_option_{arg_index};",
                    f"}}"
                ]
                for arg_index, arg in enumerate(self.union_args)
            ))),
            f"return Error(`Could not parse ${{JSON.stringify(value)}} into {self.ts_hint}`)"

            f"}})({json_value_expr})",
        ])

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"toJsonValue({value_expr})"

class MessageGenerator:
    def __init_subclass__(cls):
        super().__init_subclass__()
        _ = Hint.parse(cls)


@dataclass
class Color(MessageGenerator):
    r: int
    g: int
    b: int

@dataclass
class Url(MessageGenerator):
    datascheme: str
    protocol: str
    hostname: str
    port: Optional[str]
    path: str
    search: str
    fragment: str

@dataclass
class PixelAnnotation(MessageGenerator):
    raw_data: Url
    points: Tuple[Tuple[float, float, float], ...]

@dataclass
class RecolorLabelParams(MessageGenerator):
    label_name: str
    new_color: Color

@dataclass
class RenameLabelParams(MessageGenerator):
    old_name: str
    new_name: str

@dataclass
class CreateLabelParams(MessageGenerator):
    label_name: str
    color: Color

@dataclass
class RemoveLabelParams(MessageGenerator):
    label_name: str

@dataclass
class AddAnnotationParams(MessageGenerator):
    label_name: str
    voxels: Tuple[Tuple[float, float, float], ...]
