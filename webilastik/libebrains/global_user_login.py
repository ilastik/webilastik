# pyright: strict

import threading

import requests
from webilastik.config import WorkflowConfig

from webilastik.libebrains.user_token import AccessToken, HbpIamPublicKey
from webilastik.serialization.json_serialization import parse_json
from webilastik.server.rpc.dto import EbrainsAccessTokenDto
from webilastik.utility.request import request
from webilastik.utility.url import Url

class GlobalLogin:
    _mutex = threading.Lock()
    _token: "AccessToken" = WorkflowConfig.get().ebrains_user_token

    @classmethod
    def get_token(cls) -> "AccessToken":
        with cls._mutex:
            return cls._token

    @classmethod
    def refresh_token(cls, *, stale_token: AccessToken) -> "AccessToken | Exception":
        with cls._mutex:
            if stale_token.payload.exp < cls._token.payload.exp and not cls._token.payload.expired:
                return cls._token

            request_result = request(
                method="post",
                session=requests.Session(),
                url=Url.parse_or_raise("https://app.ilastik.org/api/refresh_token"),
                headers={
                    "Authorization": f"Bearer {cls._token.raw_token}",
                    "X-Authorization-Refresh": cls._token.refresh_token,
                },
            )
            if isinstance(request_result, Exception):
                return request_result
            result_json = parse_json(request_result[0])
            if isinstance(result_json, Exception):
                return result_json
            dto_result = EbrainsAccessTokenDto.from_json_value(result_json)
            if isinstance(dto_result, Exception):
                return dto_result
            checking_key_result = HbpIamPublicKey.get_sync()
            if isinstance(checking_key_result, Exception):
                return checking_key_result
            token_result = AccessToken.from_dto(dto_result, checking_key=checking_key_result)
            if isinstance(token_result, Exception):
                return token_result
            cls._token = token_result
            return token_result