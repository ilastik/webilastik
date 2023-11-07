# pyright: strict

import os
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Optional, cast

from cryptography.fernet import Fernet
from webilastik.libebrains.oidc_client import OidcClient

from webilastik.libebrains.user_token import AccessToken, HbpIamPublicKey
from webilastik.serialization.json_serialization import parse_json
from webilastik.server.rpc.dto import SessionAllocatorServerConfigDto, WorkflowConfigDto
from webilastik.utility import Hostname, Minutes, Username
from webilastik.utility.url import Url

class ConfigurationException(Exception):
    pass

WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG = "WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG"

@dataclass
class SessionAllocatorServerConfig:
    _global_config: ClassVar["SessionAllocatorServerConfig | None"] = None

    class _PrivateMarker:
        pass

    ebrains_oidc_client: OidcClient
    allow_local_compute_sessions: bool
    fernet: Fernet
    b64_fernet_key: str
    external_url: Url
    marker: _PrivateMarker

    @classmethod
    def from_dto(cls, dto: SessionAllocatorServerConfigDto) -> "SessionAllocatorServerConfig | ConfigurationException":
        try:
            fernet=Fernet(key=dto.b64_fernet_key.encode('utf8'))
        except Exception:
            raise ConfigurationException(f"Bad fernet key")
        return SessionAllocatorServerConfig(
            ebrains_oidc_client=OidcClient.from_dto(dto.ebrains_oidc_client),
            allow_local_compute_sessions=dto.allow_local_compute_sessions,
            external_url=Url.from_dto(dto.external_url),
            fernet=fernet,
            b64_fernet_key=dto.b64_fernet_key,
            marker=cls._PrivateMarker()
        )

    def updated(self, allow_local_compute_sessions: Optional[bool] = None) -> "SessionAllocatorServerConfig":
        if allow_local_compute_sessions is None:
            allow_local_compute_sessions = self.allow_local_compute_sessions
        return SessionAllocatorServerConfig(
            ebrains_oidc_client=self.ebrains_oidc_client,
            allow_local_compute_sessions=allow_local_compute_sessions,
            fernet=self.fernet,
            b64_fernet_key=self.b64_fernet_key,
            external_url=self.external_url,
            marker=self._PrivateMarker(),
        )

    def to_dto(self) -> SessionAllocatorServerConfigDto:
        return SessionAllocatorServerConfigDto(
            ebrains_oidc_client=self.ebrains_oidc_client.to_dto(),
            allow_local_compute_sessions=self.allow_local_compute_sessions,
            b64_fernet_key=self.b64_fernet_key,
            external_url=self.external_url.to_dto(),
        )

    @classmethod
    def get(cls) -> "SessionAllocatorServerConfig":
        if cls._global_config is None:
            config = cls.from_env()
            if isinstance(config, Exception):
                raise config
            cls._global_config = config
        return cls._global_config

    @classmethod
    def from_env(cls) -> "SessionAllocatorServerConfig | ConfigurationException":
        config_raw = os.environ.get(WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG)
        if config_raw is None:
            return ConfigurationException(f"Could not find configuration json in env var {WEBILASTIK_WORKFLOW_CONFIG}")
        config_json_result = parse_json(config_raw)
        if isinstance(config_json_result, Exception):
            return ConfigurationException(config_json_result)
        config_dto_result = SessionAllocatorServerConfigDto.from_json_value(config_json_result)
        if isinstance(config_dto_result, Exception):
            return ConfigurationException(config_dto_result)
        return SessionAllocatorServerConfig.from_dto(config_dto_result)

    def to_systemd_environment_conf(self) -> str:
        json_str = json.dumps(self.to_dto().to_json_value())
        return f"Environment={WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG}='{json_str}'"

WEBILASTIK_WORKFLOW_CONFIG = "WEBILASTIK_WORKFLOW_CONFIG"

@dataclass
class WorkflowConfig:
    _global_config: ClassVar["WorkflowConfig | None"] = None

    allow_local_fs: bool
    scratch_dir: PurePosixPath
    ebrains_user_token: AccessToken
    max_duration_minutes: Minutes
    listen_socket: Path
    session_url: Url
    session_allocator_host: Hostname
    session_allocator_username: Username
    session_allocator_socket_path: Path

    def to_dto(self) -> WorkflowConfigDto:
        return WorkflowConfigDto(
            allow_local_fs=self.allow_local_fs,
            scratch_dir=str(self.scratch_dir),
            ebrains_user_token=self.ebrains_user_token.to_dto(),
            max_duration_minutes=self.max_duration_minutes.to_int(),
            listen_socket=str(self.listen_socket),
            session_url=self.session_url.to_dto(),
            session_allocator_host=self.session_allocator_host,
            session_allocator_username=self.session_allocator_username,
            session_allocator_socket_path=str(self.session_allocator_socket_path),
        )

    @classmethod
    def from_dto(cls, dto: WorkflowConfigDto) -> "WorkflowConfig | ConfigurationException":
        checking_key_result = HbpIamPublicKey.get_sync()
        if isinstance(checking_key_result, Exception):
            return ConfigurationException(f"Could not validate user token: {checking_key_result}")
        ebrains_user_token_result = AccessToken.from_dto(dto.ebrains_user_token, checking_key=checking_key_result)
        if isinstance(ebrains_user_token_result, Exception):
            return ConfigurationException(f"Could not get a user token: {ebrains_user_token_result}")
        return WorkflowConfig(
            allow_local_fs=dto.allow_local_fs,
            scratch_dir=PurePosixPath(dto.scratch_dir),
            ebrains_user_token=ebrains_user_token_result,
            max_duration_minutes=Minutes(dto.max_duration_minutes),
            listen_socket=Path(dto.listen_socket),
            session_url=Url.from_dto(dto.session_url),
            session_allocator_host=Hostname(dto.session_allocator_host),
            session_allocator_username=Username(dto.session_allocator_username),
            session_allocator_socket_path=Path(dto.session_allocator_socket_path),
        )

    @classmethod
    def get(cls) -> "WorkflowConfig":
        if cls._global_config is None:
            config = cls.from_env()
            if isinstance(config, Exception):
                raise config
            cls._global_config = config
        return cls._global_config

    @classmethod
    def from_env(cls) -> "WorkflowConfig | ConfigurationException":
        config_raw = os.environ.get(WEBILASTIK_WORKFLOW_CONFIG)
        if config_raw is None:
            return ConfigurationException(f"Could not find configuration json in env var {WEBILASTIK_WORKFLOW_CONFIG}")
        config_json_result = parse_json(config_raw)
        if isinstance(config_json_result, Exception):
            return ConfigurationException(config_json_result)
        config_dto_result = WorkflowConfigDto.from_json_value(config_json_result)
        if isinstance(config_dto_result, Exception):
            return ConfigurationException(config_dto_result)
        return WorkflowConfig.from_dto(config_dto_result)

    def to_env_export(self) -> str:
        json_str = json.dumps(self.to_dto().to_json_value())
        escaped_json_str = json_str.replace("'", r"\'")
        return f"export {WEBILASTIK_WORKFLOW_CONFIG}='{escaped_json_str}'"

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("simple_example")
    _ = parser.add_argument("--b64-fernet-key", help="The fernet key to encrypt stuff on the HPCs", required=True)
    _ = parser.add_argument("--oidc-client-secret", help="The oidc client key", required=True)
    _ = parser.add_argument(
        "--allow-local-compute-sessions",
        help="Allow compute sessions to be spawned as local processes",
        action='store_true',
        required=True,
    )
    args = parser.parse_args()

    b64_fernet_key = cast(str, args.b64_fernet_key)
    assert isinstance(b64_fernet_key, str)

    fernet = Fernet(key=b64_fernet_key.encode('utf8'))

    oidc_client_secret = cast(str, args.oidc_client_secret)
    assert isinstance(oidc_client_secret, str)

    allow_local_compute_sessions = cast(bool, args.allow_local_compute_sessions)
    assert isinstance(allow_local_compute_sessions, bool)

    config_str = json.dumps(SessionAllocatorServerConfig(
        ebrains_oidc_client=OidcClient(client_id="webilastik", client_secret=oidc_client_secret),
        allow_local_compute_sessions=allow_local_compute_sessions,
        b64_fernet_key=b64_fernet_key,
        fernet=fernet,
        external_url=Url.parse_or_raise('https://app.ilastik.org/'),
        marker=SessionAllocatorServerConfig._PrivateMarker() #pyright: ignore [reportPrivateUsage]
    ).to_dto().to_json_value())#.replace("{", "\\{").replace("}", "\\}").replace('"', '\\"')

    print(f"export {WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG}='{config_str}'")