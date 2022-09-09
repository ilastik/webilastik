import os
from pathlib import PurePosixPath
from typing import ClassVar, Dict, Optional, Mapping
import json
import requests

from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientResponseError
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString, ensureOptional

from webilastik.libebrains.user_info import UserInfo
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Url

class UserToken:
    EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME = "EBRAINS_USER_ACCESS_TOKEN"
    EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME = "EBRAINS_USER_REFRESH_TOKEN"

    _global_login_token: "ClassVar[UserToken | None]" = None

    def __init__(
        self,
        *,
        access_token: str,
        refresh_token: str,
    ):
        api_url = Url.parse("https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect")
        assert api_url is not None
        self._api_url = api_url
        self.access_token = access_token
        self.refresh_token = refresh_token
        super().__init__()

    async def async_refreshed(self, *, http_client_session: ClientSession) -> "UserToken | Exception":
        from webilastik.libebrains.oidc_client import EBRAINS_CLIENT_ID, EBRAINS_CLIENT_SECRET

        resp = await http_client_session.request(
            method="post",
            url="https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            allow_redirects=False,
            data={
                "client_id": EBRAINS_CLIENT_ID,
                "client_secret": EBRAINS_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
        )
        if not resp.ok:
            return Exception(f"Could not refresh user token via refresh_token: {await resp.text()}")

        data = ensureJsonObject(await resp.json())
        return UserToken.from_json_value(data)

    def refreshed(self) -> "UserToken | Exception":
        from webilastik.libebrains.oidc_client import EBRAINS_CLIENT_ID, EBRAINS_CLIENT_SECRET

        resp = requests.post(
            "https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            allow_redirects=False,
            data={
                "client_id": EBRAINS_CLIENT_ID,
                "client_secret": EBRAINS_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
        )
        if not resp.ok:
            return Exception(f"Could not refresh user token via refresh_token: {resp.text}")

        data = ensureJsonObject(resp.json())
        return UserToken.from_json_value(data)

    @classmethod
    def from_environment(cls) -> "UserToken | UsageError":
        access_token = os.environ.get(cls.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME)
        refresh_token = os.environ.get(cls.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME)
        if access_token is None or refresh_token is None:
            print(f"Environment variables '{cls.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME}' and '{cls.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME}' must be set")
            return UsageError(
                f"Environment variables '{cls.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME}' and '{cls.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME}' must be set"
            )
        try:
            return UserToken(access_token=access_token, refresh_token=refresh_token)
        except Exception as e:
            return UsageError(str(e))

    @classmethod
    def login_globally(cls, token: "UserToken"):
        cls._global_login_token = token
        os.environ[cls.EBRAINS_USER_ACCESS_TOKEN_ENV_VAR_NAME] = token.access_token
        os.environ[cls.EBRAINS_USER_REFRESH_TOKEN_ENV_VAR_NAME] = token.refresh_token

    @classmethod
    def login_globally_from_environment(cls):
        token_result = cls.from_environment()
        if isinstance(token_result, UsageError):
            raise token_result
        cls.login_globally(token_result)

    @classmethod
    def get_global_login_token(cls) -> "UserToken | UsageError":
        if cls._global_login_token is None:
            token_result = cls.from_environment()
            if isinstance(token_result, UsageError):
                return token_result
            cls._global_login_token = token_result
        return cls._global_login_token

    @classmethod
    def get_global_token_or_raise(cls) -> "UserToken":
        token = cls.get_global_login_token()
        if isinstance(token, UsageError):
            raise token
        return token

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "UserToken":
        value_obj = ensureJsonObject(value)
        return UserToken(
            access_token=ensureJsonString(value_obj.get("access_token")),
            refresh_token=ensureJsonString(value_obj.get("refresh_token")),
        )

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
