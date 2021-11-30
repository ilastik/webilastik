# pyright: strict

from pathlib import Path
from typing import Optional, Sequence, Tuple, Union
from dataclasses import dataclass
# import functools
from ndstructs.point5D import Point5D
from ndstructs.utils.json_serializable import JsonValue, ensureJsonIntTripplet, ensureJsonObject, ensureJsonString, ensureOptional

from webilastik.datasource import DataSource, SkimageDataSource
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo
from webilastik.libebrains.user_token import UserToken
from webilastik.ui.filesystem import try_filesystem_from_url
from webilastik.ui.usage_error import UsageError

from webilastik.utility.url import Url, Protocol

@dataclass
class DataSourceLoadParams:
    url: Url
    spatial_resolution: Optional[Tuple[int, int, int]]
    location_override: Optional[Point5D] = None

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "DataSourceLoadParams":
        value_obj = ensureJsonObject(value)

        return DataSourceLoadParams(
            url=Url.parse(ensureJsonString(value_obj.get("url"))),
            spatial_resolution=ensureOptional(ensureJsonIntTripplet, value_obj.get("spatial_resolution")),
            location_override=ensureOptional(Point5D.from_json_value, value_obj.get("location_override")),
        )

    def try_load(
        self, *, ebrains_user_token: Optional[UserToken], allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
    ) -> Union[DataSource, UsageError]:
        fs_url = self.url.parent
        ds_path = Path(self.url.path.name)

        filesystem = try_filesystem_from_url(url=fs_url, allowed_protocols=allowed_protocols, ebrains_user_token=ebrains_user_token)
        if not filesystem:
            return UsageError(f"Can't retrieve data from {fs_url}")

        if ds_path.suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
            return SkimageDataSource(
                path=ds_path,
                filesystem=filesystem,
                location=self.location_override or Point5D.zero(),
                spatial_resolution=self.spatial_resolution,
            )

        #FIXME: add other datasource types, don't immediately assume precomp chunks
        if PrecomputedChunksInfo.tryLoad(filesystem=filesystem, path=Path("/info")):
            if self.spatial_resolution is None:
                return UsageError("Precomputed chunks must specify a resolution")
            return PrecomputedChunksDataSource(
                filesystem=filesystem,
                path=ds_path,
                resolution=self.spatial_resolution,
            )
        return UsageError(f"Could not open {self.url}")