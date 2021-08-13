from pathlib import PurePosixPath
from typing import Union, Mapping, Optional

import requests
from ndstructs.utils.json_serializable import JsonValue

from webilastik.utility.url import Url
from webilastik.libebrains.user_token import UserToken


class HttpClient:
    def __init__(
        self, token: "UserToken", api_url: Url, https_verify: bool = True
    ):
        self.token = token
        self.api_url = api_url
        self.https_verify = https_verify
