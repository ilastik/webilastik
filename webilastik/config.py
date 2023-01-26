# pyright: strict

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ClassVar, Generic, Literal, Optional, TypeVar
from typing_extensions import Self
import functools

from cryptography.fernet import Fernet
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_credentials import EbrainsUserCredentials
from webilastik.libebrains.user_token import UserToken

from webilastik.serialization.json_serialization import parse_typed_json_from_env_var
from webilastik.utility import Hostname, Minutes, Username, get_env_var
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import WorkflowConfigDto, SessionAllocatorConfigDto


T = TypeVar("T")
@dataclass
class Config(ABC, Generic[T]):
    value: T

    @classmethod
    @abstractmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        pass

    @abstractmethod
    def to_bash_value(self) -> str:
        pass

    def to_bash_export(self) -> str:
        return f"export {self.__class__.__name__}={self.to_bash_value()}"

class OptionalConfig(Config["T | None"]):
    # @functools.lru_cache
    @classmethod
    def try_get(cls) -> "Self | Exception":
        return get_env_var(
            var_name=cls.__name__,
            parser=cls.try_parse,
            default=cls(None),
        )

    @classmethod
    def require_value(cls) -> "T | Exception":
        instance = cls.try_get()
        if isinstance(instance, Exception):
            return instance
        if instance.value is None:
            return Exception(f"Environment variable {cls.__name__} was not set")
        return instance.value

class RequiredConfig(Config[T]):
    # @functools.lru_cache
    @classmethod
    def try_get(cls) -> "Self | Exception":
        return get_env_var(
            var_name=cls.__name__,
            parser=cls.try_parse,
        )

class BoolConfig(RequiredConfig[bool]):
    @classmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        if value.lower() in ("false", "0"):
            return cls(False)
        if value.lower() in ("true", "1"):
            return cls(True)
        return Exception(f"Bad value for {cls.__name__}: {value}")

    def to_bash_value(self) -> Literal["true", "false"]:
        return "true" if self.value else "false"

class IntConfig(RequiredConfig[int]):
    @classmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        try:
            return cls(int(value))
        except Exception as e:
            return e

    def to_bash_value(self) -> str:
        return str(self.value)

class PathConfig(RequiredConfig[Path]):
    @classmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        return cls(Path(value))

    def to_bash_value(self) -> str:
        return str(self.value)

class StringConfig(RequiredConfig[str]):
    @classmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        return cls(value)

    def to_bash_value(self) -> str:
        return self.value

class UrlConfig(RequiredConfig[Url]):
    @classmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        parsed = Url.parse(value)
        if parsed is None:
            return Exception(f"Bad url value for {cls.__name__}: {value}")
        return cls(parsed)

    def to_bash_value(self) -> str:
        return self.value.raw

class OptionalStringConfig(OptionalConfig["str"]):
    @classmethod
    def try_parse(cls, value: str) -> "Self | Exception":
        return cls(value) if len(value) > 0 else cls(None)

    def to_bash_value(self) -> str:
        return "" if self.value is None else self.value



class WEBILASTIK_ALLOW_LOCAL_FS(BoolConfig):
    pass
class WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS(BoolConfig):
    pass



class EBRAINS_OIDC_CLIENT_ID(OptionalStringConfig):
    pass
class EBRAINS_OIDC_CLIENT_SECRET(OptionalStringConfig):
    pass
@dataclass
class EbrainsOidcClientConfig:
    value: "OidcClient | None"

    @classmethod
    def try_get(cls) -> "Self | Exception":
        client_id_config_result = EBRAINS_OIDC_CLIENT_ID.try_get()
        if isinstance(client_id_config_result, Exception):
            return client_id_config_result
        if client_id_config_result.value is None:
            return cls(None)

        client_secret_result = EBRAINS_OIDC_CLIENT_SECRET.require_value()
        if isinstance(client_secret_result, Exception):
            return client_secret_result

        return cls(value=OidcClient(client_id=client_id_config_result.value, client_secret=client_secret_result))

    @classmethod
    def require_value(cls) -> "OidcClient | Exception":
        client_id_result = EBRAINS_OIDC_CLIENT_ID.require_value()
        if isinstance(client_id_result, Exception):
            return client_id_result

        client_secret_result = EBRAINS_OIDC_CLIENT_SECRET.require_value()
        if isinstance(client_secret_result, Exception):
            return client_secret_result

        return OidcClient(client_id=client_id_result, client_secret=client_secret_result)


class EBRAINS_USER_ACCESS_TOKEN(OptionalStringConfig):
    pass
class EBRAINS_USER_REFRESH_TOKEN(OptionalStringConfig):
    pass
@dataclass
class EbrainsUserCredentialsConfig:
    value: "EbrainsUserCredentials | None"

    @classmethod
    def try_get(cls) -> "Self | Exception":
        user_access_token_result = EBRAINS_USER_ACCESS_TOKEN.try_get()
        if isinstance(user_access_token_result, Exception):
            return user_access_token_result
        if user_access_token_result.value is None:
            return cls(value=None)

        user_refresh_token_config_result = EBRAINS_USER_REFRESH_TOKEN.try_get()
        if isinstance(user_refresh_token_config_result, Exception):
            return user_refresh_token_config_result

        oid_client_config_result = EbrainsOidcClientConfig.try_get()
        if isinstance(oid_client_config_result, Exception):
            return oid_client_config_result

        return cls(EbrainsUserCredentials(
            user_token=UserToken(
                access_token=user_access_token_result.value,
                refresh_token=user_refresh_token_config_result.value,
            ),
            oidc_client=oid_client_config_result.value,
        ))

    @classmethod
    def require_value(cls) -> "EbrainsUserCredentials | Exception":
        user_access_token_result = EBRAINS_USER_ACCESS_TOKEN.require_value()
        if isinstance(user_access_token_result, Exception):
            return user_access_token_result

        user_refresh_token_config_result = EBRAINS_USER_REFRESH_TOKEN.try_get()
        if isinstance(user_refresh_token_config_result, Exception):
            return user_refresh_token_config_result

        oid_client_config_result = EbrainsOidcClientConfig.try_get()
        if isinstance(oid_client_config_result, Exception):
            return oid_client_config_result

        return EbrainsUserCredentials(
            user_token=UserToken(
                access_token=user_access_token_result,
                refresh_token=user_refresh_token_config_result.value,
            ),
            oidc_client=oid_client_config_result.value,
        )


class WEBILASTIK_B64_FERNET_KEY(StringConfig):
    pass
class WEBILASTIK_EXTERNAL_URL(UrlConfig):
    pass
@dataclass
class SessionAllocatorConfig:
    allow_local_fs: WEBILASTIK_ALLOW_LOCAL_FS
    allow_local_compute_sessions: WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS
    ebrains_oidc_client: OidcClient
    b64_fernet_key: str
    fernet: Fernet
    external_url: Url

    @classmethod
    def try_get(cls) -> "Self | Exception":
        allow_local_fs_config_result = WEBILASTIK_ALLOW_LOCAL_FS.try_get()
        if isinstance(allow_local_fs_config_result, Exception):
            return allow_local_fs_config_result

        allow_local_compute_sessions_config_result = WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS.try_get()
        if isinstance(allow_local_compute_sessions_config_result, Exception):
            return allow_local_compute_sessions_config_result

        ebrains_oidc_client_result = EbrainsOidcClientConfig.require_value()
        if isinstance(ebrains_oidc_client_result, Exception):
            return ebrains_oidc_client_result

        b64_fernet_key_result = WEBILASTIK_B64_FERNET_KEY.try_get()
        if isinstance(b64_fernet_key_result, Exception):
            return b64_fernet_key_result
        try:
            fernet = Fernet(key=b64_fernet_key_result.value)
        except Exception as e:
            return e

        external_url_result = WEBILASTIK_EXTERNAL_URL.try_get()
        if isinstance(external_url_result, Exception):
            return external_url_result

        return SessionAllocatorConfig(
            allow_local_fs=allow_local_fs_config_result.value,
            allow_local_compute_sessions=allow_local_compute_sessions_config_result.value,
            ebrains_oidc_client=ebrains_oidc_client_result,
            b64_fernet_key=b64_fernet_key_result.value,
            fernet=fernet,
            external_url=external_url_result.value
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
    ebrains_user_credentials: EbrainsUserCredentialsConfig
    max_duration_minutes: WEBILASTIK_WORKFLOW_MAX_DURATION_MINUTES
    listen_socket: WEBILASTIK_WORKFLOW_LISTEN_SOCKET
    session_url: WEBILASTIK_WORKFLOW_SESSION_URL
    #tunnel parameter
    session_allocator_host: WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_HOST
    session_allocator_username: WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_USERNAME
    session_allocator_socket_path: WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_SOCKET_PATH

    @classmethod
    def try_get(cls) -> "WorkflowConfig | Exception":
        allow_local_fs_result = WEBILASTIK_ALLOW_LOCAL_FS.try_get()
        if isinstance(allow_local_fs_result, Exception):
            return allow_local_fs_result

        ebrains_user_credentials_result = EbrainsUserCredentialsConfig.try_get()
        if isinstance(ebrains_user_credentials_result, Exception):
            return ebrains_user_credentials_result

        max_duration_minutes_result = WEBILASTIK_WORKFLOW_MAX_DURATION_MINUTES.try_get()
        if isinstance(max_duration_minutes_result, Exception):
            return max_duration_minutes_result

        listen_socket_result = WEBILASTIK_WORKFLOW_LISTEN_SOCKET.try_get()
        if isinstance(listen_socket_result, Exception):
            return listen_socket_result

        session_url_result = WEBILASTIK_WORKFLOW_SESSION_URL.try_get()
        if isinstance(session_url_result, Exception):
            return session_url_result

        session_alocator_host_result = WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_HOST.try_get()
        if isinstance(session_alocator_host_result, Exception):
            return session_alocator_host_result

        session_allocator_username_result = WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_USERNAME.try_get()
        if isinstance(session_allocator_username_result, Exception):
            return session_allocator_username_result

        session_allocator_socket_path_result = WEBILASTIK_WORKFLOW_SESSION_ALLOCATOR_SOCKET_PATH.try_get()
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

