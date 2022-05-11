
#pyright: strict

from datetime import datetime
from abc import ABC
from pathlib import Path
from typing import Callable, ClassVar, Any, Mapping, Sequence, Tuple, TypeVar
from collections.abc import Mapping as AbcMapping
from typing_extensions import TypeAlias
import enum
import uuid

from h5py._hl.datatype import Datatype
from vigra.vigranumpycore import AxisTags

import numpy as np
from numpy import ndarray
import vigra
import h5py
from webilastik.datasource import FsDataSource
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem import JsonableFilesystem
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.ui.usage_error import UsageError
from webilastik.utility.url import Protocol, Url



IlpDatasetContents: TypeAlias = "int | bytes | str | bool | Tuple[int, ...] | Tuple[float, ...] | ndarray[Any, Any] | np.void"


class IlpParsingError(Exception):
    pass

class IlpMissingKey(IlpParsingError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Key not found: {key}")

class IlpTypeMismatch(IlpParsingError):
    def __init__(
        self,
        *,
        key: str,
        expected_dtype: "np.dtype[Any]",
        expected_shape: Tuple[int, ...],
        dataset: h5py.Dataset,
    ):
        super().__init__(
            f"Expected {key} to be of type '{expected_dtype} {expected_shape}', found '{dataset.dtype} {dataset.shape}'"
        )

class IlpAttrDataset:
    def __init__(
        self,
        value: IlpDatasetContents,
        *,
        attrs: Mapping[str, str]  #FIXME values could be of types other than str
    ) -> None:
        self.value = value
        self.attrs = attrs
        super().__init__()

IlpDatasetValue: TypeAlias = "IlpDatasetContents | IlpAttrDataset"
IlpGroup: TypeAlias = Mapping[str, "IlpValue"]
IlpValue: TypeAlias = "IlpDatasetValue | IlpGroup"

def ensure_dataset(group: h5py.Group, key: str) -> h5py.Dataset:
    if key not in group:
        raise IlpMissingKey(key)
    dataset = group[key]
    if not isinstance(dataset, h5py.Dataset):
        raise IlpParsingError(f"Expected dataset at '{key}', found {dataset.__class__.__name__}")
    return dataset

def ensure_int(group: h5py.Group, key: str) -> int:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('int64')
    if dataset.shape != () or dataset.dtype != expected_dtype:
        raise IlpTypeMismatch(
            key=key, expected_dtype=expected_dtype, expected_shape=(), dataset=dataset
        )
    return int(dataset[()])

def ensure_bool(group: h5py.Group, key: str) -> bool:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('bool')
    if dataset.shape != () or dataset.dtype != expected_dtype:
        raise IlpTypeMismatch(
            key=key, expected_dtype=expected_dtype, expected_shape=(), dataset=dataset
        )
    return bool(dataset[()])

def ensure_int_tuple(group: h5py.Group, key: str) -> Tuple[int, ...]:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('int64')
    if len(dataset.shape) != 1 or dataset.dtype != expected_dtype:
        raise IlpParsingError(f"Expected {key} to be a Tuple[int, ...], found {dataset.dtype} {dataset.shape}")
    return tuple(dataset[()])

def ensure_drange(group: h5py.Group, key: str) -> "Tuple[int, int] | Tuple[float, float]":
    dataset = ensure_dataset(group, key)
    if len(dataset.shape) == 2 and (dataset.dtype == np.dtype("int64") or dataset.dtype == np.dtype("float32")):
        return tuple(dataset[()])
    raise IlpParsingError(f"Expected {key} to be a Tuple[Number, Number], found {dataset.dtype} {dataset.shape}")

def ensure_bytes(group: h5py.Group, key: str) -> bytes:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('object')
    if dataset.shape != () or dataset.dtype != expected_dtype:
        raise IlpTypeMismatch(
            key=key, expected_dtype=expected_dtype, expected_shape=(), dataset=dataset
        )
    contents = dataset[()]
    if not isinstance(contents, bytes):
        raise IlpParsingError(f"Expected bytes at {key}, found {contents.__class__.__name__}")
    return contents

def ensure_encoded_string(group: h5py.Group, key: str) -> str:
    return ensure_bytes(group, key).decode("utf8")

T = TypeVar("T")

def ensure_optional(ensurer: Callable[[h5py.Group, str], T], group: h5py.Group, key: str) -> "T | None":
    if key not in group:
        return None
    return ensurer(group, key)

def populate_h5_group(group: h5py.Group, data: IlpGroup) -> None:
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, AbcMapping):
            subgroup = group.create_group(key)
            populate_h5_group(subgroup, value)
            continue
        if isinstance(value, IlpAttrDataset):
            h5_value = value.value
        else:
            h5_value = value

        if isinstance(h5_value, np.ndarray):
            dataset = group.create_dataset(key, data=h5_value, compression="gzip")
        else:
            dataset = group.create_dataset(key, data=h5_value)

        if isinstance(value, IlpAttrDataset):
            for attr_key, attr_value in value.attrs.items():
                dataset.attrs[attr_key] = attr_value

def read_h5_group(group: h5py.Group) -> IlpGroup:
    out: IlpGroup = {}
    for key, value in group.items():
        if isinstance(value, h5py.Group):
            out[key] = read_h5_group(value)
        elif isinstance(value, Datatype):
            print(f"Warning: unexpected Datatype with key {key}")
        else:
            out[key] = read_h5_dataset(value)
    return out

def read_h5_dataset(dataset: h5py.Dataset) -> IlpDatasetValue:
    value = dataset[()]
    if len(dataset.attrs.keys()) > 0:
        loaded_attrs: Mapping[str, Any] = {k: v for k, v in dataset.attrs.items()}
        return IlpAttrDataset(value=value, attrs=loaded_attrs)
    return value

class IlpProject(ABC):
    def __init__(
        self,
        *,
        workflowName: str,
        currentApplet: "int | None" = None,
        ilastikVersion: "str | None" = None,
        time: "datetime | None" = None,
    ) -> None:
        self.workflowName: str = workflowName
        self.currentApplet: int = currentApplet or 0
        self.ilastikVersion: str = ilastikVersion or '1.4.0b28.dev14+gb5bb2750d' #FIXME: maybe use a different version
        self.time: datetime = time or datetime.now()
        super().__init__()

    def populate_group(self, group: h5py.Group):
        group["currentApplet"] =  self.currentApplet
        group["ilastikVersion"] =  self.ilastikVersion.encode("utf8")  # FIXM
        group["time"] =  self.time.ctime().encode("utf8")
        group["workflowName"] =  self.workflowName.encode("utf8")

class IlpDatasetDisplayMode(enum.Enum):
    DEFAULT = "default"
    GRAYSCALE = "grayscale"
    RGBA = "rgba"
    RANDOM_COLORTABLE = "random-colortable"
    BINARY_MASK = "binary-mask"

    def to_ilp_data(self) -> bytes:
        return self.value.encode("utf8")

    @classmethod
    def from_ilp_data(cls, value: bytes) -> "IlpDatasetDisplayMode":
        value_str = value.decode("utf8")
        for display_mode in IlpDatasetDisplayMode:
            if display_mode.value == value_str:
                return display_mode
        raise IlpParsingError(f"Can't parse {value_str} as {cls.__name__}")

class IlpDatasetInfoLocation(enum.Enum):
    FILE_SYSTEM = "FileSystem"
    PROJECT_INTERNAL = "ProjectInternal"

    @classmethod
    def from_ilp_data(cls, value: bytes) -> "IlpDatasetInfoLocation":
        value_str = value.decode("utf8")
        for location in cls:
            if location.value == value_str:
                return location
        raise IlpParsingError(f"Can't parse {value} as {cls.__name__}")

    def to_ilp_data(self) -> bytes:
        return self.value.encode("utf8")

class IlpInfoClassName(enum.Enum):
    URL_DATASET_INFO = "UrlDatasetInfo"
    FILESYSTEM_DATASET_INFO = "FilesystemDatasetInfo"
    RELATIVE_FILESYSTEM_DATASET_INFO = "RelativeFilesystemDatasetInfo"
    PRELOADED_ARRAY_DATASET_INFO = "PreloadedArrayDatasetInfo"

    @classmethod
    def from_url(cls, url: Url) -> "IlpInfoClassName":
        if url.protocol == Protocol.HTTP or url.protocol == Protocol.HTTPS:
            return cls.URL_DATASET_INFO
        if url.protocol == Protocol.FILE:
            return cls.FILESYSTEM_DATASET_INFO
        else:
            return cls.PRELOADED_ARRAY_DATASET_INFO

    @classmethod
    def from_ilp_data(cls, value: bytes) -> "IlpInfoClassName":
        value_str = value.decode("utf8")
        for info_class in cls:
            if info_class.value == value_str:
                return info_class
        raise IlpParsingError(f"Can't parse {value} as {cls.__name__}")

    def to_ilp_data(self) -> bytes:
        return self.value.encode("utf8")


class IlpDatasetInfo:
    def __init__(
        self,
        *,
        allowLabels: "bool | None",
        axistags: AxisTags,
        datasetId: "None | uuid.UUID",
        filePath: str,
        nickname: str,
        fromstack: "bool | None",
        location: IlpDatasetInfoLocation,
        klass: IlpInfoClassName,
        shape: Tuple[int, ...],
        display_mode: "IlpDatasetDisplayMode | None",
        normalizeDisplay: "bool | None",
        drange: "Tuple[int, int] | Tuple[float, float] | None",
    ):
        self.allowLabels: bool = True if allowLabels is None else allowLabels
        self.axistags: AxisTags = axistags
        self.nickname: str = nickname
        self.fromstack: bool = True if fromstack is None else fromstack
        self.location = location
        self.klass = klass
        self.datasetId: uuid.UUID = datasetId or uuid.uuid1()
        self.filePath = filePath
        self.shape = shape
        self.display_mode: IlpDatasetDisplayMode = display_mode or IlpDatasetDisplayMode.DEFAULT
        self.normalizeDisplay: bool = (drange is not None) if normalizeDisplay is None else normalizeDisplay
        self.drange: "Tuple[int, int] | Tuple[float, float] | None" = drange
        super().__init__()

    @classmethod
    def from_datasource(
        cls,
        *,
        datasource: FsDataSource,
        allowLabels: "bool | None" = None,
        datasetId: "uuid.UUID | None" = None,
        nickname: "str | None" = None,
        fromstack: "bool | None" = None,
        display_mode: "IlpDatasetDisplayMode | None" = None,
        normalizeDisplay: "bool | None" = None,
        drange: "Tuple[int, int] | Tuple[float, float] | None" = None,

   ) -> "IlpDatasetInfo":
        return IlpDatasetInfo(
            allowLabels=allowLabels,
            axistags=vigra.defaultAxistags(datasource.c_axiskeys_on_disk),
            datasetId=datasetId,
            filePath=datasource.url.to_ilp_info_filePath(),
            nickname=nickname or datasource.url.path.name,
            fromstack=fromstack,
            location=IlpDatasetInfoLocation.FILE_SYSTEM,
            klass=IlpInfoClassName.from_url(datasource.url),
            shape=datasource.shape.to_tuple(datasource.c_axiskeys_on_disk),
            display_mode=display_mode,
            normalizeDisplay=normalizeDisplay,
            drange=drange,
        )

    def populate_group(self, group: h5py.Group) -> None:
        group["axistags"] = self.axistags.toJSON().encode("utf8")
        group["shape"] = self.shape
        group["allowLabels"] = self.allowLabels
        # subvolume_roi FIXME
        group["display_mode"] = self.display_mode.to_ilp_data()
        group["nickname"] = self.nickname.encode("utf8")
        group["normalizeDisplay"] = self.normalizeDisplay
        if self.drange:
            group["drange"] = self.drange
        group["location"] = self.location.to_ilp_data()
        group["__class__"] = self.klass.to_ilp_data()
        group["filePath"] = self.filePath.encode("utf8")
        group["datasetId"] = str(self.datasetId).encode("utf8")

        group["axisorder"] = "".join(self.axistags.keys()).encode("utf8")
        group["fromstack"] = self.fromstack # FIXME?

    @classmethod
    def from_ilp_data(cls, group: h5py.Group) -> "IlpDatasetInfo":
        return IlpDatasetInfo(
            allowLabels=ensure_bool(group, "allowLabels"),
            axistags=vigra.AxisTags.fromJSON(ensure_encoded_string(group, "axistags")),
            datasetId=uuid.UUID(ensure_encoded_string(group, "datasetId")),
            filePath=ensure_encoded_string(group, "filePath"),
            fromstack=ensure_bool(group, "fromstack"),
            location=IlpDatasetInfoLocation.from_ilp_data(ensure_bytes(group, "location")),
            klass=IlpInfoClassName.from_ilp_data(ensure_bytes(group, "__class__")), # FIXME: optional?
            nickname=ensure_encoded_string(group, "nickname"),
            shape=ensure_int_tuple(group, "shape"),
            display_mode=IlpDatasetDisplayMode.from_ilp_data(ensure_bytes(group, "display_mode")),
            normalizeDisplay=ensure_optional(ensure_bool, group, "normalizeDisplay"),
            drange=ensure_optional(ensure_drange, group, "drange")
        )

    def try_to_datasource(
        self,
        *,
        ilp_fs: JsonableFilesystem,
        ilp_base_path: Path,
        allowed_protocols: Sequence[Protocol] = (Protocol.HTTP, Protocol.HTTPS)
    ) -> "FsDataSource | UsageError":
        url = Url.parse(self.filePath)
        if url is None:
            abs_path = ilp_base_path.joinpath(self.filePath)
            url = Url.parse_or_raise(ilp_fs.geturl(abs_path.as_posix()))
        datasources_result = try_get_datasources_from_url(url=url, allowed_protocols=allowed_protocols)
        if isinstance(datasources_result, UsageError):
            return datasources_result
        assert len(datasources_result) == 1
        return datasources_result[0]


class IlpLane: #FIXME: generic over TypeVarTuple(..., bound=Literal["Raw Data", "Prediciton Mask", ...])
    def __init__(self, roles: Mapping[str, "IlpDatasetInfo | None"]) -> None:
        self.roles = roles
        super().__init__()

    @property
    def Role_Names(self) -> "ndarray[Any, Any]":
        role_names: "ndarray[Any, Any]" = np.asarray([name.encode("utf8") for name in self.roles.keys()]) # pyright: ignore [reportUnknownMemberType]
        return role_names

    def populate_group(self, group: h5py.Group):
        for role_name, role_datasouce in self.roles.items():
            role_group = group.create_group(role_name)
            if role_datasouce is not None:
                role_datasouce.populate_group(role_group)

class IlpInputDataGroup:
    def __init__(self, lanes: Sequence[IlpLane]) -> None:
        self.lanes = lanes
        super().__init__()

    def populate_group(self, group: h5py.Group):
        group["Role Names"] = self.lanes[0].Role_Names
        group["StorageVersion"] = "0.2"

        infos_group = group.create_group("infos")
        for lane_index, lane in enumerate(self.lanes):
            lane.populate_group(infos_group.create_group(f"lane{lane_index:04}"))

        _ = group.create_group("local_data")

class IlpFeatureSelectionsGroup:
    all_feature_names: ClassVar[Sequence[str]] = [
        "GaussianSmoothing",
        "LaplacianOfGaussian",
        "GaussianGradientMagnitude",
        "DifferenceOfGaussians",
        "StructureTensorEigenvalues",
        "HessianOfGaussianEigenvalues",
    ]

    def __init__(self, feature_extractors: Sequence[IlpFilter]) -> None:
        self.feature_extractors = feature_extractors
        super().__init__()

    def populate_group(self, group: h5py.Group):
        if len(self.feature_extractors) == 0:
            return

        group["FeatureIds"] = np.asarray([ # pyright: ignore [reportUnknownMemberType]
            name.encode("utf8") for name in self.all_feature_names
        ])

        default_scales = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]
        extra_scales = set(fe.ilp_scale for fe in self.feature_extractors if fe.ilp_scale not in default_scales)
        scales = default_scales + sorted(extra_scales)
        group["Scales"] = np.asarray(scales) # pyright: ignore [reportUnknownMemberType]

        SelectionMatrix: "ndarray[Any, Any]" = np.zeros((len(self.all_feature_names), len(scales)), dtype=bool) # pyright: ignore [reportUnknownMemberType]
        for fe in self.feature_extractors:
            name_idx = self.all_feature_names.index(fe.__class__.__name__)
            scale_idx = scales.index(fe.ilp_scale)
            SelectionMatrix[name_idx, scale_idx] = True

        ComputeIn2d: "ndarray[Any, Any]" = np.full(len(scales), True, dtype=bool) # pyright: ignore [reportUnknownMemberType]
        for idx, fname in enumerate(self.all_feature_names):
            ComputeIn2d[idx] = all(fe.axis_2d for fe in self.feature_extractors if fe.__class__.__name__ == fname)

        group["SelectionMatrix"] = SelectionMatrix
        group["ComputeIn2d"] = ComputeIn2d  # [: len(scales)]  # weird .ilp quirk in featureTableWidget.py:524
        group["StorageVersion"] = "0.1"
