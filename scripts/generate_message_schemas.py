import inspect
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Sequence, Type, Tuple
from pathlib import Path
from dataclasses import dataclass
import textwrap


from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString, toJsonValue

GENERATED_TS_FILE_PATH = Path(__file__).parent.parent / "overlay/src/client/message_schema.ts"
GENERATED_TS_FILE_PATH.unlink(missing_ok=True)
with open(GENERATED_TS_FILE_PATH, "w") as f:
    _ = f.write("""
        import { ensureJsonNumber, ensureJsonString, ensureJsonArray, ensureJsonObject, JsonValue, JsonObject } from "../util/serialization";
    \n""")

GENERATED_PY_FILE_PATH = Path(__file__).parent.parent / "webilastik/server/message_schema.py"
GENERATED_PY_FILE_PATH.unlink(missing_ok=True)
with open(GENERATED_PY_FILE_PATH, "w") as f:
    _ = f.write(textwrap.dedent(f"""
        # pyright: strict

        # Automatically generated via {Path(__file__).name}. Do not edit!

        from dataclasses import dataclass
        from typing import Tuple

        from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString, ensureJsonFloat, ensureJsonArray

        class MessageGenerator:
            pass

    """))

class Hint(ABC):
    @staticmethod
    def parse(hint: Any) -> "Hint":
        if MessageSchemaHint.is_message_schema_hint(hint):
            return MessageSchemaHint(hint)
        if PrimitiveHint.is_primitive(hint):
            return PrimitiveHint(hint)
        if NTuple.is_limited_tuple(hint):
            return NTuple(hint)
        if VarLenTuple.is_unlimited_tuple(hint):
            return VarLenTuple(hint)
        raise TypeError(f"Unrecognized type hint: {hint}")

    @abstractmethod
    def to_py_from_json_value_expr(self, json_value_expr: str) -> str:
        pass

    @abstractmethod
    def to_py_to_json_value_expr(self, value_expr: str) -> str:
        pass

    @abstractmethod
    def to_ts_hint(self) -> str:
        pass

    @abstractmethod
    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        pass

    @abstractmethod
    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        pass


class MessageSchemaHint(Hint):
    message_generator_type: Type['MessageGenerator']

    @staticmethod
    def is_message_schema_hint(hint: Any) -> bool:
        return hint.__class__ == type and issubclass(hint, MessageGenerator)

    def __init__(self, hint: Any) -> None:
        super().__init__()
        assert MessageSchemaHint.is_message_schema_hint(hint)
        self.message_generator_type = hint

    def to_py_from_json_value_expr(self, json_value_expr: str) -> str:
        return f"{self.message_generator_type.__name__}.from_json_value({json_value_expr})"

    def to_py_to_json_value_expr(self, value_expr: str) -> str:
        return f"{value_expr}.to_json_value()"

    def to_ts_hint(self) -> str:
        return self.message_generator_type.__name__

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        return f"{self.message_generator_type.__name__}.fromJsonValue({json_value_expr})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"{value_expr}.toJsonValue()"

class PrimitiveHint(Hint):
    hint_type: "Type[int] | Type[float] | Type[bool] | Type[str] | None"
    def __init__(self, hint: Any) -> None:
        super().__init__()
        assert PrimitiveHint.is_primitive(hint)
        self.hint_type = hint

    @staticmethod
    def is_primitive(hint_type: Any) -> bool:
        return hint_type in (int, float, bool, str, None)

    def to_py_from_json_value_expr(self, json_value_expr: str) -> str:
        if self.hint_type == int:
            return f"ensureJsonInt({json_value_expr})"
        if self.hint_type == float:
            return f"ensureJsonFloat({json_value_expr})"
        if self.hint_type == str:
            return f"ensureJsonString({json_value_expr})"
        raise Exception(f"Unexpected (or unimplemented) type: {self.hint_type=}")

    def to_py_to_json_value_expr(self, value_expr: str) -> str:
        return value_expr

    def to_ts_hint(self) -> str:
        if self.hint_type == int or self.hint_type == float:
            return "number"
        if self.hint_type == str:
            return "string"
        if self.hint_type == bool:
            return "boolean"
        if self.hint_type == None:
            return "undefined"
        raise Exception(f"Should be unreachable")

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        if self.hint_type == int or self.hint_type == float:
            return f"ensureJsonNumber({json_value_expr})"
        if self.hint_type == str:
            return f"ensureJsonString({json_value_expr})"
        if self.hint_type == bool:
            return f"ensureJsonBoolean({json_value_expr})"
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

    def to_py_to_json_value_expr(self, value_expr: str) -> str:
        return value_expr

class NTuple(TupleHint):
    """Represents tuple a type-hint with all items defined, like Tuple[int, str]"""

    generic_args: Sequence[Hint]
    def __init__(self, hint: Any) -> None:
        assert NTuple.is_limited_tuple(hint)
        super().__init__()
        self.generic_args = [Hint.parse(a) for a  in hint.__args__]

    @staticmethod
    def is_limited_tuple(hint: Any) -> bool:
        return TupleHint.is_tuple_hint(hint) and (... not in hint.__args__)

    def to_py_from_json_value_expr(self, json_value_expr: str) -> str:
         #FIXME: ensureJsonArray is called on every element
        return (
            "(" +
                "".join(
                    hint.to_py_from_json_value_expr(f"ensureJsonArray({json_value_expr})[{hint_index}]") + ", "
                    for hint_index, hint in enumerate(self.generic_args)
                 ) +
            ")"
        )

    def to_ts_hint(self) -> str:
        return "[" + ",".join(arg.to_ts_hint() for arg in self.generic_args) + "]"

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        #FIXME: ensureJsonArray is called on every element
        return ("[" +
            ",\n".join(
                hint.to_ts_fromJsonValue_expr(f"ensureJsonArray({json_value_expr})[{hint_idx}]")
                for hint_idx, hint in enumerate(self.generic_args)
            ) +
        "]")

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
        assert VarLenTuple.is_unlimited_tuple(hint)
        super().__init__()
        self.element_type = Hint.parse(hint.__args__[0])

    @staticmethod
    def is_unlimited_tuple(hint: Any) -> bool:
        return TupleHint.is_tuple_hint(hint) and len(hint.__args__) == 2 and hint.__args__[-1] == ...

    def to_py_from_json_value_expr(self, json_value_expr: str) -> str:
        return (
            f"tuple({self.element_type.to_py_from_json_value_expr('item')} for item in ensureJsonArray({json_value_expr}) )"
        )

    def to_ts_hint(self) -> str:
        return f"Array<{self.element_type.to_ts_hint()}>"

    def to_ts_fromJsonValue_expr(self, json_value_expr: str) -> str:
        return f"ensureJsonArray({json_value_expr}).map(item => {self.element_type.to_ts_fromJsonValue_expr('item')})"

    def to_ts_toJsonValue_expr(self, value_expr: str) -> str:
        return f"{value_expr}.map(item => {self.element_type.to_ts_toJsonValue_expr('item')})"

class MessageGenerator:
    def __init_subclass__(cls):
        super().__init_subclass__()
        field_annotations: Dict[str, Hint] = {
            field_name: Hint.parse(raw_hint)
            for klass in reversed(cls.__mro__)
            for field_name, raw_hint in getattr(klass, "__annotations__", {}).items()
        }

        LF = "\n"

        with open(GENERATED_TS_FILE_PATH, "a") as f:
            print(f"Generating typescript class for {cls.__name__}...", file=sys.stderr)
            _ = f.write(f"""
                // automatically generated via {MessageGenerator.__qualname__}
                export class {cls.__name__} {{

                    {LF.join(f"public {field_name}: {hint.to_ts_hint()};" for field_name, hint in field_annotations.items())}

                    constructor(params: {{

                        {LF.join(f'{field_name}: {hint.to_ts_hint()},' for field_name, hint in field_annotations.items())}

                    }}) {{

                        {LF.join(f'this.{field_name} = params.{field_name};' for field_name in field_annotations.keys())}

                    }}

                    public static fromJsonValue(value: JsonValue): {cls.__name__} {{
                        const valueObject = ensureJsonObject(value);
                        return new {cls.__name__}({{

                            {LF.join(
                                f"{field_name}: {hint.to_ts_fromJsonValue_expr(f'valueObject.{field_name}')}," for field_name, hint in field_annotations.items()
                            )}

                        }})
                    }}

                    public toJsonValue(): JsonObject{{
                        return {{

                            {LF.join(f"{field_name}: {hint.to_ts_toJsonValue_expr('this.' + field_name)}," for field_name, hint in field_annotations.items())}

                        }}
                    }}
                }}
            """)

        with open(GENERATED_PY_FILE_PATH, "a") as f:
            _ = f.write(inspect.getsource(cls) + "\n\n")
            _ = f.write(textwrap.indent(
                textwrap.dedent(f"""
                    def to_json_value(self) -> JsonObject:
                        json_obj: JsonObject = {{
                            {','.join(
                                    f"'{field_name}': " + hint.to_py_to_json_value_expr(f'self.{field_name}')
                                    for field_name, hint in field_annotations.items()
                            )}
                        }}
                        return json_obj

                    @classmethod
                    def from_json_value(cls, value: JsonValue) -> '{cls.__name__}':
                        json_obj = ensureJsonObject(value)
                        return {cls.__name__}(
                            {','.join(
                                field_name + "=" + hint.to_py_from_json_value_expr(f"json_obj.get('{field_name}')")
                                for field_name, hint in field_annotations.items()
                            )}
                        )
                    \n""")
                ,prefix="    "
            ))


@dataclass
class Color(MessageGenerator):
    r: int
    g: int
    b: int

@dataclass
class PixelAnnotation(MessageGenerator):
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
