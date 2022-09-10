import threading
from webilastik.libebrains.oidc_client import OidcClient

from webilastik.libebrains.user_token import UserToken

_oidc_client = OidcClient.from_environment()
_global_login_token: UserToken = UserToken.from_environment_or_raise()

def get_global_login_token() -> "UserToken":
    return _global_login_token

def refresh_global_login_token() -> "UserToken | Exception":
    global _global_login_token
    fresh_token_result = _global_login_token.refreshed(oidc_client=_oidc_client)
    if isinstance(fresh_token_result, UserToken):
        _global_login_token = fresh_token_result
    return fresh_token_result