# pyright: strict

import re
from pathlib import PurePosixPath
import enum
from typing import Optional, List, Dict, Mapping, Union
from urllib.parse import parse_qs, urlencode, quote_plus, quote

from ndstructs.utils.json_serializable import JsonValue, ensureJsonString


class DataScheme(enum.Enum):
    PRECOMPUTED = "precomputed"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_str(cls, value: str) -> "DataScheme":
        for scheme in DataScheme:
            if scheme.value == value:
                return scheme
        raise ValueError(f"Bad data scheme: {value}")

class Protocol(enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    FILE = "file"
    MEMORY = "memory"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_str(cls, value: str) -> "Protocol":
        for protocol in Protocol:
            if protocol.value == value.lower():
                return protocol
        raise ValueError(f"Bad protocol: {value}")

class SearchQuotingMethod(enum.Enum):
    QUOTE = 0
    QUOTE_PLUS = 1

class Url:
    hostname_pattern = r"[0-9a-z\-\.]*"

    url_pattern = re.compile(
        "("
            r"(?P<datascheme>[a-z0-9\-\.]+)" + r"(\+|://)"
        ")?"

        r"(?P<protocol>[a-z0-9\-\.]+)" + "://"

        f"(?P<hostname>{hostname_pattern})"

        "(:"
            r"(?P<port>\d+)"
        ")?"

        r"(?P<path>/[^?]*)"

        r"(\?"
            r"(?P<search>[^#]*)"
        r")?"

        r"(#"
            r"(?P<hash_>.*)"
        r")?",
        re.IGNORECASE
    )

    def to_json_value(self) -> JsonValue:
        return self.raw

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "Url":
        url = Url.parse(ensureJsonString(value))
        if url is not None:
            return url
        raise ValueError(f"Bad url: {value}")

    @staticmethod
    def parse(url: str) -> Optional["Url"]:
        match = Url.url_pattern.fullmatch(url)
        if match is None:
            return None
        raw_datascheme = match.group("datascheme")
        raw_port = match.group("port")
        raw_search = match.group("search")
        if raw_search is None:
            search: Dict[str, str] = {}
        else:
            parsed_qs: Dict[str, List[str]] = parse_qs(raw_search, keep_blank_values=True, strict_parsing=True, encoding='utf-8')
            search: Dict[str, str] = {k: v[-1] if v else "" for k,v in parsed_qs.items()}

        return Url(
            datascheme=None if raw_datascheme is None else DataScheme.from_str(raw_datascheme),
            protocol=Protocol.from_str(match.group("protocol")),
            hostname=match.group("hostname"),
            port=None if raw_port is None else int(raw_port),
            path=PurePosixPath(match.group("path")),
            search=search,
            hash_=match.group("hash_")
        );

    def __init__(
        self,
        *,
        datascheme: Optional[DataScheme] = None,
        protocol: Protocol,
        hostname: str,
        port: Optional[int] = None,
        path: PurePosixPath,
        search: Optional[Mapping[str, str]] = None,
        hash_: Optional[str] = None,
        search_quoting_method: SearchQuotingMethod = SearchQuotingMethod.QUOTE_PLUS,
    ):
        if not path.is_absolute():
            raise ValueError("Path '{path}' is not absolute")
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
        self.schemeless_raw = f"{protocol}://{self.host}"
        if self.port:
            self.schemeless_raw += f":{self.port}"
        self.schemeless_raw += str(path)
        if self.search:
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

        if hostname == "" and protocol not in (Protocol.FILE, Protocol.MEMORY):
            raise ValueError(f"Missing hostname in {self.raw}")

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
        return Url(
            path=path or self.path,
            datascheme=datascheme or self.datascheme,
            protocol=protocol or self.protocol,
            hostname=hostname or self.hostname,
            port=port or self.port,
            search={**new_search, **(extra_search or {})},
            hash_=hash_ if hash_ is not None else self.hash_,
        )

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
