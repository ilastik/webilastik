import json
from pathlib import PurePosixPath
from typing import Any, Mapping, Optional, Union, Dict, List
from datetime import datetime

import aiohttp
from ndstructs.utils.json_serializable import JsonValue, ensureJsonInt, ensureJsonObject, ensureJsonString
import requests
from webilastik.filesystem.http_fs import HttpFs

from webilastik.libebrains.user_token import UserToken
from webilastik.utility.url import Url

HtmlParams = Mapping[str, Union[str, List[str]]]
HtmlHeaders = Mapping[str, str]

def _clean_params(params: Mapping[str, Any]) -> Dict[str, str]:
    return {key: str(value) for key, value in params.items() if value is not None}

class Bucket:
    def __init__(
        self, name: str, user_token: UserToken, session: aiohttp.ClientSession
    ):
        self._api_url = Url.parse("https://data-proxy.ebrains.eu/api")
        self.name = name
        self.user_token = user_token
        self.session = session

    async def _get(
        self, endpoint: str, *, params: Optional[HtmlParams] = None, headers: Optional[HtmlHeaders] = None
    ) -> JsonValue:
        headers = {**(headers or {}), **self.user_token.as_auth_header()}
        async with self.session.get(self._api_url.joinpath(endpoint).raw, params=params or {}, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    async def list_objects(
        self,
        *,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        limit: Optional[int] = None,
    ): # FIXME
        data = await self._get(f"buckets/{self.name}", params=_clean_params({"prefix": prefix, "delimiter": delimiter, "limit": limit}))
        print(json.dumps(data, indent=4))

    async def get_temp_url(
        self, *, prefix: Optional[str] = None, lifetime: str = "very_long"
    ): # FIXME
        data = await self._get(f"tempurl/{self.name}", params=_clean_params({"lifetime": lifetime, "prefix": prefix}))
        print(json.dumps(data, indent=4))

    @staticmethod
    def default_bucket(*, user_token: UserToken, session: aiohttp.ClientSession) -> "Bucket":
        return Bucket(
            name="hbp-image-service",
            user_token=user_token,
            session=session,
        )

class BucketObject:
    def __init__(
        self,
        *,
        hash_: str,
        last_modified: datetime,
        bytes_: int,
        name: PurePosixPath,
        content_type: str
    ):
        self.hash = hash_
        self.last_modified = last_modified
        self.bytes = bytes_
        self.name = name
        self.content_type = content_type

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "BucketObject":
        value_dict = ensureJsonObject(value)
        return BucketObject(
            hash_ = ensureJsonString(value_dict.get("hash")),
            last_modified=datetime.fromisoformat(ensureJsonString(value_dict.get("last_modified"))),
            bytes_=ensureJsonInt(value_dict.get("bytes")),
            name=PurePosixPath(ensureJsonString(value_dict.get("name"))),
            content_type=ensureJsonString(value_dict.get("content_type")),
        )

    def to_json_value(self) -> JsonValue:
        return {
            "hash": self.hash,
            "last_modified": self.last_modified.isoformat(),
            "bytes": self.bytes,
            "name": str(self.name),
            "content_type": self.content_type,
        }

class BucketFs(HttpFs):
    def __init__(self, bucket: Bucket):
        super().__init__(
            read_url=bucket._api_url.concatpath(f"buckets/{bucket.name}").updated_with(search={"redirect": "true"}),
            write_url=bucket._api_url.concatpath(f"buckets/{bucket.name}"),
            headers=bucket.user_token.as_auth_header()
        )
        self.writing_session = requests.Session()

    def _put_object(self, subpath: str, contents: bytes) -> requests.Response:
        full_path = self.write_url.concatpath(subpath)
        assert full_path.raw != "/"

        response = self.session.put(full_path.raw, verify=self.requests_verify)
        response.raise_for_status()
        tmp_url = response.json()["url"]

        response = self.writing_session.put(
            tmp_url, data=contents, headers={"Content-Type": "application/octet-stream"}, verify=self.requests_verify
        )
        response.raise_for_status()
        return response
