from typing import Optional
from webilastik.serialization.json_serialization import parse_typed_json_from_env_var

from webilastik.server.rpc.dto import EbrainsUserCredentialsDto
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_token import UserToken


class EbrainsUserCredentials:
    def __init__(self, user_token: UserToken, oidc_client: Optional[OidcClient]) -> None:
        super().__init__()
        self.user_token = user_token
        self.oidc_client = oidc_client

    def refresh(self) -> "None | Exception":
        if self.oidc_client is None:
            return Exception(f"Can't refresh Ebrains user token")
        refreshed_token_result = self.user_token.refreshed(oidc_client=self.oidc_client)
        if isinstance(refreshed_token_result, Exception):
            return refreshed_token_result
        self.user_token = refreshed_token_result