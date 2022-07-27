import dataclasses
from typing import Optional
import uuid
import datetime
from ndstructs.utils.json_serializable import JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString, ensureOptional, toJsonValue

from webilastik.utility.url import Url
from webilastik.libebrains.user_token import UserToken
from webilastik.libebrains.job import JobDescription, JobStatus, SiteName
from webilastik.libebrains.service_token import ServiceToken

import aiohttp

# https://wiki.ebrains.eu/bin/view/Collabs/ebrains-hpc-job-proxy/User%20documentation/

class JobProxyClient:
    API_URL: Url = Url.parse_or_raise("https://unicore-job-proxy.apps.hbp.eu/api")

    def __init__(self, http_client_session: aiohttp.ClientSession, service_token: ServiceToken) -> None:
        self.http_client_session = http_client_session
        self.service_token = service_token
        super().__init__()

    async def start_job(
        self, *, job_def: JobDescription, site: SiteName, end_user_token: UserToken,
    ) -> "JobSubmission | Exception":
        payload: JsonValue = toJsonValue({
            "job_def": job_def,
            "site": site.value,
            "user_info": end_user_token.access_token
        })
        # print(f"Posting this payload:\n{json.dumps(payload, indent=4)}")

        resp = await self.http_client_session.post(
            self.API_URL.concatpath("jobs/").raw + "/",
            json=payload,
            headers={"Authorization": f"Bearer {self.service_token.access_token}"},
        )
        if not resp.ok:
            return Exception(f"Request failed {await resp.text()}: {resp.text}")

        try:
            return JobSubmission.from_json_value(await resp.json())
        except Exception as e:
            return e


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


