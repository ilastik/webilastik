#pyright: strict

from pathlib import PurePosixPath
from typing import Optional, Set, Iterable
import os
import enum
import uuid

from aiohttp.client import ClientSession
from ndstructs.utils.json_serializable import JsonValue, ensureJsonObject, ensureJsonString

from webilastik.libebrains.user_token import UserToken
from webilastik.utility.url import Url, Protocol

EBRAINS_CLIENT_ID = os.environ["EBRAINS_CLIENT_ID"]
EBRAINS_CLIENT_SECRET = os.environ["EBRAINS_CLIENT_SECRET"]

class Scope(enum.Enum):
    # This scope is required because we use the OIDC protocol. It will give your app access to the
    # user's basic information such as username, email and full name.
    OPENID = "openid"
    # (optional): More information on user if provided by the user
    PROFILE = "profile"
    # (optional): The verified email of the user, should be add in addition of openid and/or profile to get the email.
    EMAIL = "email"
    # (optional): If you request this scope, the future access token generated will authorize your app to identify which units and groups the user belongs to.
    GROUP = "group"
    # (optional): This scope is like the group scope lets your app identify the permissions of the user, but by identifying what collabs the user has access to and with what roles.
    TEAM = "team"
    # (optional): access to GET Collab API
    CLB_WIKI_READ = "clb.wiki.read"
    # (optional): access to DELETE/PUT/POST Collab API
    CLB_WIKI_WRITE = "clb.wiki.write"
    # (optional): access to GET/POST/PUT/DELETE drive API
    COLLAB_DRIVE = "collab.drive"
    COLLAB_DRIVE_READ = "clb.drive:read"
    COLLAB_DRIVE_WRITE = "clb.drive:write"
    # (optional): provide refresh token
    OFFLINE_ACCESS = "offline_access"
    MICROPROFILE_JWT = "microprofile-jwt"

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "Scope":
        value_str = ensureJsonString(value)
        for scope in Scope:
            if scope.value == value_str:
                return scope
        raise ValueError(f"Bad scope: {value_str}")

    def to_json_value(self) -> str:
        return self.value

    @staticmethod
    def iterable_to_json_value(scopes: Iterable["Scope"]) -> str:
        return " ".join(s.to_json_value() for s in scopes)


class OidcClient:
    """A Client from the OIDC perspective (e.g.: "webilastik-server-app").

    Not to be confused with an http client"""
    def __init__(self, *, client_id: str, client_secret: str):
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        super().__init__()

    @classmethod
    def from_environment(cls) -> "OidcClient":
        return OidcClient(client_id=EBRAINS_CLIENT_ID, client_secret=EBRAINS_CLIENT_SECRET)

    async def get_user_token(self, *, code: str, redirect_uri: Url, http_client_session: ClientSession) -> "UserToken":
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri.raw,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
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

    def create_user_login_url(self, *, redirect_uri: Url, scopes: Optional[Set["Scope"]] = None, state: Optional[str] = None) -> Url:
        scopes = scopes or set()

        return Url(
            protocol=Protocol.HTTPS,
            hostname="iam.ebrains.eu",
            path=PurePosixPath("/auth/realms/hbp/protocol/openid-connect/auth"),
            search={
                "response_type": "code",
                "login": "true",
                "client_id": self.client_id,
                "redirect_uri": redirect_uri.raw,
                "scope": Scope.iterable_to_json_value(scopes.union([Scope.OPENID])),
                "state": state if state is not None else str(uuid.uuid4()),
            }
        )