# pyright: strict

from pathlib import PurePosixPath
from tests import run_all_tests
from webilastik.utility.url import Url

def test_url_basics():
    raw = "precomputed://http://some.host.com/some/path?a=123&b=456#myhash"
    url = Url.parse(raw)
    assert url is not None
    assert url.datascheme == "precomputed"
    assert url.protocol == "http"
    assert url.port == None
    assert url.path == PurePosixPath("/some/path")
    assert url.search == {"a": '123', "b": '456'}
    assert url.double_protocol_raw == raw

    url2 = url.updated_with(extra_search={"c": "456", "d": "789"})
    assert url2.search ==  {"a": '123', "b": '456', "c": "456", "d": "789"}
    assert url2.raw == "precomputed+http://some.host.com/some/path?a=123&b=456&c=456&d=789#myhash"

    url3 = Url.parse("http://some.host.com/some/path?a=123&b=%5B1%2C+2%2C+3%5D#myhash")
    assert url3 is not None
    assert url3.search["b"]== '[1, 2, 3]'

if __name__ == "__main__":
    import sys
    run_all_tests(sys.modules[__name__])