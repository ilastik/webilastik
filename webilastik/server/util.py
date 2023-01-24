from base64 import b64decode
import json
from pathlib import Path, PurePosixPath
from typing import Optional

from aiohttp import web
from webilastik.datasource import FsDataSource
from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_credentials import EbrainsUserCredentials
from webilastik.libebrains.user_token import UserToken
from webilastik.server.rpc.dto import parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_


def get_encoded_datasource_from_url(
    match_info_key: str, request: web.Request, ebrains_user_credentials: Optional[EbrainsUserCredentials]
) -> "FsDataSource | Exception":
    encoded_datasource = request.match_info.get(match_info_key)
    if not encoded_datasource:
        return Exception("Missing path segment: datasource=...")
    decoded_datasource = b64decode(encoded_datasource, altchars=b'-_').decode('utf8')
    datasource_json_value = json.loads(decoded_datasource)
    datasource_dto = parse_as_Union_of_PrecomputedChunksDataSourceDto0N5DataSourceDto0SkimageDataSourceDto0DziLevelDataSourceDto_endof_(datasource_json_value)
    if isinstance(datasource_dto, Exception):
        return datasource_dto
    return FsDataSource.try_from_message(datasource_dto, ebrains_user_credentials=ebrains_user_credentials)

def sanitize(path: Path) -> str:
    return "'" + path.as_posix() + "'"