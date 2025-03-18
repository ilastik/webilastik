# pyright: strict

from pathlib import PurePosixPath
from typing import ClassVar, Dict, Final, Literal
from typing_extensions import assert_never
import uuid
from datetime import datetime, timezone, timedelta

import requests
import aiohttp
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from aiohttp.client import ClientSession

from webilastik.server.rpc.dto import EbrainsAccessTokenHeaderDto, EbrainsAccessTokenPayloadDto, EbrainsAccessTokenDto, HbpIamPublicKeyDto
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_info import UserInfo
from webilastik.serialization.json_serialization import parse_json, JsonValue
from webilastik.server.util import urlsafe_b64decode
from webilastik.utility.url import Url
from webilastik.utility import parse_uuid
from webilastik.utility.log import Logger

logger = Logger()

class EbrainsCommunicationFailure(Exception):
    def __init__(self, message: str = "") -> None:
        super().__init__(f"Failed communicating with ebrains: {message}")

class CantFetchHbpIamKey(EbrainsCommunicationFailure):
    def __init__(self, message: str = '') -> None:
        super().__init__(f"Could not fetch HBP IAM public key {message}")

class AccessTokenExpired(Exception):
    def __init__(self) -> None:
        super().__init__("Access token expired")

class AccessTokenInvalid(Exception):
    def __init__(self, message: str = "") -> None:
        super().__init__(f"Access token is invalid: {message}")

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
    async def get_async(cls) -> "HbpIamPublicKey | CantFetchHbpIamKey":
        cached_intance = cls.get_cached_instance()
        if cached_intance:
            return cached_intance

        response = await aiohttp.ClientSession().get(url=cls.key_fetch_endpoint)
        if not response.ok:
            return CantFetchHbpIamKey()
        try:
            payload = await response.text()
        except Exception as _:
            return CantFetchHbpIamKey("Garbled response")
        return cls._process_get_payload(payload)

    @classmethod
    def get_sync(cls) -> "HbpIamPublicKey | CantFetchHbpIamKey":
        cached_intance = cls.get_cached_instance()
        if cached_intance:
            return cached_intance

        response = requests.get(url=cls.key_fetch_endpoint)
        if not response.ok:
            return CantFetchHbpIamKey(f"Could not fetch HBP Iam public key")
        try:
            payload = response.text
        except Exception:
            return CantFetchHbpIamKey()
        return cls._process_get_payload(payload)

    @classmethod
    def _process_get_payload(cls, payload: str) -> "HbpIamPublicKey | CantFetchHbpIamKey":
        payload_obj_result = parse_json(payload)
        if isinstance(payload_obj_result, Exception):
            return CantFetchHbpIamKey("Could not deserialize payload as json")

        dto = HbpIamPublicKeyDto.from_json_value(payload_obj_result)
        if isinstance(dto, Exception):
            return CantFetchHbpIamKey("Could not parse payload's message structure")
        key_result = HbpIamPublicKey.from_dto(dto)
        if isinstance(key_result, Exception):
            return CantFetchHbpIamKey("Could not parse key")
        cls._instance = key_result
        return key_result

    @classmethod
    def from_dto(cls, dto: HbpIamPublicKeyDto) -> "HbpIamPublicKey | CantFetchHbpIamKey":
        public_key_pem = "-----BEGIN RSA PUBLIC KEY-----\n"
        cursor = 0
        while cursor < len(dto.public_key):
            end = min(cursor  + 64, len(dto.public_key))
            public_key_pem += dto.public_key[cursor : end] + "\n"
            cursor = end
        public_key_pem += "-----END RSA PUBLIC KEY-----\n"

        try:
            key = load_pem_public_key(data=public_key_pem.encode("utf8"))
            if not isinstance(key, RSAPublicKey):
                return CantFetchHbpIamKey(f"Could not decode key as an RSA public key")
        except Exception as e:
            return CantFetchHbpIamKey(f"Could not decode key as an RSA public key: {e}")

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
    def from_raw(cls, raw: str) -> "AccessTokenHeader | AccessTokenInvalid":
        header_json_str = urlsafe_b64decode(raw)
        if isinstance(header_json_str ,Exception):
            return AccessTokenInvalid(f"Could not b64 decode token header")
        json_obj = parse_json(header_json_str)
        if isinstance(json_obj, Exception):
            return AccessTokenInvalid("Access token could not be parsed as json object")
        dto_result =  EbrainsAccessTokenHeaderDto.from_json_value(json_obj)
        if isinstance(dto_result, Exception):
            return AccessTokenInvalid("Access token could not be parsed as token message")
        return AccessTokenHeader(
            _marker=cls._PrivateMarker(),
            raw=raw,
            alg=dto_result.alg
        )


class AccessTokenPayload:
    class _PrivateMarker:
        pass

    def __init__(
        self, _marker: _PrivateMarker, raw: str, exp: datetime, auth_time: datetime, sub: uuid.UUID
    ) -> None:
        super().__init__()
        self.raw: Final[str] = raw
        self.exp = exp
        self.auth_time = auth_time
        self.sub = sub
        # my_timezone = datetime.now(timezone.utc).astimezone().tzinfo
        # print(f"%%%%%%% AccessToken auth time is {self.auth_time.astimezone(my_timezone)}")

    @classmethod
    def from_raw(cls, raw: str) -> "AccessTokenPayload | AccessTokenInvalid":
        payload_json_str = urlsafe_b64decode(raw)
        if isinstance(payload_json_str ,Exception):
            return AccessTokenInvalid(f"Could not b64 decode token payload")
        payload_json = parse_json(payload_json_str)
        if isinstance(payload_json, Exception):
            return AccessTokenInvalid("Could not parse raw token payload as json")
        payload_dto = EbrainsAccessTokenPayloadDto.from_json_value(payload_json)
        if isinstance(payload_dto, Exception):
            return AccessTokenInvalid(f"Could not deserialize token payload from json value")
        sub_result = parse_uuid(payload_dto.sub)
        if isinstance(sub_result, Exception):
            return AccessTokenInvalid("Could not parse user id as UUID")

        return AccessTokenPayload(
            _marker=cls._PrivateMarker(),
            raw=raw,
            exp=datetime.fromtimestamp(payload_dto.exp, timezone.utc),
            auth_time=datetime.fromtimestamp(payload_dto.auth_time, timezone.utc),
            sub=sub_result,
        )

    @property
    def expired(self) -> bool:
        return datetime.now(tz=timezone.utc) > self.exp


class AccessToken:
    class _PrivateMarker:
        pass

    def __init__(
        self,
        *,
        _marker: _PrivateMarker,
        header: AccessTokenHeader,
        payload: AccessTokenPayload,
        raw_signature: str,
        refresh_token: str,
    ) -> None:
        super().__init__()
        api_url = Url.parse("https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect")
        assert api_url is not None
        self._api_url = api_url
        self.header: AccessTokenHeader = header
        self.payload = payload
        self.raw_token: Final[str] = header.raw + "." + payload.raw + "." + raw_signature
        self.refresh_token = refresh_token

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AccessToken):
            return False
        return self.raw_token == other.raw_token

    @property
    def user_id(self) -> uuid.UUID:
        return self.payload.sub

    def to_dto(self) -> EbrainsAccessTokenDto:
        return EbrainsAccessTokenDto(access_token=self.raw_token, refresh_token=self.refresh_token)

    def get_status(self, checking_key: HbpIamPublicKey) -> Literal['expired', 'invalid', 'valid']:
        if self.payload.expired:
            return "expired"
        if checking_key.check(raw_token=self.raw_token):
            return "valid"
        return "invalid"

    @classmethod
    def from_webilastik_client_headers(
        cls, auth_header: str, refresh_header: str, checking_key: HbpIamPublicKey
    ) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid":
        parts = auth_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return AccessTokenInvalid("Badly encoded authentication token")
        return cls.from_raw_token(raw_token=parts[1], refresh_token=refresh_header, checking_key=checking_key)

    def as_ebrains_auth_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.raw_token}"}

    async def get_userinfo(self, http_client_session: ClientSession) -> "UserInfo | Exception":
        url = self._api_url.concatpath(PurePosixPath("userinfo")).updated_with(search={})
        resp = await http_client_session.request(
            method="GET",
            url=url.raw,
            headers=self.as_ebrains_auth_header(),
            raise_for_status=True,
        )
        if not resp.ok:
            return Exception("Could not retrieve user info")

        try:
            data = await resp.json()
        except Exception:
            return Exception("Could not parse userinfo response as json")
        return UserInfo.from_json_value(data)

    @classmethod
    def try_from_refresh_token_sync(
        cls, *, oidc_client: OidcClient, refresh_token: str
    ) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid | EbrainsCommunicationFailure":
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
                "refresh_token": refresh_token,
            }
        )
        if not resp.ok:
            return EbrainsCommunicationFailure(f"Could not refresh user token via refresh_token: {resp.text}")

        try:
            data = resp.json()
        except Exception:
            return AccessTokenInvalid("Could not parse user token as json")
        return cls.from_json_value(data, checking_key=checking_key_result)

    def refreshed(self, oidc_client: OidcClient) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid | EbrainsCommunicationFailure":
        return self.try_from_refresh_token_sync(oidc_client=oidc_client, refresh_token=self.refresh_token)

    @classmethod
    async def try_from_refresh_token_async(
        cls, *, http_client_session: ClientSession, oidc_client: OidcClient, refresh_token: str
    ) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid | EbrainsCommunicationFailure":
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
                "refresh_token": refresh_token,
            }
        )
        if not resp.ok:
            return EbrainsCommunicationFailure(f"Could not refresh user token via refresh_token: {await resp.text()}")

        try:
            data = await resp.json()
        except Exception:
            return AccessTokenInvalid("Could not parse user token as josn")
        return cls.from_json_value(data, checking_key=checking_key_result)

    @classmethod
    async def from_code_async(
        cls,
        *,
        code: str,
        redirect_uri: Url,
        http_client_session: ClientSession,
        oidc_client: OidcClient,
        checking_key: HbpIamPublicKey,
    ) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid | EbrainsCommunicationFailure":
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
        if not resp.ok:
            return EbrainsCommunicationFailure("Could not fetch token from code")

        try:
            data = await resp.json()
        except Exception:
            return AccessTokenInvalid("Could not parse raw token response as json")
        return cls.from_json_value(data, checking_key=checking_key)

    @classmethod
    def from_json_value(cls, value: JsonValue, *, checking_key: HbpIamPublicKey) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid":
        dto_result = EbrainsAccessTokenDto.from_json_value(value)
        if isinstance(dto_result, Exception):
            return AccessTokenInvalid("Could not parse refresh token payload")
        return cls.from_dto(dto_result, checking_key=checking_key)

    @classmethod
    def from_dto(cls, dto: EbrainsAccessTokenDto, checking_key: HbpIamPublicKey) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid":
        return AccessToken.from_raw_token(
            raw_token=dto.access_token, checking_key=checking_key, refresh_token=dto.refresh_token
        )

    @classmethod
    def from_raw_token(cls, *, raw_token: str, refresh_token: str, checking_key: HbpIamPublicKey) -> "AccessToken | AccessTokenExpired | AccessTokenInvalid":
        parts = raw_token.split(".")
        if len(parts) != 3:
            return AccessTokenInvalid(f"Bad user token. Should have 3 parts, found {len(parts)}")
        serialized_header, serialized_payload, serialized_signature = parts

        header_result = AccessTokenHeader.from_raw(serialized_header)
        if isinstance(header_result, Exception):
            return header_result

        payload_result = AccessTokenPayload.from_raw(serialized_payload)
        if isinstance(payload_result, Exception):
            return payload_result

        access_token = AccessToken(
            _marker=cls._PrivateMarker(),
            header=header_result,
            payload=payload_result,
            raw_signature=serialized_signature,
            refresh_token=refresh_token,
        )
        status =  access_token.get_status(checking_key=checking_key)
        if status == "valid":
            return access_token
        if status == "expired":
            return AccessTokenExpired()
        if status == "invalid":
            return AccessTokenInvalid()
        assert_never(status)
