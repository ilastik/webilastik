# pyright: strict

from base64 import b64decode, b64encode
import re
from pathlib import PurePosixPath
import enum
from typing import Literal, Optional, List, Dict, Mapping, Union, Final
from typing_extensions import assert_never
from urllib.parse import parse_qs, urlencode, quote_plus, quote

from webilastik.server.rpc import dto

DataScheme = Literal["precomputed", "n5", "deepzoom"]
Protocol = Literal["http", "https", "file", "memory"]

class SearchQuotingMethod(enum.Enum):
    QUOTE = 0
    QUOTE_PLUS = 1

def parse_params(params: "str | None") -> Dict[str, str]:
    if params is None:
        return {}
    else:
        parsed_params: Dict[str, List[str]] = parse_qs(params, keep_blank_values=True, strict_parsing=True, encoding='utf-8')
        return {k: v[-1] if v else "" for k,v in parsed_params.items()}

class Url:
    datascheme: Optional[DataScheme]
    protocol: Protocol

    datascheme_pattern: Final[str] = (
        "("
            r"(?P<datascheme>precomputed|n5|deepzoom)" + r"(\+|://)"
        ")?"
    )
    hostname_pattern: Final[str] = r"(?P<hostname>[\w\-\.]+)"
    port_pattern: Final[str] = (
        "(:"
            r"(?P<port>\d+)"
        ")?"
    )
    path_pattern: Final[str] = r"(?P<path>/[^?#]*)"
    search_params_pattern: Final[str] = (
        r"(\?"
            r"(?P<search>[^#]*)"
        r")?"
    )
    hash_pattern: Final[str] = (
        r"(#"
            r"(?P<hash_>.*)"
        r")?"
    )

    file_url_regex = re.compile(
        datascheme_pattern + "file://" + path_pattern + hash_pattern,
        re.IGNORECASE
    )

    networked_url_regex = re.compile(
        datascheme_pattern + r"(?P<protocol>http|https)://" + hostname_pattern + port_pattern + path_pattern + search_params_pattern + hash_pattern,
        re.IGNORECASE,
    )

    @classmethod
    def parse_as_file_url(cls, raw_url: str) -> "Url | None | Exception":
        match = Url.file_url_regex.fullmatch(raw_url)
        if match is None:
            return None
        datascheme = match.group("datascheme")
        if datascheme != "precomputed" and datascheme != "n5" and datascheme != "deepzoom":
            return ValueError(f"unexpected datascheme: {datascheme}")
        return Url(
            datascheme=datascheme,
            protocol="file",
            hostname="",
            path=PurePosixPath(match.group("path")),
            hash_=match.group("hash_")
        )

    @classmethod
    def parse_as_net_url(cls, raw_url: str) -> "Url | None | Exception":
        match = Url.networked_url_regex.fullmatch(raw_url)
        if match is None:
            return None
        datascheme = match.group("datascheme")
        if datascheme is not None and datascheme != "precomputed" and datascheme != "n5" and datascheme != "deepzoom":
            return RuntimeError(f"Bug: unexpected datascheme: {datascheme}")
        protocol = match.group("protocol")
        if protocol != "http" and protocol != "https":
            return RuntimeError(f"Bug: unexpected protocol: {protocol}")
        raw_port = match.group("port")
        if raw_port is None:
            port = None
        else:
            try:
                port = int(raw_port)
            except:
                return None #Fixme: would be better to return an exception
        try:
            path = PurePosixPath(match.group("path"))
        except:
            return ValueError(f"Could not parse URL path from {raw_url}")

        raw_search = match.group("search")
        search = parse_params(raw_search)

        return Url(
            datascheme=datascheme,
            protocol=protocol,
            hostname=match.group("hostname"),
            port=port,
            path=path,
            search=search,
            hash_=match.group("hash_")
        )

    def to_ilp_info_filePath(self) -> str:
        # FIXME: not completely compatible with classic ilastik
        if self.protocol == "file" and not self.datascheme:
            return self.path.as_posix()
        return self.raw

    @staticmethod
    def parse(url: str) -> Optional["Url"]:
        file_url_result = Url.parse_as_file_url(url)
        if isinstance(file_url_result, Url):
            return file_url_result
        if isinstance(file_url_result, Exception):
            return None #FIXME
        if file_url_result is not None:
            assert_never(file_url_result)

        net_url_result = Url.parse_as_net_url(url)
        if isinstance(net_url_result, Url):
            return net_url_result
        if isinstance(net_url_result, Exception):
            return None #FIXME
        if net_url_result is not None:
            assert_never(net_url_result)
        return None

    @staticmethod
    def parse_or_raise(url: str) -> "Url":
        parsed = Url.parse(url)
        if parsed is None:
            raise ValueError("Could not parse {str} as an Url")
        return parsed

    @classmethod
    def from_dto(cls, url_message: dto.UrlDto) -> 'Url':
        return Url(
            datascheme=url_message.datascheme,
            protocol=url_message.protocol,
            hostname=url_message.hostname,
            port=url_message.port,
            path=PurePosixPath(url_message.path),
            search=url_message.search,
            hash_=url_message.fragment,
        )

    def to_dto(self) -> dto.UrlDto:
        return dto.UrlDto(
            datascheme=self.datascheme,
            protocol=self.protocol,
            hostname=self.hostname,
            port=self.port,
            path=self.path.as_posix(),
            search=self.search,
            fragment=self.hash_,
        )

    #FIXME: http:// and file:// URLs are too different to be a single class
    #FIXME: file:// has no hostname, search or port
    def __init__(
        self,
        *,
        datascheme: Optional[DataScheme] = None,
        protocol: Literal["http", "https", "file", "memory"],
        hostname: str,
        port: Optional[int] = None,
        path: PurePosixPath,
        search: Optional[Mapping[str, str]] = None,
        hash_: Optional[str] = None,
        search_quoting_method: SearchQuotingMethod = SearchQuotingMethod.QUOTE_PLUS,
    ):
        path = PurePosixPath("/") / path
        path_parts: List[str] = []
        for part in  path.as_posix().split("/"):
            if part == "." or part == "":
                continue;
            if part == "..":
                if len(path_parts) > 0:
                    _ = path_parts.pop()
            else:
                path_parts.append(part)

        self.datascheme = datascheme
        self.protocol = protocol
        self.hostname = hostname
        self.host = hostname + ("" if port is None else f":{port}")
        self.port = port
        self.path = PurePosixPath("/") / "/".join(path_parts)
        self.search = search or {}
        self.hash_ = hash_
        self.schemeless_raw = f"{protocol}://{self.host if protocol != 'file' else ''}"
        self.schemeless_raw += str(path)
        if self.search and protocol != "file":
            if search_quoting_method == SearchQuotingMethod.QUOTE_PLUS:
                quote_via = quote_plus
            else:
                quote_via = quote
            self.schemeless_raw += "?" + urlencode(self.search, doseq=True, quote_via=quote_via)
        if self.hash_:
            self.schemeless_raw += "#" + self.hash_

        if self.datascheme:
            self.raw = f"{self.datascheme}+{self.schemeless_raw}"
            self.double_protocol_raw = f"{self.datascheme}://{self.schemeless_raw}"
        else:
            self.raw = self.schemeless_raw
            self.double_protocol_raw = self.raw

        if hostname == "" and protocol != "file" and protocol != "memory":
            raise ValueError(f"Missing hostname in {self.raw}")
        super().__init__()

    def __hash__(self) -> int:
        return hash(self.raw)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Url) and self.raw == other.raw

    def __str__(self) -> str:
        return self.raw

    def updated_with(
        self,
        *,
        datascheme: Optional[DataScheme] = None,
        protocol: Optional[Protocol] = None,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[PurePosixPath] = None,
        search: Optional[Mapping[str, str]] = None,
        extra_search: Optional[Mapping[str, str]] = None,
        hash_: Optional[str] = None,
    ) -> "Url":

        new_search = search if search is not None else self.search
        if hash_ is None:
            new_hash = self.hash_
        elif hash_ == "":
            new_hash = None
        else:
            new_hash = hash_
        return Url(
            path=path or self.path,
            datascheme=datascheme or self.datascheme,
            protocol=protocol or self.protocol,
            hostname=hostname or self.hostname,
            port=port or self.port,
            search={**new_search, **(extra_search or {})},
            hash_=new_hash
        )

    def schemeless(self) -> "Url":
        return Url(
            path=self.path,
            datascheme=None,
            protocol=self.protocol,
            hostname=self.hostname,
            port=self.port,
            search={**self.search},
            hash_=self.hash_,
        )

    def hashless(self) -> "Url":
        return Url(
            path=self.path,
            datascheme=self.datascheme,
            protocol=self.protocol,
            hostname=self.hostname,
            port=self.port,
            search={**self.search},
            hash_=None,
        )

    def get_hash_params(self) -> "Dict[str, str]":
        if not self.hash_:
            return {}
        return parse_params(self.hash_)

    @property
    def parent(self) -> "Url":
        return self.updated_with(path=self.path.parent)

    def joinpath(self, subpath: Union[str, PurePosixPath]) -> "Url":
        """joins paths the same way Path does (e.g.: absolute paths are not appended)"""
        return self.updated_with(path=self.path / subpath)

    def concatpath(self, subpath: Union[str, PurePosixPath]) -> "Url":
        """Always concatenates path, event if starting with '/'. Disallows going up the path with .."""
        fixed_subpath = PurePosixPath("/").joinpath(subpath).as_posix().lstrip("/")
        return self.joinpath(fixed_subpath)

    def ensure_datascheme(self, datascheme: DataScheme) -> "Url":
        if self.datascheme != datascheme:
            raise ValueError(f"Url {self.raw} had unexpected datascheme: {self.datascheme}. Expected {datascheme}")
        return self

    def to_base64(self) -> str:
        return b64encode(self.raw.encode("utf8"), altchars=b'-_').decode("utf8")

    @staticmethod
    def from_base64(encoded_url: str) -> "Url":
        decoded_raw_url = b64decode(encoded_url, altchars=b'-_').decode('utf8')
        url = Url.parse(decoded_raw_url)
        assert url is not None
        return url