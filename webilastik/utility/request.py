from io import IOBase
from typing import Literal, Mapping, Optional
import requests

from webilastik.utility.url import Url

class ErrRequestCompletedAsFailure(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Request completed but with a failure response: {status_code}")

class ErrRequestCrashed(Exception):
    def __init__(self, cause: Exception) -> None:
        self.request_exception = cause
        super().__init__(f"Request crashed")

def request(
    session: requests.Session,
    method: Literal["get", "put", "post", "delete"],
    url: Url,
    data: "bytes | IOBase | None" = None,
    headers: "Mapping[str, str] | None" = None,
) -> "bytes | ErrRequestCompletedAsFailure | ErrRequestCrashed":
    try:
        response = session.request(method=method, url=url.schemeless_raw, data=data, headers=headers)
        if not response.ok:
            return ErrRequestCompletedAsFailure(response.status_code)
        return response.content
    except Exception as e:
        print(f"WTF? {e}")
        return ErrRequestCrashed(e)