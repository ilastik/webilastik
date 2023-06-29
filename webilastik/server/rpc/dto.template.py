#pyright: strict

from typing import Literal, Optional, Tuple, Union, Mapping, Any, cast
from dataclasses import dataclass

from ndstructs.point5D import Interval5D, Point5D, Shape5D
import numpy as np

from webilastik.server.rpc import DataTransferObject

# @dataclass
# class DataType(DataTransferObject):
#     type_name: Literal["uint8", "uint16", "uint32", "uint64", "float32"]

@dataclass
class ColorDto(DataTransferObject):
    r: int
    g: int
    b: int

@dataclass
class LabelHeaderDto(DataTransferObject):
    name: str
    color: ColorDto

Protocol = Literal["http", "https", "file", "memory"]

@dataclass
class UrlDto(DataTransferObject):
    datascheme: Optional[Literal["precomputed", "n5"]]
    protocol: Literal["http", "https", "file", "memory"]
    hostname: str
    port: Optional[int]
    path: str
    search: Optional[Mapping[str, str]]
    fragment: Optional[str]

@dataclass
class Point5DDto(DataTransferObject):
    x: int
    y: int
    z: int
    t: int
    c: int

    @classmethod
    def from_point5d(cls, point: Point5D) -> "Point5DDto":
        return Point5DDto(x=point.x, y=point.y, z=point.z, t=point.t, c=point.c)
    def to_point5d(self) -> Point5D:
        return Point5D(x=self.x, y=self.y, z=self.z, t=self.t, c=self.c)

@dataclass
class Shape5DDto(Point5DDto):
    @classmethod
    def from_shape5d(cls, shape: Shape5D) -> "Shape5DDto":
        return Shape5DDto(x=shape.x,y=shape.y,z=shape.z,t=shape.t,c=shape.c)
    def to_shape5d(self) -> Shape5D:
        return Shape5D(x=self.x, y=self.y, z=self.z, t=self.t, c=self.c)

@dataclass
class Interval5DDto(DataTransferObject):
    start: Point5DDto
    stop: Point5DDto

    @classmethod
    def from_interval5d(cls, interval: Interval5D) -> 'Interval5DDto':
        return Interval5DDto(
            start=Point5DDto.from_point5d(interval.start),
            stop=Point5DDto.from_point5d(interval.stop)
        )
    def to_interval5d(self) -> Interval5D:
        return Interval5D.create_from_start_stop(start=self.start.to_point5d(), stop=self.stop.to_point5d())

@dataclass
class OsfsDto(DataTransferObject):
    pass

@dataclass
class HttpFsDto(DataTransferObject):
    protocol: Literal["http", "https"]
    hostname: str
    port: Optional[int]
    path: str
    search: Optional[Mapping[str, str]]
    # fragment: Optional[str]

@dataclass
class BucketFSDto(DataTransferObject):
    bucket_name: str

@dataclass
class ZipFsDto(DataTransferObject):
    zip_file_fs: Union[OsfsDto, HttpFsDto, BucketFSDto] #FIXME: no other ZipFs?
    zip_file_path: str

FsDto = Union[OsfsDto, HttpFsDto, BucketFSDto, ZipFsDto]

DtypeDto = Literal["uint8", "uint16", "uint32", "uint64", "int64", "float32"]

def dtype_to_dto(dtype: "np.dtype[Any]") -> DtypeDto:
    return cast(DtypeDto, str(dtype))

@dataclass
class PrecomputedChunksDataSourceDto(DataTransferObject):
    url: UrlDto
    filesystem: FsDto
    path: str
    scale_key: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    dtype: DtypeDto
    encoder: Literal["raw", "jpeg"]

#####################################################

ImageFormatDto = Literal["jpeg", "jpg", "png"]

@dataclass
class DziSizeElementDto(DataTransferObject):
    Width: int
    Height: int

@dataclass
class DziImageElementDto(DataTransferObject):
    Format: ImageFormatDto
    Overlap: int
    TileSize: int
    Size: DziSizeElementDto

@dataclass
class DziLevelSinkDto(DataTransferObject):
    filesystem: FsDto
    xml_path: str
    dzi_image: DziImageElementDto
    num_channels: Literal[1, 3]
    level_index: int

@dataclass
class DziLevelDataSourceDto(DataTransferObject):
    filesystem: FsDto
    xml_path: str
    dzi_image: DziImageElementDto
    num_channels: Literal[1, 3]
    level_index: int


############################################

@dataclass
class N5GzipCompressorDto(DataTransferObject):
    level: int

    @classmethod
    def tag_key(cls) -> str:
        return "type"

    @classmethod
    def tag_value(cls) -> str:
        return "gzip"

@dataclass
class N5Bzip2CompressorDto(DataTransferObject):
    blockSize: int # name doesn't make sense but is what is in the n5 'spec'

    @classmethod
    def tag_key(cls) -> str:
        return "type"

    @classmethod
    def tag_value(cls) -> str:
        return "bzip2"

@dataclass
class N5XzCompressorDto(DataTransferObject):
    preset: int

    @classmethod
    def tag_key(cls) -> str:
        return "type"

    @classmethod
    def tag_value(cls) -> str:
        return "xz"

@dataclass
class N5RawCompressorDto(DataTransferObject):
    @classmethod
    def tag_key(cls) -> str:
        return "type"

    @classmethod
    def tag_value(cls) -> str:
        return "raw"

N5CompressorDto = Union[N5GzipCompressorDto, N5Bzip2CompressorDto, N5XzCompressorDto, N5RawCompressorDto]

@dataclass
class N5DatasetAttributesDto(DataTransferObject):
    dimensions: Tuple[int, ...]
    blockSize: Tuple[int, ...]
    # axes: Optional[Tuple[Literal["x", "y", "z", "t", "c"], ...]] # FIXME: retore this
    axes: Optional[Tuple[str, ...]] # FIXME: retore this
    dataType: DtypeDto
    compression: N5CompressorDto

    @classmethod
    def tag_value(cls) -> None:
        return None

@dataclass
class N5DataSourceDto(DataTransferObject):
    url: UrlDto
    filesystem: FsDto
    path: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    dtype: DtypeDto
    compressor: N5CompressorDto
    c_axiskeys_on_disk: str

@dataclass
class SkimageDataSourceDto(DataTransferObject):
    url: UrlDto
    filesystem: FsDto
    path: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    dtype: DtypeDto


FsDataSourceDto = Union[PrecomputedChunksDataSourceDto, N5DataSourceDto, SkimageDataSourceDto, DziLevelDataSourceDto]

##################################################333

@dataclass
class PrecomputedChunksSinkDto(DataTransferObject):
    filesystem: Union[OsfsDto, HttpFsDto, BucketFSDto]
    path: str #FIXME?
    tile_shape: Shape5DDto
    interval: Interval5DDto
    dtype: DtypeDto
    scale_key: str #fixme?
    resolution: Tuple[int, int, int]
    encoding: Literal["raw", "jpeg"]

#################################################

@dataclass
class N5DataSinkDto(DataTransferObject):
    filesystem: FsDto
    path: str
    interval: Interval5DDto
    tile_shape: Shape5DDto
    spatial_resolution: Tuple[int, int, int]
    c_axiskeys: str
    dtype: DtypeDto
    compressor: N5CompressorDto

DataSinkDto = Union[PrecomputedChunksSinkDto, N5DataSinkDto, DziLevelSinkDto]

#################################################################

@dataclass
class PixelAnnotationDto(DataTransferObject):
    raw_data: FsDataSourceDto
    points: Tuple[Tuple[int, int, int], ...]

######################################################################

@dataclass
class RpcErrorDto(DataTransferObject):
    error: str

#################################################################
@dataclass
class RecolorLabelParams(DataTransferObject):
    label_name: str
    new_color: ColorDto

@dataclass
class RenameLabelParams(DataTransferObject):
    old_name: str
    new_name: str

@dataclass
class CreateLabelParams(DataTransferObject):
    label_name: str
    color: ColorDto

@dataclass
class RemoveLabelParams(DataTransferObject):
    label_name: str

@dataclass
class AddPixelAnnotationParams(DataTransferObject):
    label_name: str
    pixel_annotation: PixelAnnotationDto

@dataclass
class RemovePixelAnnotationParams(DataTransferObject):
    label_name: str
    pixel_annotation: PixelAnnotationDto

@dataclass
class LabelDto(DataTransferObject):
    name: str
    color: ColorDto
    annotations: Tuple[PixelAnnotationDto, ...]

@dataclass
class BrushingAppletStateDto(DataTransferObject):
    labels: Tuple[LabelDto, ...]

##################################################3

@dataclass
class JobDto(DataTransferObject):
    name: str
    num_args: Optional[int]
    uuid: str
    status: Literal["pending", "running", "cancelled", "completed"]
    num_completed_steps: int
    error_message: Optional[str]

@dataclass
class ExportJobDto(JobDto):
    datasink: DataSinkDto


@dataclass
class OpenDatasinkJobDto(JobDto):
    datasink: DataSinkDto

@dataclass
class CreateDziPyramidJobDto(JobDto):
    pass

@dataclass
class ZipJobDto(JobDto):
    output_fs: FsDto
    output_path: str

ExportJobDtoUnion = Union[ExportJobDto, OpenDatasinkJobDto, CreateDziPyramidJobDto, ZipJobDto]

@dataclass
class PixelClassificationExportAppletStateDto(DataTransferObject):
    jobs: Tuple[ExportJobDtoUnion, ...]
    populated_labels: Optional[Tuple[LabelHeaderDto, ...]]
    datasource_suggestions: Optional[Tuple[FsDataSourceDto, ...]]



#########################################################

@dataclass
class IlpFeatureExtractorDto(DataTransferObject):
    ilp_scale: float
    axis_2d: Optional[Literal["x", "y", "z"]]
    class_name: Literal[
        "Gaussian Smoothing",
        "Laplacian of Gaussian",
        "Gaussian Gradient Magnitude",
        "Difference of Gaussians",
        "Structure Tensor Eigenvalues",
        "Hessian of Gaussian Eigenvalues"
    ]

@dataclass
class FeatureSelectionAppletStateDto(DataTransferObject):
    feature_extractors: Tuple[IlpFeatureExtractorDto, ...]

@dataclass
class AddFeatureExtractorsParamsDto(DataTransferObject):
    feature_extractors: Tuple[IlpFeatureExtractorDto, ...]

@dataclass
class RemoveFeatureExtractorsParamsDto(DataTransferObject):
    feature_extractors: Tuple[IlpFeatureExtractorDto, ...]

#################################################################


@dataclass
class ComputeSessionDto(DataTransferObject):
    start_time_utc_sec: Optional[int]
    time_elapsed_sec: int
    time_limit_minutes: int
    num_nodes: int
    compute_session_id: str
    state: Literal[
        "BOOT_FAIL",
        "CANCELLED",
        "COMPLETED",
        "DEADLINE",
        "FAILED",
        "NODE_FAIL",
        "OUT_OF_MEMORY",
        "PENDING",
        "PREEMPTED",
        "RUNNING",
        "REQUEUED",
        "RESIZING",
        "REVOKED",
        "SUSPENDED",
        "TIMEOUT",
    ]

HpcSiteName = Literal["LOCAL_DASK", "LOCAL_PROCESS_POOL", "CSCS", "JUSUF"]

@dataclass
class ComputeSessionStatusDto(DataTransferObject):
    compute_session: ComputeSessionDto
    hpc_site: HpcSiteName
    session_url: UrlDto
    connected: bool

@dataclass
class CreateComputeSessionParamsDto(DataTransferObject):
    session_duration_minutes: int
    hpc_site: HpcSiteName

@dataclass
class GetComputeSessionStatusParamsDto(DataTransferObject):
    compute_session_id: str
    hpc_site: HpcSiteName

@dataclass
class CloseComputeSessionParamsDto(DataTransferObject):
    compute_session_id: str
    hpc_site: HpcSiteName

@dataclass
class CloseComputeSessionResponseDto(DataTransferObject):
    compute_session_id: str

@dataclass
class ListComputeSessionsParamsDto(DataTransferObject):
    hpc_site: HpcSiteName

@dataclass
class ListComputeSessionsResponseDto(DataTransferObject):
    compute_sessions_stati: Tuple[ComputeSessionStatusDto, ...]

@dataclass
class GetAvailableHpcSitesResponseDto(DataTransferObject):
    available_sites: Tuple[HpcSiteName, ...]

#############################################################3

@dataclass
class CheckLoginResultDto(DataTransferObject):
    logged_in: bool

#############################################3333

@dataclass
class StartPixelProbabilitiesExportJobParamsDto(DataTransferObject):
    datasource: FsDataSourceDto
    datasink: DataSinkDto

@dataclass
class StartSimpleSegmentationExportJobParamsDto(DataTransferObject):
    datasource: FsDataSourceDto
    datasink: DataSinkDto
    label_header: LabelHeaderDto

############################################

@dataclass
class LoadProjectParamsDto(DataTransferObject):
    fs: FsDto
    project_file_path: str


@dataclass
class SaveProjectParamsDto(DataTransferObject):
    fs: FsDto
    project_file_path: str

#########################################

@dataclass
class GetDatasourcesFromUrlParamsDto(DataTransferObject):
    url: UrlDto

@dataclass
class GetDatasourcesFromUrlResponseDto(DataTransferObject):
    datasources: Union[Tuple[FsDataSourceDto, ...], None]


@dataclass
class GetFileSystemAndPathFromUrlParamsDto(DataTransferObject):
    url: UrlDto
@dataclass
class GetFileSystemAndPathFromUrlResponseDto(DataTransferObject):
    fs: FsDto
    path: str


@dataclass
class CheckDatasourceCompatibilityParams(DataTransferObject):
    datasources: Tuple[FsDataSourceDto, ...]
    # classifier_generation: int

@dataclass
class CheckDatasourceCompatibilityResponse(DataTransferObject):
    compatible: Tuple[bool, ...]


#################################################

@dataclass
class ListFsDirRequest(DataTransferObject):
    fs: FsDto
    path: str

@dataclass
class ListFsDirResponse(DataTransferObject):
    files: Tuple[str, ...]
    directories: Tuple[str, ...]