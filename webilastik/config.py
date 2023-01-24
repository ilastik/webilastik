# pyright: strict

from pathlib import Path
from typing import ClassVar, Optional

from cryptography.fernet import Fernet
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_credentials import EbrainsUserCredentials

from webilastik.serialization.json_serialization import parse_typed_json_from_env_var
from webilastik.utility import Hostname, Minutes, Username
from webilastik.utility.url import Url
from webilastik.server.rpc.dto import WorkflowConfigDto, SessionAllocatorConfigDto

class SessionAllocatorConfig:
    _global_config: ClassVar["SessionAllocatorConfig | None | Exception"] = None

    CONFIG_ENV_VAR_NAME = "WEBILASTIK_SESSION_ALLOCATOR_CONFIG_JSON"

    def __init__(
        self,
        *,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,

        allow_local_compute_sessions: bool,
        b64_fernet_key: str,
        fernet: Fernet,
        external_url: Url
    ) -> None:
        super().__init__()
        self.allow_local_fs=allow_local_fs
        self.ebrains_oidc_client=ebrains_oidc_client
        self.allow_local_compute_sessions = allow_local_compute_sessions
        self.ebrains_oidc_client = ebrains_oidc_client
        self.b64_fernet_key = b64_fernet_key
        self.external_url = external_url
        self.fernet = fernet

    def to_dto(self) -> SessionAllocatorConfigDto:
        return SessionAllocatorConfigDto(
            allow_local_compute_sessions=self.allow_local_compute_sessions,
            allow_local_fs=self.allow_local_fs,
            b64_fernet_key=self.b64_fernet_key,
            ebrains_oidc_client=self.ebrains_oidc_client.to_dto(),
            external_url=self.external_url.to_dto(),
        )

    @classmethod
    def try_from_dto(cls, dto: SessionAllocatorConfigDto) -> "SessionAllocatorConfig | Exception":
        try:
            fernet = Fernet(key=dto.b64_fernet_key.encode('utf8'))
        except Exception as e:
            return e
        return SessionAllocatorConfig(
            allow_local_fs=dto.allow_local_fs,
            ebrains_oidc_client=OidcClient.from_dto(dto.ebrains_oidc_client),
            allow_local_compute_sessions=dto.allow_local_compute_sessions,
            external_url=Url.from_dto(dto.external_url),
            b64_fernet_key=dto.b64_fernet_key,
            fernet=fernet,
        )

    @classmethod
    def try_from_env(cls) -> "SessionAllocatorConfig | Exception":
        dto_result =  parse_typed_json_from_env_var(
            var_name=cls.CONFIG_ENV_VAR_NAME,
            json_value_parser=SessionAllocatorConfigDto.from_json_value,
        )
        if isinstance(dto_result, Exception):
            return dto_result
        return SessionAllocatorConfig.try_from_dto(dto_result)

    @classmethod
    def try_get_global(cls) -> "SessionAllocatorConfig | Exception":
        if cls._global_config is None:
            cls._global_config = cls.try_from_env()
        return cls._global_config

    def to_bash_export(self) -> str:
        import json
        value = json.dumps(self.to_dto(), indent=4)
        return f"""export {self.CONFIG_ENV_VAR_NAME}=$(cat << 'EOF'\n{value}\nEOF)"""

class WorkflowConfig:
    CONFIG_ENV_VAR_NAME = "WEBILASTIK_WORKFLOW_CONFIG_JSON"
    _global_config: ClassVar["WorkflowConfig | None | Exception"] = None

    def __init__(
        self,
        *,
        allow_local_fs: bool,
        ebrains_user_credentials: Optional[EbrainsUserCredentials],
        max_duration_minutes: Minutes,
        listen_socket: Path,
        session_url: Url,
        #tunnel parameters
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> None:
        super().__init__()
        self.allow_local_fs = allow_local_fs
        self.ebrains_user_credentials: Optional[EbrainsUserCredentials] = ebrains_user_credentials
        self.max_duration_minutes = max_duration_minutes
        self.listen_socket = listen_socket
        self.session_url = session_url

        self.session_allocator_host = session_allocator_host
        self.session_allocator_username = session_allocator_username
        self.session_allocator_socket_path = session_allocator_socket_path

    @classmethod
    def try_from_dto(cls, dto: WorkflowConfigDto) -> "WorkflowConfig | Exception":
        return WorkflowConfig(
            allow_local_fs=dto.allow_local_fs,
            ebrains_user_credentials=dto.ebrains_user_credentials and EbrainsUserCredentials.from_dto(dto.ebrains_user_credentials),
            listen_socket=Path(dto.listen_socket),
            session_url=Url.from_dto(dto.session_url),
            max_duration_minutes=Minutes(dto.max_duration_minutes),
            session_allocator_host=Hostname(dto.session_allocator_host),
            session_allocator_username=Username(dto.session_allocator_username),
            session_allocator_socket_path=Path(dto.session_allocator_socket_path),
        )

    def to_dto(self) -> WorkflowConfigDto:
        return WorkflowConfigDto(
            allow_local_fs=self.allow_local_fs,
            ebrains_user_credentials=self.ebrains_user_credentials and self.ebrains_user_credentials.to_dto(),
            listen_socket=self.listen_socket.as_posix(),
            session_url=self.session_url.to_dto(),
            max_duration_minutes=self.max_duration_minutes.to_int(),
            session_allocator_host=self.session_allocator_host,
            session_allocator_username=self.session_allocator_username,
            session_allocator_socket_path=self.session_allocator_socket_path.as_posix(),
        )

    def to_bash_export(self) -> str:
        import json
        value = json.dumps(self.to_dto(), indent=4)
        return f"""export {self.CONFIG_ENV_VAR_NAME}=$(cat << 'EOF'\n{value}\nEOF)"""

    @classmethod
    def try_from_env(cls) -> "WorkflowConfig | Exception":
        dto_result =  parse_typed_json_from_env_var(
            var_name=cls.CONFIG_ENV_VAR_NAME,
            json_value_parser=WorkflowConfigDto.from_json_value,
        )
        if isinstance(dto_result, Exception):
            return dto_result
        return WorkflowConfig.try_from_dto(dto_result)

    @classmethod
    def try_get_global(cls) -> "WorkflowConfig | Exception":
        if cls._global_config is None:
            cls._global_config = cls.try_from_env()
        return cls._global_config

