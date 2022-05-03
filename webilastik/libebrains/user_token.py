import os
from pathlib import PurePosixPath
from typing import ClassVar, Dict, Optional, Mapping
from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientResponseError

import requests
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString, ensureOptional
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url



class UserToken:
    ENV_VAR_NAME = "EBRAINS_USER_ACCESS_TOKEN"

    _global_login_token: "ClassVar[UserToken | None]" = None

    def __init__(
        self,
        *,
        access_token: str,
        refresh_token: Optional[str] = None,
        # expires_in: int,
        # refresh_expires_in: int,
        # token_type: str,
        # id_token: str,
        # not_before_policy: int,
        # session_state: str,
        # scope: str
    ):
        api_url = Url.parse("https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect")
        assert api_url is not None
        self._api_url = api_url
        self.access_token = access_token
        self.refresh_token = refresh_token
        # self.expires_in = expires_in
        # self.refresh_expires_in = refresh_expires_in
        # self.token_type = token_type
        # self.id_token = id_token
        # self.not_before_policy = not_before_policy
        # self.session_state = session_state
        # self.scope = scope
        super().__init__()

    @classmethod
    def from_environment(cls) -> "UserToken | UsageError":
        access_token = os.environ.get(cls.ENV_VAR_NAME)
        if access_token is None:
            return UsageError(f"Environment variable '{cls.ENV_VAR_NAME}' is not set")
        return UserToken(access_token=access_token)

    @classmethod
    def login_globally(cls, token: "UserToken"):
        cls._global_login_token = token

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
            refresh_token=ensureOptional(ensureJsonString, value_obj.get("refresh_token")),
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
            _ = await self.get_userinfo(http_client_session)
            return True
        except ClientResponseError:
            return False

    async def get_userinfo(self, http_client_session: ClientSession) -> JsonObject:
        return ensureJsonObject(await self._get(
            path=PurePosixPath("userinfo"), http_client_session=http_client_session
        ))
