from typing import Literal, Mapping, Optional
import requests

from webilastik.utility.url import Url

class ErrRequestCompletedAsFailure(Exception):
    def __init__(self, response: requests.Response) -> None:
        self.response = response
        super().__init__(f"Request completed but with a failure response: {response.status_code}")

class ErrRequestCrashed(Exception):
    def __init__(self, cause: Exception) -> None:
        self.request_exception = cause
        super().__init__(f"Request crashed")

def request(
    session: requests.Session,
    method: Literal["get", "put", "post", "delete"],
    url: Url,
    data: Optional[bytes] = None,
    headers: "Mapping[str, str] | None" = None,
) -> "bytes | ErrRequestCompletedAsFailure | ErrRequestCrashed":
    try:
        response = session.request(method=method, url=url.schemeless_raw, data=data, headers=headers)
        if not response.ok:
            return ErrRequestCompletedAsFailure(response)
        return response.content
    except Exception as e:
        print(f"WTF? {e}")
        return ErrRequestCrashed(e)