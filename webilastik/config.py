# pyright: strict

import os

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Optional, Sequence

from cryptography.fernet import Fernet
from webilastik.libebrains.oidc_client import OidcClient

from webilastik.libebrains.user_token import UserToken
from webilastik.utility import Hostname, Minutes, Username
from webilastik.utility.url import Url


def read_str_env_var(name: str, *, help_text: str, allow_empty: bool = False) -> str:
    value = os.environ.get(name)
    if value is None:
        raise Exception(f"Configuration variable '{name}' is unset. {help_text}")
    if len(value) == 0 and not allow_empty:
        raise Exception(f"Configuration variable '{name}' is empty.")
    return value

def read_bool_env_var(name: str, *, help_text: str) -> bool:
    valid_true_values = ["true", "1"]
    valid_false_values = ["false", "0"]

    value = read_str_env_var(name, help_text=help_text)
    if value in valid_true_values:
        return True
    if value in valid_false_values:
        return False
    raise Exception(f"Configuration variable {name} has a bad value: {value}. Expected one of {[*valid_true_values, *valid_false_values]}")

def read_int_env_var(name: str, *, help_text: str) -> int:
    raw_value = read_str_env_var(name, help_text=help_text)
    try:
        return int(raw_value)
    except ValueError:
        raise Exception(f"Could not parse env var {name} as int: {raw_value}")

def read_url_env_var(name: str, *, help_text: str) -> Url:
    url = Url.parse(read_str_env_var(name, help_text=help_text))
    if url is None:
        raise Exception(f"Bad url in env var {name}")
    return url

@dataclass
class EnvVar:
    name: str
    value: str

    def to_bash_export(self) -> str:
        return f'export {self.name}="{self.value}"'

    def to_systemd_environment_conf(self) -> str:
        return f'Environment={self.name}={self.value}'

WEBILASTIK_ALLOW_LOCAL_FS="WEBILASTIK_ALLOW_LOCAL_FS"
WEBILASTIK_SCRATCH_DIR="WEBILASTIK_SCRATCH_DIR"
WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS="WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS"
WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY="WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY"
WEBILASTIK_EXTERNAL_URL="WEBILASTIK_EXTERNAL_URL"
EBRAINS_CLIENT_ID="EBRAINS_CLIENT_ID"
EBRAINS_CLIENT_SECRET="EBRAINS_CLIENT_SECRET"
EBRAINS_USER_ACCESS_TOKEN="EBRAINS_USER_ACCESS_TOKEN"
EBRAINS_USER_REFRESH_TOKEN="EBRAINS_USER_REFRESH_TOKEN"
WEBILASTIK_JOB_MAX_DURATION_MINUTES="WEBILASTIK_JOB_MAX_DURATION_MINUTES"
WEBILASTIK_JOB_LISTEN_SOCKET="WEBILASTIK_JOB_LISTEN_SOCKET"
WEBILASTIK_JOB_SESSION_URL="WEBILASTIK_JOB_SESSION_URL"
WEBILASTIK_SESSION_ALLOCATOR_HOST="WEBILASTIK_SESSION_ALLOCATOR_HOST"
WEBILASTIK_SESSION_ALLOCATOR_USERNAME="WEBILASTIK_SESSION_ALLOCATOR_USERNAME"
WEBILASTIK_SESSION_ALLOCATOR_SOCKET_PATH="WEBILASTIK_SESSION_ALLOCATOR_SOCKET_PATH"

class WebilastikConfig:
    def __init__(
        self,
        *,
        allow_local_fs: bool,
        scratch_dir: PurePosixPath,
        ebrains_oidc_client: OidcClient,
    ) -> None:
        super().__init__()
        self.allow_local_fs = allow_local_fs
        self.scratch_dir = scratch_dir
        self.ebrains_oidc_client = ebrains_oidc_client

    @classmethod
    def from_env(
        cls,
        *,
        allow_local_fs: Optional[bool] = None,
        scratch_dir: Optional[PurePosixPath] = None,
        ebrains_oidc_client: Optional[OidcClient] = None,
    ) -> "WebilastikConfig":
        return WebilastikConfig(
            allow_local_fs=allow_local_fs if allow_local_fs is not None else read_bool_env_var(
                name= WEBILASTIK_ALLOW_LOCAL_FS,
                help_text="Allow ilastik to read and write to the local filesystem",
            ),
            scratch_dir=scratch_dir if scratch_dir is not None else PurePosixPath(read_str_env_var(
                name= WEBILASTIK_SCRATCH_DIR,
                help_text="base path where temporary files can be created",
            )),
            ebrains_oidc_client=ebrains_oidc_client if ebrains_oidc_client is not None else OidcClient(
                client_id=read_str_env_var(
                    EBRAINS_CLIENT_ID,
                    help_text="The client ID that is registered in Ebrains' keycloak. Should be a simple string like 'webilastik'",
                ),
                client_secret=read_str_env_var(
                    EBRAINS_CLIENT_SECRET,
                    help_text="The client secret for the Oidc client",
                ),
            ),
        )

    def to_env_vars(self) -> Sequence[EnvVar]:
        return [
            EnvVar(name=WEBILASTIK_ALLOW_LOCAL_FS, value=str(self.allow_local_fs).lower()),
            EnvVar(name=EBRAINS_CLIENT_ID, value=self.ebrains_oidc_client.client_id),
            EnvVar(name=EBRAINS_CLIENT_SECRET, value=self.ebrains_oidc_client.client_secret),
        ]

    def to_bash_exports(self) -> str:
        return "\n".join(ev.to_bash_export() for ev in self.to_env_vars())

    def to_systemd_environment_confs(self) -> str:
        return "\n".join(ev.to_systemd_environment_conf() for ev in self.to_env_vars())


class SessionAllocatorConfig(WebilastikConfig):
    _global_config: ClassVar["SessionAllocatorConfig | None"] = None

    def __init__(
        self,
        *,
        allow_local_fs: bool,
        scratch_dir: PurePosixPath,
        ebrains_oidc_client: OidcClient,

        allow_local_compute_sessions: bool,
        session_allocator_b64_fernet_key: str,
        external_url: Url
    ) -> None:
        super().__init__(
            allow_local_fs=allow_local_fs,
            scratch_dir=scratch_dir,
            ebrains_oidc_client=ebrains_oidc_client,
        )
        self.allow_local_compute_sessions = allow_local_compute_sessions
        self.ebrains_oidc_client = ebrains_oidc_client
        self.session_allocator_b64_fernet_key = session_allocator_b64_fernet_key
        self.external_url = external_url

        try:
            self.fernet=Fernet(key=session_allocator_b64_fernet_key.encode('utf8'))
        except Exception:
            raise Exception(f"Bad fernet key")
        self.fernet = Fernet(key=session_allocator_b64_fernet_key.encode("utf8"))

    @classmethod
    def get(cls) -> "SessionAllocatorConfig":
        if cls._global_config is None:
            cls._global_config = cls.from_env()
        return cls._global_config

    @classmethod
    def from_env(
        cls,
        *,
        allow_local_fs: Optional[bool] = None,
        scratch_dir: Optional[PurePosixPath] = None,
        ebrains_oidc_client: Optional[OidcClient] = None,

        allow_local_compute_sessions: Optional[bool] = None,
        session_allocator_b64_fernet_key: Optional[str] = None,
        external_url: Optional[Url] = None
    ) -> "SessionAllocatorConfig":
        base_config = WebilastikConfig.from_env(allow_local_fs=allow_local_fs, scratch_dir=scratch_dir, ebrains_oidc_client=ebrains_oidc_client)

        return SessionAllocatorConfig(
            allow_local_fs=base_config.allow_local_fs,
            scratch_dir=base_config.scratch_dir,
            ebrains_oidc_client=base_config.ebrains_oidc_client,
            allow_local_compute_sessions=allow_local_compute_sessions if allow_local_compute_sessions is not None else read_bool_env_var(
                name=WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS,
                help_text="Allow compute sessions to be allocated in the machine running the webilastik server",
            ),
            external_url=external_url if external_url is not None else read_url_env_var(
                name=WEBILASTIK_EXTERNAL_URL,
                help_text="Url from which sessions can be accessed (where the session sockets live)",
            ),
            session_allocator_b64_fernet_key = session_allocator_b64_fernet_key if session_allocator_b64_fernet_key is not None else read_str_env_var(
                name=WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY,
                help_text="A Fernet key used to encrypt data that is publicly visible in HPCs, like job names",
            ),
        )

    def to_env_vars(self) -> Sequence[EnvVar]:
        return [
            *super().to_env_vars(),
            EnvVar(name=WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS, value=str(self.allow_local_compute_sessions).lower()),
            EnvVar(name=WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY, value=self.session_allocator_b64_fernet_key),
            EnvVar(name=WEBILASTIK_EXTERNAL_URL, value=self.external_url.raw),
        ]

class WorkflowConfig(WebilastikConfig):
    _global_config: ClassVar["WorkflowConfig | None"] = None

    def __init__(
        self,
        *,
        allow_local_fs: bool,
        scratch_dir: PurePosixPath,
        ebrains_oidc_client: OidcClient,

        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        listen_socket: Path,
        session_url: Url,
        #tunnel parameters
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> None:
        super().__init__(
            allow_local_fs=allow_local_fs,
            scratch_dir=scratch_dir,
            ebrains_oidc_client=ebrains_oidc_client,
        )
        self.ebrains_user_token: UserToken = ebrains_user_token
        self.max_duration_minutes = max_duration_minutes
        self.listen_socket = listen_socket
        self.session_url = session_url

        self.session_allocator_host = session_allocator_host
        self.session_allocator_username = session_allocator_username
        self.session_allocator_socket_path = session_allocator_socket_path

    @classmethod
    def get(cls) -> "WorkflowConfig":
        if cls._global_config is None:
            cls._global_config = cls.from_env()
        return cls._global_config

    @classmethod
    def from_env(
        cls,
        *,
        allow_local_fs: Optional[bool] = None,
        scratch_dir: Optional[PurePosixPath] = None,
        ebrains_oidc_client: Optional[OidcClient] = None,

        ebrains_user_token: Optional[UserToken] = None,
        max_duration_minutes: Optional[Minutes] = None,
        listen_socket: Optional[Path] = None,
        session_url: Optional[Url] = None,
        # tunnel parameters
        session_allocator_host: Optional[Hostname] = None,
        session_allocator_username: Optional[Username] = None,
        session_allocator_socket_path: Optional[Path] = None
    ) -> "WorkflowConfig":
        base_config = WebilastikConfig.from_env(allow_local_fs=allow_local_fs, scratch_dir=scratch_dir, ebrains_oidc_client=ebrains_oidc_client)
        if ebrains_user_token is None:
            raw_user_access_token = read_str_env_var(
                EBRAINS_USER_ACCESS_TOKEN,
                help_text="The raw string for an ebrains user access token, retrieved from ebrains iam",
            )
            raw_user_refresh_token = read_str_env_var(
                EBRAINS_USER_REFRESH_TOKEN,
                help_text="The raw string for an ebrains user refresh token, retrieved from ebrains iam",
            )
            ebrains_user_token = UserToken(access_token=raw_user_access_token, refresh_token=raw_user_refresh_token)
        return WorkflowConfig(
            allow_local_fs=base_config.allow_local_fs,
            scratch_dir=base_config.scratch_dir,
            ebrains_oidc_client=base_config.ebrains_oidc_client,
            ebrains_user_token=ebrains_user_token,
            max_duration_minutes=max_duration_minutes if max_duration_minutes is not None else Minutes(float(read_int_env_var(
                WEBILASTIK_JOB_MAX_DURATION_MINUTES,
                help_text="Maximum job duration in minutes"
            ))),
            listen_socket=listen_socket if listen_socket is not None else Path(read_str_env_var(
                WEBILASTIK_JOB_LISTEN_SOCKET,
                help_text="Path to the socket on which the job server will listen for frontend requests"
            )),
            session_url=session_url if session_url is not None else Url.parse_or_raise(read_str_env_var(
                WEBILASTIK_JOB_SESSION_URL,
                help_text="The session URL as seen from the frontend"
            )),

            # tunnel parameters
            session_allocator_host=session_allocator_host if session_allocator_host is not None else Hostname(read_str_env_var(
                WEBILASTIK_SESSION_ALLOCATOR_HOST,
                help_text="The hostname of the session allocator, to which an SSH conection can be made"
            )),
            session_allocator_username=session_allocator_username if session_allocator_username is not None else Username(read_str_env_var(
                WEBILASTIK_SESSION_ALLOCATOR_USERNAME,
                help_text="A existing username on the session allocator, with which an SSH conection can be made"
            )),
            session_allocator_socket_path=session_allocator_socket_path if session_allocator_socket_path is not None else Path(read_str_env_var(
                WEBILASTIK_SESSION_ALLOCATOR_SOCKET_PATH,
                help_text="The path where a socket connecting back to the job is to be created"
            )),
        )


    def to_env_vars(self) -> Sequence[EnvVar]:
        return [
            *super().to_env_vars(),
            EnvVar(name=EBRAINS_USER_ACCESS_TOKEN, value=self.ebrains_user_token.access_token),
            EnvVar(name=EBRAINS_USER_REFRESH_TOKEN, value=self.ebrains_user_token.refresh_token),
            EnvVar(name=WEBILASTIK_JOB_MAX_DURATION_MINUTES, value=str(self.max_duration_minutes.to_int())),
            EnvVar(name=WEBILASTIK_JOB_LISTEN_SOCKET, value=str(self.listen_socket)),
            EnvVar(name=WEBILASTIK_JOB_SESSION_URL, value=self.session_url.raw),
            EnvVar(name=WEBILASTIK_SESSION_ALLOCATOR_HOST, value=self.session_allocator_host),
            EnvVar(name=WEBILASTIK_SESSION_ALLOCATOR_USERNAME, value=self.session_allocator_username),
            EnvVar(name=WEBILASTIK_SESSION_ALLOCATOR_SOCKET_PATH, value=str(self.session_allocator_socket_path)),
        ]
