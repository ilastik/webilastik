import os
from pathlib import PurePosixPath
from typing import Dict, Optional, Mapping

import requests
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString

from webilastik.utility.url import Url



class UserToken:
    ENV_VAR_NAME = "EBRAINS_USER_ACCESS_TOKEN"

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

    @classmethod
    def from_environment(cls) -> "UserToken":
        return UserToken(access_token=os.environ[cls.ENV_VAR_NAME])

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "UserToken":
        value_obj = ensureJsonObject(value)
        raw_refresh_token = value_obj.get("access_token")
        if raw_refresh_token is not None:
            refresh_token = ensureJsonString(raw_refresh_token)
        else:
            refresh_token = None
        return UserToken(
            access_token=ensureJsonString(value_obj.get("access_token")),
            refresh_token=refresh_token
        )

    def to_json_value(self) -> JsonObject:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }

    def as_auth_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get(
        self,
        path: PurePosixPath,
        *,
        params: Optional[Mapping[str, str]] = None,
        headers: Optional[Mapping[str, str]] = None,
        https_verify: bool = True,
    ) -> JsonValue:
        url = self._api_url.joinpath(path).updated_with(search={})
        resp = requests.get(
            url.raw,
            params={**url.search, **(params or {})},
            headers={
                **(headers or {}),
                **self.as_auth_header(),
            },
            verify=https_verify,
        )
        resp.raise_for_status()
        return resp.json()

    def is_valid(self) -> bool:
        #FIXME: maybe just validate signature + time ?
        try:
            _ = self.get_userinfo()
            return True
        except requests.exceptions.HTTPError:
            return False

    def get_userinfo(self) -> JsonObject:
        return ensureJsonObject(self._get(PurePosixPath("userinfo")))
