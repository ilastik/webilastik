import threading
from webilastik.config import WorkflowConfig
from webilastik.libebrains.oidc_client import OidcClient

from webilastik.libebrains.user_token import AccessToken

_oidc_client = WorkflowConfig.get().ebrains_oidc_client
_global_login_token: AccessToken = WorkflowConfig.get().ebrains_user_token

def get_global_login_token() -> "AccessToken":
    return _global_login_token

def refresh_global_login_token() -> "AccessToken | Exception":
    global _global_login_token
    fresh_token_result = _global_login_token.refreshed(oidc_client=_oidc_client)
    if isinstance(fresh_token_result, AccessToken):
        _global_login_token = fresh_token_result
    return fresh_token_result