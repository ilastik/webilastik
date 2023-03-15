#pyright: strict

from datetime import datetime
from abc import ABC
from pathlib import PurePosixPath
from typing import Callable, ClassVar, Any, Dict, List, Mapping, Sequence, Tuple, Type, TypeVar, cast
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
from webilastik.annotations.annotation import Color
from webilastik.datasource import FsDataSource
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians, IlpGaussianGradientMagnitude, IlpGaussianSmoothing, IlpHessianOfGaussianEigenvalues,
    IlpLaplacianOfGaussian, IlpStructureTensorEigenvalues
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem import IFilesystem
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.utility.url import Url


DT = TypeVar("DT", np.float64, np.int64, np.bool_, np.object_)

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

def ensure_group(group: h5py.Group, key: str) -> h5py.Group:
    if key not in group:
        raise IlpMissingKey(key)
    inner_group = group[key]
    if not isinstance(inner_group, h5py.Group):
        raise IlpParsingError(f"Expected dataset at '{key}', found {inner_group.__class__.__name__}")
    return inner_group

def ensure_dataset(group: h5py.Group, key: str) -> h5py.Dataset:
    if key not in group:
        raise IlpMissingKey(key)
    dataset = group[key]
    if not isinstance(dataset, h5py.Dataset):
        raise IlpParsingError(f"Expected dataset at '{group.name}/{key}', found {dataset.__class__.__name__}")
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

def ensure_ndarray(group: h5py.Group, key: str, expected_shape: Tuple[int, ...], expected_dtype: "np.dtype[DT]") -> "np.ndarray[Any, np.dtype[DT]]":
    dataset = ensure_dataset(group, key)
    if dataset.dtype != expected_dtype or dataset.shape != expected_shape:
        raise IlpTypeMismatch(key=key, expected_dtype=expected_dtype, expected_shape=expected_shape, dataset=dataset)
    contents = dataset[()]
    if not isinstance(contents, np.ndarray):
        raise IlpParsingError(f"Expected ndarray at {key}, found {contents.__class__.__name__}")
    return contents

def ensure_scalar(group: h5py.Group, key: str, expected_dtype: "np.dtype[DT]") -> "DT":
    dataset = ensure_dataset(group, key)
    if dataset.dtype != expected_dtype or dataset.shape != ():
        raise IlpTypeMismatch(key=key, expected_dtype=expected_dtype, expected_shape=(), dataset=dataset)
    contents = dataset[()]
    if not isinstance(contents, expected_dtype.type):
        raise IlpParsingError(f"Expected a {expected_dtype} scalar at {key}, found {contents.__class__.__name__}")
    return contents

def ensure_list(group: h5py.Group, key: str, expected_dtype: "np.dtype[DT]") -> Sequence["DT"]:
    dataset = ensure_dataset(group, key)
    if dataset.dtype != expected_dtype or len(dataset.shape) != 1:
        raise IlpParsingError(f"Expected {key} tp be list of {expected_dtype}, found {dataset}")
    contents = dataset[()]
    if not isinstance(contents, np.ndarray):
        raise IlpParsingError(f"Expected ndarray at {key}, found {contents.__class__.__name__}")
    return cast(Sequence["DT"], contents)

def ensure_encoded_string_list(group: h5py.Group, key: str) -> Sequence[str]:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('object')
    if len(dataset.shape) != 1 or dataset.dtype != expected_dtype:
        raise IlpTypeMismatch(
            key=key, expected_dtype=expected_dtype, expected_shape=(), dataset=dataset
        )
    contents = dataset[()]
    if not isinstance(contents, np.ndarray):
        raise IlpParsingError(f"Expected ndarray at {key}, found {contents.__class__.__name__}")
    return [s.decode('utf8') for s in contents]

def ensure_color_list(group: h5py.Group, key: str) -> Sequence[Color]:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('int64') # classic ilastik saves color components as int64
    if len(dataset.shape) != 2 or dataset.shape[1] != 3 or dataset.dtype != expected_dtype:
        raise IlpTypeMismatch(
            key=key, expected_dtype=expected_dtype, expected_shape=(), dataset=dataset
        )
    contents = dataset[()]
    if not isinstance(contents, np.ndarray):
        raise IlpParsingError(f"Expected ndarray at {key}, found {contents.__class__.__name__}")
    return [
        Color(r=np.uint8(c[0]), g=np.uint8(c[1]), b=np.uint8(c[2])) for c in contents
    ]

def ensure_float_list(group: h5py.Group, key: str) -> Sequence[float]:
    dataset = ensure_dataset(group, key)
    expected_dtype = np.dtype('float64')
    if len(dataset.shape) != 1 or dataset.dtype != expected_dtype:
        raise IlpParsingError(f"Expected {key} to be a  Sequence[int, ...] of float64, found {dataset.dtype} {dataset.shape}")
    return [float(item) for item in tuple(dataset[()])]



T = TypeVar("T")

def ensure_optional(ensurer: Callable[[h5py.Group, str], T], group: h5py.Group, key: str) -> "T | None":
    if key not in group:
        return None
    return ensurer(group, key)

def populate_h5_group(group: h5py.Group, data: IlpGroup) -> None:
    for key, value in data.items():
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
        if url.protocol == "http" or url.protocol == "https":
            return cls.URL_DATASET_INFO
        if url.protocol == "file":
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

        # group["axisorder"] = "".join(self.axistags.keys()).encode("utf8")

    @classmethod
    def parse(cls, group: h5py.Group) -> "IlpDatasetInfo":
        return IlpDatasetInfo(
            allowLabels=ensure_bool(group, "allowLabels"),
            axistags=vigra.AxisTags.fromJSON(ensure_encoded_string(group, "axistags")),
            datasetId=uuid.UUID(ensure_encoded_string(group, "datasetId")),
            filePath=ensure_encoded_string(group, "filePath"),
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
        ilp_fs: IFilesystem,
        ilp_path: PurePosixPath,
    ) -> "FsDataSource | Exception":
        url = Url.parse(self.filePath)
        if url is None: # filePath was probably a path, not an URL
            path = ilp_path.parent.joinpath(self.filePath)
            url = ilp_fs.geturl(path)
        # import pydevd; pydevd.settrace()
        datasources_result = try_get_datasources_from_url(url=url)
        if datasources_result is None:
            return Exception(f"Could not open {url} as a data source: unsupported format")
        if isinstance(datasources_result, Exception):
            return Exception(f"Could not open {url} as a data source: {datasources_result}")
        if isinstance(datasources_result, tuple):
            if len(datasources_result) != 1:
                return Exception(f"Expected a single datasource from {url}, found {len(datasources_result)}")
            return datasources_result[0]
        else:
            return datasources_result


class IlpLane: #FIXME: generic over TypeVarTuple(..., bound=Literal["Raw Data", "Prediciton Mask", ...])
    def __init__(self, roles: Mapping[str, "IlpDatasetInfo | None"]) -> None:
        self.roles = roles
        super().__init__()

    @property
    def Role_Names(self) -> "List[bytes]":
        return [name.encode("utf8") for name in self.roles.keys()]

    def populate_group(self, group: h5py.Group):
        for role_name, role_datasouce in self.roles.items():
            role_group = group.create_group(role_name) # empty roles still show up in the .ilp
            if role_datasouce is not None:
                role_datasouce.populate_group(role_group)

    @classmethod
    def parse(cls, group: h5py.Group, role_names: Sequence[str]) -> "IlpLane":
        roles: Dict[str, "IlpDatasetInfo | None"] = {}
        for role_name in role_names:
            if role_name not in group:
                roles[role_name] = None
                continue
            info_group = ensure_group(group, role_name)
            if len(info_group.keys()) == 0:
                roles[role_name] = None
                continue
            roles[role_name] = IlpDatasetInfo.parse(info_group)
        return IlpLane(roles=roles)


class IlpInputDataGroup:
    def __init__(self, lanes: Sequence[IlpLane]) -> None:
        self.lanes = lanes
        super().__init__()

    def populate_group(self, group: h5py.Group):
        group["Role Names"] = ["Raw Data".encode("utf8"), "Prediciton Mask".encode("utf8")] # FIXME! what about other workflows?
        group["StorageVersion"] = "0.2"

        infos_group = group.create_group("infos")
        for lane_index, lane in enumerate(self.lanes):
            lane.populate_group(infos_group.create_group(f"lane{lane_index:04}"))

        _ = group.create_group("local_data")

    @classmethod
    def parse(cls, group: h5py.Group) -> "IlpInputDataGroup":
        RoleNames = ensure_encoded_string_list(group, "Role Names")
        expected_storage_version = "0.2"
        found_storage_version = ensure_encoded_string(group, "StorageVersion")
        if found_storage_version != expected_storage_version:
            raise IlpParsingError(f"Expected {group.name}/StorageVersion to be {expected_storage_version}, found {found_storage_version}")
        infos = ensure_group(group, "infos")
        group.file
        return IlpInputDataGroup(
            lanes=[
                IlpLane.parse(group=ensure_group(infos, lane_name), role_names=RoleNames) for lane_name in infos.keys()
            ]
        )

    @classmethod
    def find_and_parse(cls, h5_file: h5py.File) -> "IlpInputDataGroup":
        return cls.parse(ensure_group(h5_file, "Input Data"))

    def try_to_datasources(
        self,
        *,
        role_name: str,
        ilp_fs: IFilesystem,
        ilp_path: PurePosixPath,
    ) -> "Dict[int, 'FsDataSource | None'] | Exception":
        infos = [lane.roles[role_name] for lane in self.lanes]
        raw_data_datasources: Dict[int, "FsDataSource | None"] = {}
        for lane_index, info in enumerate(infos):
            if info is None:
                raw_data_datasources[lane_index] = None
            else:
                datasource_result = info.try_to_datasource(ilp_fs=ilp_fs, ilp_path=ilp_path)
                if isinstance(datasource_result, Exception):
                    return datasource_result
                raw_data_datasources[lane_index] = datasource_result
        return raw_data_datasources

class IlpFeatureSelectionsGroup:
    named_feature_classes: ClassVar[Mapping[str, Type[IlpFilter]]] = {
        "GaussianSmoothing": IlpGaussianSmoothing,
        "LaplacianOfGaussian": IlpLaplacianOfGaussian,
        "GaussianGradientMagnitude": IlpGaussianGradientMagnitude,
        "DifferenceOfGaussians": IlpDifferenceOfGaussians,
        "StructureTensorEigenvalues": IlpStructureTensorEigenvalues,
        "HessianOfGaussianEigenvalues": IlpHessianOfGaussianEigenvalues,
    }
    feature_names: ClassVar[Sequence[str]] = list(named_feature_classes.keys())
    feature_classes: ClassVar[Sequence[Type[IlpFilter]]] = list(named_feature_classes.values())

    def __init__(self, feature_extractors: Sequence[IlpFilter]) -> None:
        self.feature_extractors = feature_extractors
        super().__init__()

    def populate_group(self, group: h5py.Group):
        if len(self.feature_extractors) == 0:
            return

        group["FeatureIds"] = [name.encode("utf8") for name in self.feature_names]

        default_scales = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]
        extra_scales = set(fe.ilp_scale for fe in self.feature_extractors if fe.ilp_scale not in default_scales)
        scales = default_scales + sorted(extra_scales)
        group["Scales"] = np.asarray(scales)

        SelectionMatrix: "ndarray[Any, Any]" = np.zeros((len(self.feature_classes), len(scales)), dtype=bool)
        for fe in self.feature_extractors:
            name_idx = self.feature_classes.index(fe.__class__)
            scale_idx = scales.index(fe.ilp_scale)
            SelectionMatrix[name_idx, scale_idx] = True

        ComputeIn2d: "ndarray[Any, Any]" = np.full(len(scales), True, dtype=bool)
        for idx, fname in enumerate(self.feature_classes):
            ComputeIn2d[idx] = all(fe.axis_2d for fe in self.feature_extractors if fe.__class__.__name__ == fname)

        group["SelectionMatrix"] = SelectionMatrix
        group["ComputeIn2d"] = ComputeIn2d  # [: len(scales)]  # weird .ilp quirk in featureTableWidget.py:524
        group["StorageVersion"] = "0.1"

    @classmethod
    def parse(cls, group: h5py.Group) -> "IlpFeatureSelectionsGroup":
        if len(group.keys()) == 0:
            return IlpFeatureSelectionsGroup(feature_extractors=[])
        FeatureIds = ensure_encoded_string_list(group, "FeatureIds")
        Scales = ensure_list(group, key="Scales", expected_dtype=np.dtype("float64"))
        SelectionMatrix = ensure_ndarray(
            group, key="SelectionMatrix", expected_shape=(len(FeatureIds), len(Scales)), expected_dtype=np.dtype("bool")
        )
        ComputeIn2d = ensure_list(group, key="ComputeIn2d", expected_dtype=np.dtype("bool"))
        # if len(ComputeIn2d) != len(FeatureIds):
            # raise IlpParsingError(f"FeatureIds has different length from ComputeIn2D")
        StorageVersion = ensure_encoded_string(group, key="StorageVersion")
        if StorageVersion != "0.1":
            raise IlpParsingError(f"Unexpected storage version on {group.name}: {StorageVersion}")

        feature_extractors: List[IlpFilter] = []
        for feature_name_index, feature_name in enumerate(FeatureIds):
            for scale_index, scale in enumerate(Scales):
                if not SelectionMatrix[feature_name_index][scale_index]:
                    continue
                feature_class = cls.named_feature_classes.get(feature_name)
                if feature_class is None:
                    raise IlpParsingError(f"Bad entry in {group.name}/FeatureIds: {feature_name}")
                feature_extractors.append(feature_class(
                    ilp_scale=float(scale),
                    axis_2d="z" if ComputeIn2d[feature_name_index] else None, #FIXME: always z?
                ))
        return IlpFeatureSelectionsGroup(feature_extractors=feature_extractors)