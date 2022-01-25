from typing import Union

from webilastik.utility.url import Url
from webilastik.ui.usage_error import UsageError

def parse_url(url: str) -> Union[Url, UsageError]:
    parsed_url = Url.parse(url)
    if parsed_url is None:
        return UsageError(f"Bad url: {url}")
    return parsed_url