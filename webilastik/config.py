# pyright: strict

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, List, Literal, Optional, TypeVar
from typing_extensions import Self

from cryptography.fernet import Fernet
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_credentials import EbrainsUserCredentials
from webilastik.libebrains.user_token import UserToken

from webilastik.utility import get_env_var
from webilastik.utility.url import Url


T = TypeVar("T")
@dataclass
class Config(ABC, Generic[T]):
    value: T

    @classmethod
    @abstractmethod
    def try_parse(cls, value: str) -> "T | Exception":
        pass

    # @functools.lru_cache
    @classmethod
    def try_get(cls) -> "Self | None | Exception":
        value = get_env_var(
            var_name=cls.__name__,
            parser=cls.try_parse,
            default=None,
        )
        if isinstance(value, (type(None), Exception)):
            return value
        return cls(value)

    @classmethod
    def require(cls) -> "Self | Exception":
        value = cls.try_get()
        if value is None:
            return Exception(f"Env var {cls.__name__} was not set")
        return value


    @abstractmethod
    def to_bash_value(self) -> str:
        pass

    def to_bash_export(self) -> str:
        return f"export {self.__class__.__name__}={self.to_bash_value()}"


class BoolConfig(Config[bool]):
    @classmethod
    def try_parse(cls, value: str) -> "bool | Exception":
        if value.lower() in ("false", "0"):
            return False
        if value.lower() in ("true", "1"):
            return True
        return Exception(f"Bad value for {cls.__name__}: {value}")

    def to_bash_value(self) -> Literal["true", "false"]:
        return "true" if self.value else "false"

class IntConfig(Config[int]):
    @classmethod
    def try_parse(cls, value: str) -> "int | Exception":
        try:
            return int(value)
        except Exception as e:
            return e

    def to_bash_value(self) -> str:
        return str(self.value)

class PathConfig(Config[Path]):
    @classmethod
    def try_parse(cls, value: str) -> "Path | Exception":
        return Path(value)

    def to_bash_value(self) -> str:
        return str(self.value)

class StringConfig(Config[str]):
    @classmethod
    def try_parse(cls, value: str) -> "str | Exception":
        return value

    def to_bash_value(self) -> str:
        return self.value

class UrlConfig(Config[Url]):
    @classmethod
    def try_parse(cls, value: str) -> "Url | Exception":
        parsed = Url.parse(value)
        if parsed is None:
            return Exception(f"Bad url value for {cls.__name__}: {value}")
        return parsed

    def to_bash_value(self) -> str:
        return self.value.raw



class WEBILASTIK_ALLOW_LOCAL_FS(BoolConfig):
    pass
class WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS(BoolConfig):
    pass



class EBRAINS_OIDC_CLIENT_ID(StringConfig):
    pass
class EBRAINS_OIDC_CLIENT_SECRET(StringConfig):
    pass
class EbrainsOidcClientConfig:
    def __init__(
        self,
        *,
        client_id: EBRAINS_OIDC_CLIENT_ID,
        client_secret: EBRAINS_OIDC_CLIENT_SECRET,
    ):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = OidcClient(client_id=client_id.value, client_secret=client_secret.value)

    @classmethod
    def from_oidc_client(cls, client: OidcClient) -> Self:
        return EbrainsOidcClientConfig(
            client_id=EBRAINS_OIDC_CLIENT_ID(client.client_id),
            client_secret=EBRAINS_OIDC_CLIENT_SECRET(client.client_secret),
        )

    @classmethod
    def try_get(cls) -> "EbrainsOidcClientConfig | None |  Exception":
        client_id_result = EBRAINS_OIDC_CLIENT_ID.try_get()
        if isinstance(client_id_result, (Exception, type(None))):
            return client_id_result

        client_secret_result = EBRAINS_OIDC_CLIENT_SECRET.try_get()
        if isinstance(client_secret_result, Exception):
            return client_secret_result
        if isinstance(client_secret_result, type(None)):
            return Exception(f"{EBRAINS_OIDC_CLIENT_ID.__name__} is set but {EBRAINS_OIDC_CLIENT_SECRET.__name__} is not")

        return EbrainsOidcClientConfig(client_id=client_id_result, client_secret=client_secret_result)

    @classmethod
    def require(cls) -> "Self | Exception":
        client_id_result = EBRAINS_OIDC_CLIENT_ID.require()
        if isinstance(client_id_result, Exception):
            return client_id_result

        client_secret_result = EBRAINS_OIDC_CLIENT_SECRET.require()
        if isinstance(client_secret_result, Exception):
            return client_secret_result

        return EbrainsOidcClientConfig(client_id=client_id_result, client_secret=client_secret_result)

    def to_bash_exports(self) -> List[str]:
        return [
            self.client_id.to_bash_export(),
            self.client_secret.to_bash_export(),
        ]


class EBRAINS_USER_ACCESS_TOKEN(StringConfig):
    pass
class EBRAINS_USER_REFRESH_TOKEN(StringConfig):
    pass
class EbrainsUserCredentialsConfig:
    def __init__(
        self,
        *,
        user_access_token: EBRAINS_USER_ACCESS_TOKEN,
        user_refresh_token: Optional[EBRAINS_USER_REFRESH_TOKEN],
        oidc_client: Optional[EbrainsOidcClientConfig],
    ):
        super().__init__()
        self.user_access_token = user_access_token
        self.user_refresh_token = user_refresh_token
        self.oidc_client = oidc_client
        self.credentials = EbrainsUserCredentials(
            user_token=UserToken(
                access_token=self.user_access_token.value,
                refresh_token=self.user_refresh_token and self.user_access_token.value,
            ),
            oidc_client=self.oidc_client and self.oidc_client.client,
        )

    @classmethod
    def from_credentials(cls, credentials: EbrainsUserCredentials) -> "Self":
        return EbrainsUserCredentialsConfig(
            oidc_client=credentials.oidc_client and EbrainsOidcClientConfig.from_oidc_client(credentials.oidc_client),
            user_access_token=EBRAINS_USER_ACCESS_TOKEN(credentials.user_token.access_token),
            user_refresh_token=None if credentials.user_token.refresh_token is None else EBRAINS_USER_REFRESH_TOKEN(credentials.user_token.refresh_token),
        )

    def to_bash_exports(self) -> List[str]:
        out = [self.user_access_token.to_bash_export()]
        if self.user_refresh_token:
            out.append(self.user_access_token.to_bash_export())
        if self.oidc_client:
            out += self.oidc_client.to_bash_exports()
        return out

    @classmethod
    def try_get(cls) -> "Self | None | Exception":
        user_access_token_result = EBRAINS_USER_ACCESS_TOKEN.try_get()
        if isinstance(user_access_token_result, Exception):
            return user_access_token_result

        user_refresh_token_result = EBRAINS_USER_REFRESH_TOKEN.try_get()
        if isinstance(user_refresh_token_result, Exception):
            return user_refresh_token_result

        oidc_client_result = EbrainsOidcClientConfig.try_get()
        if isinstance(oidc_client_result, Exception):
            return oidc_client_result

        if user_access_token_result is None:
            return None

        return EbrainsUserCredentialsConfig(
            user_access_token=user_access_token_result,
            user_refresh_token=user_refresh_token_result,
            oidc_client=oidc_client_result,
        )

    @classmethod
    def require(cls) -> "Self | Exception":
        user_access_token_result = EBRAINS_USER_ACCESS_TOKEN.require()
        if isinstance(user_access_token_result, Exception):
            return user_access_token_result

        user_refresh_token_result = EBRAINS_USER_REFRESH_TOKEN.try_get()
        if isinstance(user_refresh_token_result, Exception):
            return user_refresh_token_result

        oidc_client_result = EbrainsOidcClientConfig.try_get()
        if isinstance(oidc_client_result, Exception):
            return oidc_client_result

        return EbrainsUserCredentialsConfig(
            user_access_token=user_access_token_result,
            user_refresh_token=user_refresh_token_result,
            oidc_client=oidc_client_result,
        )

class WEBILASTIK_B64_FERNET_KEY(StringConfig):
    pass
class WEBILASTIK_EXTERNAL_URL(UrlConfig):
    pass
@dataclass
class SessionAllocatorConfig:
    allow_local_fs: WEBILASTIK_ALLOW_LOCAL_FS
    allow_local_compute_sessions: WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS
    ebrains_oidc_client: EbrainsOidcClientConfig
    b64_fernet_key: WEBILASTIK_B64_FERNET_KEY
    fernet: Fernet
    external_url: WEBILASTIK_EXTERNAL_URL

    def to_bash_exports(self) -> List[str]:
        return [
            self.allow_local_fs.to_bash_export(),
            self.allow_local_compute_sessions.to_bash_export(),
            *self.ebrains_oidc_client.to_bash_exports(),
            self.b64_fernet_key.to_bash_export(),
            self.external_url.to_bash_export(),
        ]

    @classmethod
    def require(cls) -> "Self | Exception":
        allow_local_fs_config_result = WEBILASTIK_ALLOW_LOCAL_FS.require()
        if isinstance(allow_local_fs_config_result, Exception):
            return allow_local_fs_config_result

        allow_local_compute_sessions_config_result = WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS.require()
        if isinstance(allow_local_compute_sessions_config_result, Exception):
            return allow_local_compute_sessions_config_result

        ebrains_oidc_client_result = EbrainsOidcClientConfig.require()
        if isinstance(ebrains_oidc_client_result, Exception):
            return ebrains_oidc_client_result

        b64_fernet_key_result = WEBILASTIK_B64_FERNET_KEY.require()
        if isinstance(b64_fernet_key_result, Exception):
            return b64_fernet_key_result
        try:
            fernet = Fernet(key=b64_fernet_key_result.value)
        except Exception as e:
            return e

        external_url_result = WEBILASTIK_EXTERNAL_URL.require()
        if isinstance(external_url_result, Exception):
            return external_url_result

        return SessionAllocatorConfig(
            allow_local_fs=allow_local_fs_config_result,
            allow_local_compute_sessions=allow_local_compute_sessions_config_result,
            ebrains_oidc_client=ebrains_oidc_client_result,
            b64_fernet_key=b64_fernet_key_result,
            fernet=fernet,
            external_url=external_url_result,
        )

class WEBILASTIK_WORKFLOW_MAX_DURATION_MINUTES(IntConfig):
    pass
class WEBILASTIK_WORKFLOW_LISTEN_SOCKET(PathConfig):
    pass
class WEBILASTIK_WORKFLOW_SESSION_URL(UrlConfig):
    pass
class WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_HOST(StringConfig):
    pass
class WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_USERNAME(StringConfig):
    pass
class WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_SOCKET_PATH(PathConfig):
    pass
@dataclass
class WorkflowConfig:
    allow_local_fs: WEBILASTIK_ALLOW_LOCAL_FS
    ebrains_user_credentials: Optional[EbrainsUserCredentialsConfig]
    max_duration_minutes: WEBILASTIK_WORKFLOW_MAX_DURATION_MINUTES
    listen_socket: WEBILASTIK_WORKFLOW_LISTEN_SOCKET
    session_url: WEBILASTIK_WORKFLOW_SESSION_URL
    #tunnel parameter
    session_allocator_host: WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_HOST
    session_allocator_username: WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_USERNAME
    session_allocator_socket_path: WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_SOCKET_PATH

    @classmethod
    def require(cls) -> "WorkflowConfig | Exception":
        allow_local_fs_result = WEBILASTIK_ALLOW_LOCAL_FS.require()
        if isinstance(allow_local_fs_result, Exception):
            return allow_local_fs_result

        ebrains_user_credentials_result = EbrainsUserCredentialsConfig.try_get()
        if isinstance(ebrains_user_credentials_result, Exception):
            return ebrains_user_credentials_result

        max_duration_minutes_result = WEBILASTIK_WORKFLOW_MAX_DURATION_MINUTES.require()
        if isinstance(max_duration_minutes_result, Exception):
            return max_duration_minutes_result

        listen_socket_result = WEBILASTIK_WORKFLOW_LISTEN_SOCKET.require()
        if isinstance(listen_socket_result, Exception):
            return listen_socket_result

        session_url_result = WEBILASTIK_WORKFLOW_SESSION_URL.require()
        if isinstance(session_url_result, Exception):
            return session_url_result

        session_alocator_host_result = WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_HOST.require()
        if isinstance(session_alocator_host_result, Exception):
            return session_alocator_host_result

        session_allocator_username_result = WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_USERNAME.require()
        if isinstance(session_allocator_username_result, Exception):
            return session_allocator_username_result

        session_allocator_socket_path_result = WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_SOCKET_PATH.require()
        if isinstance(session_allocator_socket_path_result, Exception):
            return session_allocator_socket_path_result

        return WorkflowConfig(
            allow_local_fs=allow_local_fs_result,
            ebrains_user_credentials=ebrains_user_credentials_result,
            max_duration_minutes=max_duration_minutes_result,
            listen_socket=listen_socket_result,
            session_url=session_url_result,
            session_allocator_host=session_alocator_host_result,
            session_allocator_username=session_allocator_username_result,
            session_allocator_socket_path=session_allocator_socket_path_result,
        )

    def to_bash_exports(self) -> List[str]:
        return [
            self.allow_local_fs.to_bash_export(),
            *([] if not self.ebrains_user_credentials else self.ebrains_user_credentials.to_bash_exports()),
            self.max_duration_minutes.to_bash_export(),
            self.listen_socket.to_bash_export(),
            self.session_url.to_bash_export(),
            self.session_allocator_host.to_bash_export(),
            self.session_allocator_username.to_bash_export(),
            self.session_allocator_socket_path.to_bash_export(),
        ]

