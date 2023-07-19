import os
from pathlib import PurePosixPath
from typing import ClassVar, Dict, Final, Literal, Optional, Mapping
from typing_extensions import assert_never
import requests
from datetime import datetime, timezone, timedelta

import aiohttp
import jwt
from cryptography.hazmat.backends.openssl.backend import backend as ossl
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.asymmetric import padding


from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientResponseError
from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonObject, ensureJsonString, ensureOptional

from webilastik.server.rpc.dto import EbrainsAccessTokenHeaderDto, EbrainsAccessTokenPayloadDto, EbrainsUserTokenDto, HbpIamPublicKeyDto
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_info import UserInfo
from webilastik.serialization.json_serialization import parse_json
from webilastik.server.util import urlsafe_b64decode
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Url

class HbpIamPublicKey:
    _instance: ClassVar["HbpIamPublicKey | None"] = None
    key_fetch_endpoint: Final[str] = "https://iam.ebrains.eu/auth/realms/hbp/"

    @classmethod
    def get_cached_instance(cls) -> "HbpIamPublicKey | None":
        if cls._instance is None or cls._instance.is_stale:
            return None
        return cls._instance

    def __init__(self, public_key: RSAPublicKey) -> None:
        super().__init__()
        self.public_key: Final[RSAPublicKey] = public_key
        self.creation_time = datetime.now(tz=timezone.utc)

    @property
    def age(self) -> timedelta:
        return datetime.now(tz=timezone.utc) - self.creation_time

    @property
    def is_stale(self) -> bool:
        return self.age < timedelta(days=2)

    @classmethod
    async def get_async(cls) -> "HbpIamPublicKey | Exception":
        cached_intance = cls.get_cached_instance()
        if cached_intance:
            return cached_intance

        response = await aiohttp.ClientSession().get(url=cls.key_fetch_endpoint)
        if not response.ok:
            return Exception(f"Could not fetch HBP Iam public key")
        try:
            payload = await response.text()
        except Exception as e:
            return e
        return cls._process_get_payload(payload)

    @classmethod
    def get_sync(cls) -> "HbpIamPublicKey | Exception":
        cached_intance = cls.get_cached_instance()
        if cached_intance:
            return cached_intance

        response = requests.get(url=cls.key_fetch_endpoint)
        if not response.ok:
            return Exception(f"Could not fetch HBP Iam public key")
        try:
            payload = response.text
        except Exception as e:
            return e
        return cls._process_get_payload(payload)

    @classmethod
    def _process_get_payload(cls, payload: str) -> "HbpIamPublicKey | Exception":
        payload_obj_result = parse_json(payload)
        if isinstance(payload_obj_result, Exception):
            return payload_obj_result

        dto = HbpIamPublicKeyDto.from_json_value(payload_obj_result)
        if isinstance(dto, Exception):
            return dto
        key_result = HbpIamPublicKey.from_dto(dto)
        if isinstance(key_result, Exception):
            return key_result
        cls._instance = key_result
        return key_result

    @classmethod
    def from_dto(cls, dto: HbpIamPublicKeyDto) -> "HbpIamPublicKey | Exception":
        public_key_pem = "-----BEGIN RSA PUBLIC KEY-----\n"
        cursor = 0
        while cursor < len(dto.public_key):
            end = min(cursor  + 64, len(dto.public_key))
            public_key_pem += dto.public_key[cursor : end] + "\n"
            cursor = end
        public_key_pem += "-----END RSA PUBLIC KEY-----\n"

        try:
            key = ossl.load_pem_public_key(data=public_key_pem.encode("utf8"))
            if not isinstance(key, RSAPublicKey):
                return Exception(f"Could not decode key as an RSA public key")
        except Exception:
            return Exception(f"Could not decode key as an RSA public key")

        return HbpIamPublicKey(public_key=key)

    def check(self, raw_token: str) -> bool:
        try:
            jwt.decode(raw_token, key=self.public_key, algorithms=['RS256'], audience=["jupyterhub", "jupyterhub-jsc", "team", "group"])
            return True
        except Exception:
            return False

# try to grab the key right now and warm the cache
if isinstance(HbpIamPublicKey.get_sync(), Exception):
    print("Warning: could not fetch HBP public token key")

class AccessTokenHeader:
    class _PrivateMarker:
        pass

    def __init__(self, _marker: _PrivateMarker, raw: str, alg: Literal["RS256"]) -> None:
        super().__init__()
        self.raw: Final[str] = raw
        self.alg: Literal["RS256"] = alg

    @classmethod
    def from_raw(cls, raw: str) -> "AccessTokenHeader | Exception":
        header_json_str = urlsafe_b64decode(raw)
        if isinstance(header_json_str ,Exception):
            return Exception(f"Could not b64 decode token header")
        json_obj = parse_json(header_json_str)
        if isinstance(json_obj, Exception):
            return json_obj
        dto_result =  EbrainsAccessTokenHeaderDto.from_json_value(json_obj)
        if isinstance(dto_result, Exception):
            return dto_result
        return AccessTokenHeader(
            _marker=cls._PrivateMarker(),
            raw=raw,
            alg=dto_result.alg
        )


class AccessTokenPayload:
    class _PrivateMarker:
        pass

    def __init__(self, _marker: _PrivateMarker, raw: str, exp: datetime) -> None:
        super().__init__()
        self.raw: Final[str] = raw
        self.exp = exp

    @classmethod
    def from_raw(cls, raw: str) -> "AccessTokenPayload | Exception":
        payload_json_str = urlsafe_b64decode(raw)
        if isinstance(payload_json_str ,Exception):
            return Exception(f"Could not b64 decode token payload")
        payload_json = parse_json(payload_json_str)
        if isinstance(payload_json, Exception):
            return Exception("Could not parse raw token payload as json")
        payload_dto = EbrainsAccessTokenPayloadDto.from_json_value(payload_json)
        if isinstance(payload_dto, Exception):
            return Exception(f"Could not deserialize token payload from json value")
        return AccessTokenPayload(
            _marker=cls._PrivateMarker(),
            raw=raw,
            exp = datetime.fromtimestamp(payload_dto.exp, timezone.utc)
        )

    @property
    def expired(self) -> bool:
        return datetime.now(tz=timezone.utc) > self.exp


class AccessToken:
    class _PrivateMarker:
        pass

    def __init__(
        self, *, _marker: _PrivateMarker, header: AccessTokenHeader, payload: AccessTokenPayload, raw_signature: str
    ) -> None:
        super().__init__()
        self.header: AccessTokenHeader = header
        self.payload = payload
        self.raw_token: Final[str] = header.raw + "." + payload.raw + "." + raw_signature

    def is_valid(self, checking_key: HbpIamPublicKey) -> bool:
        if self.payload.expired:
            return False
        return checking_key.check(raw_token=self.raw_token)

    @classmethod
    def create(cls, header: AccessTokenHeader, payload: AccessTokenPayload, raw_signature: str) -> "AccessToken | Exception":
        if header.alg == "RS256":
            return AccessToken(_marker=cls._PrivateMarker(), header=header, payload=payload, raw_signature=raw_signature)
        assert_never(header.alg)

    @classmethod
    def from_raw_token(cls, raw_token: str, checking_key: HbpIamPublicKey) -> "AccessToken | Exception":
        parts = raw_token.split(".")
        if len(parts) != 3:
            return Exception(f"Bad user token. Should have 3 parts, found {len(parts)}")
        serialized_header, serialized_payload, serialized_signature = parts

        header_result = AccessTokenHeader.from_raw(serialized_header)
        if isinstance(header_result, Exception):
            return header_result

        payload_result = AccessTokenPayload.from_raw(serialized_payload)
        if isinstance(payload_result, Exception):
            return payload_result

        access_token = AccessToken(
            _marker=cls._PrivateMarker(), header=header_result, payload=payload_result, raw_signature=serialized_signature
        )
        if not access_token.is_valid(checking_key=checking_key):
            return Exception("Token is not valid!")

        return access_token


class UserToken:
    def __init__(
        self,
        *,
        access_token: AccessToken,
        refresh_token: str,
    ):
        api_url = Url.parse("https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect")
        assert api_url is not None
        self._api_url = api_url
        self.access_token = access_token
        self.refresh_token = refresh_token
        super().__init__()

    @classmethod
    async def async_from_code(
        cls, *, code: str, redirect_uri: Url, http_client_session: ClientSession, oidc_client: OidcClient
    ) -> "UserToken | Exception":
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

        try:
            data = await resp.json()
        except Exception:
            return Exception("Could not parse raw token response as json")

        checking_key_result = await HbpIamPublicKey.get_async()
        if isinstance(checking_key_result, Exception):
            return checking_key_result

        return UserToken.from_json_value(data, checking_key=checking_key_result)

    async def async_refreshed(self, *, http_client_session: ClientSession, oidc_client: OidcClient) -> "UserToken | Exception":
        checking_key_result = await HbpIamPublicKey.get_async()
        if isinstance(checking_key_result, Exception):
            return checking_key_result

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

        try:
            data = await resp.json()
        except Exception:
            return Exception("Could not parse user token as josn")
        return UserToken.from_json_value(data, checking_key=checking_key_result)

    def refreshed(self, *, oidc_client: OidcClient) -> "UserToken | Exception":
        checking_key_result = HbpIamPublicKey.get_sync()
        if isinstance(checking_key_result, Exception):
            return checking_key_result

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

        try:
            data = resp.json()
        except Exception:
            return Exception("Could not parse user token as json")
        return UserToken.from_json_value(data, checking_key=checking_key_result)

    @classmethod
    def from_dto(cls, dto: EbrainsUserTokenDto, checking_key: HbpIamPublicKey) -> "UserToken | Exception":
        acces_token_result = AccessToken.from_raw_token(dto.access_token, checking_key=checking_key)
        if isinstance(acces_token_result, Exception):
            return acces_token_result
        refresh_token = dto.refresh_token
        return UserToken(access_token=acces_token_result, refresh_token=refresh_token)

    @classmethod
    def from_json_value(cls, value: JsonValue, checking_key: HbpIamPublicKey) -> "UserToken | Exception":
        dto_result = EbrainsUserTokenDto.from_json_value(value)
        if isinstance(dto_result, Exception):
            return dto_result
        access_token_result = AccessToken.from_raw_token(raw_token=dto_result.access_token, checking_key=checking_key)
        if isinstance(access_token_result, Exception):
            return access_token_result
        return UserToken(
            access_token=access_token_result,
            refresh_token=dto_result.refresh_token,
        )

    # def to_json_value(self) -> JsonObject:
    #     return {
    #         "access_token": self.access_token,
    #         "refresh_token": self.refresh_token,
    #     }

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

    async def is_valid(self, http_client_session: ClientSession, checking_key: HbpIamPublicKey) -> bool:
        return self.access_token.is_valid(checking_key=checking_key)

    async def get_userinfo(self, http_client_session: ClientSession) -> "UserInfo | Exception":
        try:
            return UserInfo.from_json_value(await self._get(
                path=PurePosixPath("userinfo"), http_client_session=http_client_session
            ))
        except Exception as e:
            return e
