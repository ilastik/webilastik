import os
from pathlib import PurePosixPath
from typing import Dict, Optional, Mapping
import requests

from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientResponseError
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString, ensureOptional
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.server.rpc.dto import EbrainsUserTokenDto

from webilastik.libebrains.user_info import UserInfo
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Url

class UserToken:
    def __init__(
        self,
        *,
        access_token: str,
        refresh_token: Optional[str],
    ):
        api_url = Url.parse("https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect")
        assert api_url is not None
        self._api_url = api_url
        self.access_token = access_token
        self.refresh_token = refresh_token
        super().__init__()

    @classmethod
    async def async_from_code(cls, *, code: str, redirect_uri: Url, http_client_session: ClientSession, oidc_client: OidcClient) -> "UserToken":
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri.raw,
            "client_id": oidc_client.client_id,
            "client_secret": oidc_client.client_secret,
        }
        resp = await http_client_session.request(
            method="post",
            url="https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            allow_redirects=False,
            data=data
        )
        resp.raise_for_status()

        data = ensureJsonObject(await resp.json())
        return UserToken.from_json_value(data)

    async def async_refreshed(self, *, http_client_session: ClientSession, oidc_client: OidcClient) -> "UserToken | Exception":
        if self.refresh_token is None:
            return Exception(f"No refresh token available")
        resp = await http_client_session.request(
            method="post",
            url="https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            allow_redirects=False,
            data={
                "client_id": oidc_client.client_id,
                "client_secret": oidc_client.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
        )
        if not resp.ok:
            return Exception(f"Could not refresh user token via refresh_token: {await resp.text()}")

        data = ensureJsonObject(await resp.json())
        return UserToken.from_json_value(data)

    def refreshed(self, *, oidc_client: OidcClient) -> "UserToken | Exception":
        if self.refresh_token is None:
            return Exception(f"No refresh token available")
        resp = requests.post(
            "https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            allow_redirects=False,
            data={
                "client_id": oidc_client.client_id,
                "client_secret": oidc_client.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
        )
        if not resp.ok:
            return Exception(f"Could not refresh user token via refresh_token: {resp.text}")

        data = ensureJsonObject(resp.json())
        return UserToken.from_json_value(data)

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "UserToken":
        value_obj = ensureJsonObject(value)
        return UserToken(
            access_token=ensureJsonString(value_obj.get("access_token")),
            refresh_token=ensureJsonString(value_obj.get("refresh_token")),
        )

    @classmethod
    def from_dto(cls, dto: EbrainsUserTokenDto) -> "UserToken":
        return UserToken(access_token=dto.access_token, refresh_token=dto.refresh_token)

    # def to_dto(self) -> EbrainsUserTokenDto:
    #     return EbrainsUserTokenDto(access_token=self.access_token, refresh_token=self.refresh_token)

    # FIXME: remove this
    def to_json_value(self) -> JsonObject:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }

    def as_auth_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _get(
        self,
        path: PurePosixPath,
        *,
        params: Optional[Mapping[str, str]] = None,
        headers: Optional[Mapping[str, str]] = None,
        http_client_session: ClientSession,
    ) -> JsonValue:
        url = self._api_url.concatpath(path).updated_with(search={})
        resp = await http_client_session.request(
            method="GET",
            url=url.raw,
            params={**url.search, **(params or {})},
            headers={
                **(headers or {}),
                **self.as_auth_header(),
            },
            raise_for_status=True,
        )
        resp.raise_for_status
        return await resp.json()

    async def is_valid(self, http_client_session: ClientSession) -> bool:
        #FIXME: maybe just validate signature + time ?
        try:
            user_info_result = await self.get_userinfo(http_client_session)
            return isinstance(user_info_result, UserInfo)
        except ClientResponseError:
            return False

    async def get_userinfo(self, http_client_session: ClientSession) -> "UserInfo | Exception":
        try:
            return UserInfo.from_json_value(await self._get(
                path=PurePosixPath("userinfo"), http_client_session=http_client_session
            ))
        except Exception as e:
            return e
