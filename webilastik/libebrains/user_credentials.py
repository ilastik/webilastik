from typing import Optional

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

    def to_dto(self) -> EbrainsUserCredentialsDto:
        return EbrainsUserCredentialsDto(
            oidc_client=None if self.oidc_client is None else self.oidc_client.to_dto(),
            user_token=self.user_token.to_dto(),
        )

    @classmethod
    def from_dto(cls, dto: EbrainsUserCredentialsDto) -> "EbrainsUserCredentials":
        return EbrainsUserCredentials(
            oidc_client=dto.oidc_client if dto.oidc_client is None else OidcClient.from_dto(dto.oidc_client),
            user_token=UserToken.from_dto(dto.user_token),
        )