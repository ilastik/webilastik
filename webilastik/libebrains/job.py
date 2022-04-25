#pyright: strict

import dataclasses
import enum
from typing import Literal, NewType, Optional, Tuple
import typing
import uuid
import datetime
import requests

import aiohttp

from ndstructs.utils.json_serializable import (
    IJsonable,
    JsonObject,
    JsonValue,
    ensureJsonInt,
    ensureJsonObject,
    ensureJsonString,
    ensureOptional,
    toJsonValue,
)
from webilastik.libebrains.user_token import UserToken
from webilastik.utility.url import Url


Seconds = NewType("Seconds", int)

class Memory:
    def __init__(self, amount: int, unit: Literal["G"]) -> None:
        self.amount = amount
        self.unit = unit

    def to_json_value(self) -> str:
        return f"{self.amount}{self.unit}"

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

@dataclasses.dataclass
class JobImport(IJsonable):
    From: str #FIXME: PurePosixPath | Url ?
    To: str #FIXME: PurePosixPath | Url ?

    def to_json_value(self) -> JsonObject:
        return {
            "From": self.From,
            "To": self.To,
        }


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
                # "Exports": self.Exports,
                # "Imports": tuple(imp.to_json_value() for imp in self.Imports),
                # "Tags": self.Tags,
            }.items()
            if v is not None
        }

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


@dataclasses.dataclass
class JobSubmission:
    id: uuid.UUID
    job_id: uuid.UUID
    site: SiteName
    num_cpus: Optional[int]
    num_nodes: Optional[int]
    runtime: Optional[int]
    total_runtime: Optional[int]
    status: JobStatus
    #pre_command_status: None
    #post_command_status: None
    error: Optional[str]
    created: datetime.datetime
    updated: datetime.datetime
    # job_def: JobDescription

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "JobSubmission":
        value_obj = ensureJsonObject(value)
        return JobSubmission(
            id=uuid.UUID(ensureJsonString(value_obj.get("id"))),
            job_id=uuid.UUID(ensureJsonString(value_obj.get("job_id"))),
            site=SiteName.from_json_value(value_obj.get("site")),
            num_cpus=ensureOptional(ensureJsonInt, value_obj.get("num_cpus")),
            num_nodes=ensureOptional(ensureJsonInt, value_obj.get("num_nodes")),
            runtime=ensureOptional(ensureJsonInt, value_obj.get("runtime")),
            total_runtime=ensureOptional(ensureJsonInt, value_obj.get("total_runtime")),
            status=JobStatus.from_json_value(value_obj.get("status")),
            error=ensureOptional(ensureJsonString, value_obj.get("error")),
            created=datetime.datetime.strptime(
                ensureJsonString(value_obj.get("created")),
                '%Y-%m-%dT%H:%M:%S.%f'
            ),
            updated=datetime.datetime.strptime(
                ensureJsonString(value_obj.get("updated")),
                '%Y-%m-%dT%H:%M:%S.%f'
            ),
        )


class JobProxyClient:
    API_URL: Url = Url.parse_or_raise("https://unicore-job-proxy.apps.hbp.eu/api")

    def __init__(self, http_client_session: aiohttp.ClientSession) -> None:
        self.http_client_session = http_client_session

    async def start_job(
        self, *, job_def: JobDescription, site: SiteName, service_account_token: UserToken,
    ) -> "JobSubmission | Exception":
        payload: JsonValue = toJsonValue({
            "job_def": job_def,
            "site": site,
            "user_info": service_account_token.access_token
        })
        # print(f"Posting this payload:\n{json.dumps(payload, indent=4)}")

        resp = requests.post(
            self.API_URL.concatpath("jobs/").raw + "/",
            json=payload,
            headers=service_account_token.as_auth_header(),
        )
        if resp.status_code // 100 != 2:
            return Exception(f"Request failed {resp.status_code}: {resp.text}")

        return JobSubmission.from_json_value(await resp.json())


