from pathlib import Path, PurePosixPath
from typing import Optional, Sequence, Set, Tuple, Union, Iterable, List
import json

from aiohttp.client import ClientSession
from webilastik.libebrains.user_token import UserToken
import requests
import enum
import uuid

from ndstructs.utils.json_serializable import JsonObject, JsonValue, ensureJsonArray, ensureJsonBoolean, ensureJsonInt, ensureJsonObject, ensureJsonString, ensureJsonStringArray

from webilastik.utility.url import Url, Protocol


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
    def __init__(
        self,
        *,
        alwaysDisplayInConsole: bool,
        # attributes: JsonObject,
        # authenticationFlowBindingOverrides: JsonObject,
        baseUrl: Url,
        bearerOnly: bool,
        clientAuthenticatorType: str,
        clientId: str,
        consentRequired: bool,
        defaultClientScopes: Tuple[str, ...],
        description: str,
        directAccessGrantsEnabled: bool,
        enabled: bool,
        frontchannelLogout: bool,
        fullScopeAllowed: bool,
        id: str,
        implicitFlowEnabled: bool,
        name: str,
        nodeReRegistrationTimeout: int,
        notBefore: int,
        optionalClientScopes: Set["Scope"],
        protocol: str,
        publicClient: bool,
        redirectUris: Tuple[Url, ...],
        registrationAccessToken: str,
        rootUrl: Url,
        secret: str,
        serviceAccountsEnabled: bool,
        standardFlowEnabled: bool,
        surrogateAuthRequired: bool,
        webOrigins: Tuple[str, ...],
    ):
        self.alwaysDisplayInConsole = alwaysDisplayInConsole
        # attributes: JsonObject
        # authenticationFlowBindingOverrides: JsonObject
        self.baseUrl = baseUrl
        self.bearerOnly = bearerOnly
        self.clientAuthenticatorType = clientAuthenticatorType
        self.clientId = clientId
        self.consentRequired = consentRequired
        self.defaultClientScopes = defaultClientScopes
        self.description = description
        self.directAccessGrantsEnabled = directAccessGrantsEnabled
        self.enabled = enabled
        self.frontchannelLogout = frontchannelLogout
        self.fullScopeAllowed = fullScopeAllowed
        self.id = id
        self.implicitFlowEnabled = implicitFlowEnabled
        self.name = name
        self.nodeReRegistrationTimeout = nodeReRegistrationTimeout
        self.notBefore = notBefore
        self.optionalClientScopes = optionalClientScopes
        self.protocol = protocol
        self.publicClient = publicClient
        self.redirectUris = redirectUris
        self.registrationAccessToken = registrationAccessToken
        self.rootUrl = rootUrl
        self.secret = secret
        self.serviceAccountsEnabled = serviceAccountsEnabled
        self.standardFlowEnabled = standardFlowEnabled
        self.surrogateAuthRequired = surrogateAuthRequired
        self.webOrigins = webOrigins
        super().__init__()

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "OidcClient":
        value_obj = ensureJsonObject(value)
        raw_rootUrl = ensureJsonString(value_obj.get("rootUrl"))
        rootUrl = Url.parse(raw_rootUrl)
        if rootUrl is None:
            rootUrl = Url.parse(raw_rootUrl + "/") # it's possible to register a rootUrl without a path -.-
        assert rootUrl is not None

        redirectUris: List[Url] = []
        for raw_redirect_uri in ensureJsonStringArray(value_obj.get("redirectUris")):
            try:
                redirect_uri = Url.parse(raw_redirect_uri)
                assert redirect_uri is not None
                redirectUris.append(redirect_uri)
            except ValueError:
                uri = rootUrl.joinpath(PurePosixPath(raw_redirect_uri)) # FIXME: do leading slashes mean root here too?
                redirectUris.append(uri)

        baseUrl = Url.parse(ensureJsonString(value_obj.get("baseUrl")))
        assert baseUrl is not None
        return OidcClient(
            alwaysDisplayInConsole=ensureJsonBoolean(value_obj.get("alwaysDisplayInConsole")),
            baseUrl=baseUrl,
            bearerOnly=ensureJsonBoolean(value_obj.get("bearerOnly")),
            clientAuthenticatorType=ensureJsonString(value_obj.get("clientAuthenticatorType")),
            clientId=ensureJsonString(value_obj.get("clientId")),
            consentRequired=ensureJsonBoolean(value_obj.get("consentRequired")),
            defaultClientScopes=ensureJsonStringArray(value_obj.get("defaultClientScopes")),
            description=ensureJsonString(value_obj.get("description")),
            directAccessGrantsEnabled=ensureJsonBoolean(value_obj.get("directAccessGrantsEnabled")),
            enabled=ensureJsonBoolean(value_obj.get("enabled")),
            frontchannelLogout=ensureJsonBoolean(value_obj.get("frontchannelLogout")),
            fullScopeAllowed=ensureJsonBoolean(value_obj.get("fullScopeAllowed")),
            id=ensureJsonString(value_obj.get("id")),
            implicitFlowEnabled=ensureJsonBoolean(value_obj.get("implicitFlowEnabled")),
            name=ensureJsonString(value_obj.get("name")),
            nodeReRegistrationTimeout=ensureJsonInt(value_obj.get("nodeReRegistrationTimeout")),
            notBefore=ensureJsonInt(value_obj.get("notBefore")),
            optionalClientScopes=set(Scope.from_json_value(s) for s in ensureJsonArray(value_obj.get("optionalClientScopes"))),
            protocol=ensureJsonString(value_obj.get("protocol")),
            publicClient=ensureJsonBoolean(value_obj.get("publicClient")),
            redirectUris=tuple(redirectUris),
            registrationAccessToken=ensureJsonString(value_obj.get("registrationAccessToken")),
            rootUrl=rootUrl,
            secret=ensureJsonString(value_obj.get("secret")),
            serviceAccountsEnabled=ensureJsonBoolean(value_obj.get("serviceAccountsEnabled")),
            standardFlowEnabled=ensureJsonBoolean(value_obj.get("standardFlowEnabled")),
            surrogateAuthRequired=ensureJsonBoolean(value_obj.get("surrogateAuthRequired")),
            webOrigins=ensureJsonStringArray(value_obj.get("webOrigins")),
        )

    def to_json_value(self) -> JsonObject:
        return {
            "alwaysDisplayInConsole": self.alwaysDisplayInConsole,
            # attributes: JsonObject,
            # authenticationFlowBindingOverrides: JsonObject,
            "baseUrl": str(self.baseUrl),
            "bearerOnly": self.bearerOnly,
            "clientAuthenticatorType": self.clientAuthenticatorType,
            "clientId": self.clientId,
            "consentRequired": self.consentRequired,
            "defaultClientScopes": self.defaultClientScopes,
            "description": self.description,
            "directAccessGrantsEnabled": self.directAccessGrantsEnabled,
            "enabled": self.enabled,
            "frontchannelLogout": self.frontchannelLogout,
            "fullScopeAllowed": self.fullScopeAllowed,
            "id": self.id,
            "implicitFlowEnabled": self.implicitFlowEnabled,
            "name": self.name,
            "nodeReRegistrationTimeout": self.nodeReRegistrationTimeout,
            "notBefore": self.notBefore,
            "optionalClientScopes": tuple(s.to_json_value() for s in self.optionalClientScopes),
            "protocol": self.protocol,
            "publicClient": self.publicClient,
            "redirectUris": tuple(str(p) for p in self.redirectUris),
            "registrationAccessToken": self.registrationAccessToken,
            "rootUrl": self.rootUrl.raw,
            "secret": self.secret,
            "serviceAccountsEnabled": self.serviceAccountsEnabled,
            "standardFlowEnabled": self.standardFlowEnabled,
            "surrogateAuthRequired": self.surrogateAuthRequired,
            "webOrigins": self.webOrigins,
        }

    def can_redirect_to(self, url: Url) -> bool:
        for allowed_uri in self.redirectUris:
            if url.protocol != allowed_uri.protocol or url.host != allowed_uri.host:
                continue
            if allowed_uri.path == url.path:
                return True
            allowed_path = allowed_uri.path.as_posix()
            if allowed_path.endswith("*") and url.path.as_posix().startswith(allowed_path[:-1]):
                return True
        return False

    async def get_user_token(self, *, code: str, redirect_uri: Url, http_client_session: ClientSession) -> "UserToken":
        if not self.can_redirect_to(redirect_uri):
            raise ValueError(f"Can't redirect to {redirect_uri.raw}")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri.raw,
            "client_id": self.clientId,
            "client_secret": self.secret,
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
        if not self.can_redirect_to(redirect_uri):
            raise ValueError(f"Can't redirect to {redirect_uri}")

        scopes = scopes or set()

        return Url(
            protocol=Protocol.HTTPS,
            hostname="iam.ebrains.eu",
            path=PurePosixPath("/auth/realms/hbp/protocol/openid-connect/auth"),
            search={
                "response_type": "code",
                "login": "true",
                "client_id": self.clientId,
                "redirect_uri": redirect_uri.raw,
                "scope": Scope.iterable_to_json_value(scopes.union([Scope.OPENID])),
                "state": state if state is not None else str(uuid.uuid4()),
                # 'response_mode': ['fragment'],
                # 'nonce': ['b70e8d45-0b48-4688-9bd8-66bee41e5130'],
                # 'code_challenge': ['nPoae6il0nH3ZjurKJmS1Vx-T7wx9VaeR_XbJgeh2gQ'],
                # 'code_challenge_method': ['S256'],
            }
        )