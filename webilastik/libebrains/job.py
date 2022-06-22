#pyright: strict

import dataclasses
import enum
from typing import Literal, NewType, Optional, Tuple, cast
import typing
import re

from ndstructs.utils.json_serializable import (
    IJsonable,
    JsonObject,
    JsonValue,
    ensureJsonArray,
    ensureJsonInt,
    ensureJsonObject,
    ensureJsonString,
    ensureJsonStringArray,
)


Seconds = NewType("Seconds", int)

class Memory:
    def __init__(self, amount: int, unit: Literal["G"]) -> None:
        self.amount = amount
        self.unit = unit
        super().__init__()

    def to_json_value(self) -> str:
        return f"{self.amount}{self.unit}"

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "Memory":
        value_str = ensureJsonString(value)
        match = re.compile(r"(?<amount>\d+)(?<unit>[G]))", re.IGNORECASE).fullmatch(value_str)
        if not match:
            raise ValueError(f"Bad memory value: {value}")
        return Memory(amount=int(match.group("amount")), unit=cast(Literal["G"], match.group("unit")))


@dataclasses.dataclass
class JobResources(IJsonable):
    Memory: Memory
    Runtime: Seconds = Seconds(5 * 60)
    CPUs: Optional[int] = None
    Nodes: Optional[int] = None
    CPUsPerNode: Optional[int] = None
    Reservation: Optional[str] = None

    def to_json_value(self) -> JsonObject:
        json_obj: JsonObject = {
            "Memory": self.Memory.to_json_value(),
            "Runtime": self.Runtime,
            "CPUs": self.CPUs,
            "Nodes": self.Nodes,
            "CPUsPerNode": self.CPUsPerNode,
            "Reservation": self.Reservation,
        }
        return {k:v for k, v in json_obj.items() if v is not None}

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobResources":
        value_obj = ensureJsonObject(value)
        return JobResources(
            Memory=Memory.from_json_value(value_obj.get("Memory")),
            Runtime=Seconds(ensureJsonInt(value_obj.get("Runtime"))),
            CPUs=ensureJsonInt(value_obj.get("CPUs")),
            Nodes=ensureJsonInt(value_obj.get("Nodes")),
            CPUsPerNode=ensureJsonInt(value_obj.get("CPUsPerNode")),
            Reservation=ensureJsonString(value_obj.get("Reservation")),
        )

@dataclasses.dataclass
class JobImport(IJsonable):
    From: str #FIXME: PurePosixPath | Url ?
    To: str #FIXME: PurePosixPath | Url ?

    def to_json_value(self) -> JsonObject:
        return {
            "From": self.From,
            "To": self.To,
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobImport":
        value_obj = ensureJsonObject(value)
        return JobImport(
            From=ensureJsonString(value_obj.get("From")),
            To=ensureJsonString(value_obj.get("To")),
        )


@dataclasses.dataclass
class JobDescription(IJsonable):
    Name: str
    Project: str
    Executable: str
    Arguments: Tuple[str, ...]
    Resources: JobResources
    Environment: "None | typing.Mapping[str, str]" = None
    Exports: Tuple[str, ...] = ()
    Imports: Tuple[JobImport, ...] = ()
    Tags: Tuple[str, ...] = ()

    def to_json_value(self) -> JsonObject:
        return {
            k:v for k, v in {
                "Name": self.Name,
                "Project": self.Project,
                "Executable": self.Executable,
                "Arguments": self.Arguments,
                "Resources": self.Resources.to_json_value(),
                "Environment": self.Environment,
                "Exports": self.Exports,
                "Imports": tuple(imp.to_json_value() for imp in self.Imports),
                "Tags": self.Tags,
            }.items()
            if v is not None
        }

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobDescription":
        value_obj = ensureJsonObject(value)
        return JobDescription(
            Name=ensureJsonString(value_obj.get("Name")),
            Project=ensureJsonString(value_obj.get("Project")),
            Executable=ensureJsonString(value_obj.get("Executable")),
            Arguments=tuple(ensureJsonString(arg) for arg in ensureJsonArray(value_obj.get("Arguments"))),
            Resources=JobResources.from_json_value(value_obj.get("Resources")),
            Environment={k: ensureJsonString(v) for k, v in ensureJsonObject(value_obj.get("Environment")).items()},
            Exports=ensureJsonStringArray(value_obj.get("Exports")),
            Imports=tuple(JobImport.from_json_value(v) for v in ensureJsonArray(value_obj.get("Imports"))),
            Tags=ensureJsonStringArray(value_obj.get("Tags")),
        )

class SiteName(enum.Enum):
    DAINT_CSCS = "DAINT-CSCS"

    def to_json_value(self) -> str:
        return self.value

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "SiteName":
        value_str = ensureJsonString(value)
        for name in SiteName:
            if name.value == value_str:
                return name
        raise ValueError(f"Bad site name: {value_str}")


class JobStatus(enum.Enum):
    SUBMITTED = "SUBMITTED"

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobStatus":
        value_str = ensureJsonString(value)
        for status in JobStatus:
            if status.value == value_str:
                return status
        raise ValueError(f"Bad job status name: {value_str}")
