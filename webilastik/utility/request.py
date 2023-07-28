# pyright: strict

from io import IOBase
from typing import Literal, Mapping, Tuple
import requests
import sys

from requests.models import CaseInsensitiveDict

from webilastik.utility.url import Url

class ErrRequestCompletedAsFailure(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Request completed but with a failure response: {status_code}")

class ErrRequestCrashed(Exception):
    def __init__(self, cause: Exception) -> None:
        self.request_exception = cause
        super().__init__(f"Request crashed")

class ErrBadContentLength(Exception):
    pass

def request(
    session: requests.Session,
    method: Literal["get", "put", "post", "delete", "head"],
    url: Url,
    data: "bytes | IOBase | None" = None,
    offset: int = 0,
    num_bytes: "int | None" = None,
    headers: "Mapping[str, str] | None" = None,
) -> "Tuple[bytes, CaseInsensitiveDict[str]] | ErrRequestCompletedAsFailure | ErrRequestCrashed":
    range_header_value: str
    if offset >= 0:
        range_header_value = f"bytes={offset}-"
        if num_bytes is not None:
            range_end = max(offset, offset + num_bytes - 1)
            range_header_value += str(range_end)
    else:
        range_header_value = f"bytes={offset}"

    headers = {**(headers or {}), "Range": range_header_value}

    try:
        response = session.request(method=method, url=url.schemeless_raw, data=data, headers=headers)
        if not response.ok:
            return ErrRequestCompletedAsFailure(response.status_code)
        content = response.content
        if num_bytes is not None:
            content = content[:num_bytes]
        return (content, response.headers)
    except Exception as e:
        print(f"HTTP ERROR: {e}", file=sys.stderr)
        return ErrRequestCrashed(e)

def request_size(
    session: requests.Session,
    url: Url,
    headers: "Mapping[str, str] | None" = None,
) -> "int | ErrRequestCompletedAsFailure | ErrRequestCrashed | ErrBadContentLength":
    response = request(session=session, method="head", url=url, headers=headers)
    if isinstance(response, Exception):
        return response
    try:
        return int(response[1]["content-length"])
    except Exception:
        return ErrBadContentLength()