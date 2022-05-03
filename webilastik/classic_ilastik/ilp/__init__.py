
#pyright: strict

# import io
from datetime import datetime
from abc import ABC
# from pathlib import Path
from typing import ClassVar, Optional, Dict, Any, Mapping, Sequence, Tuple
from collections.abc import Mapping as AbcMapping
# import pickle
from typing_extensions import TypeAlias

from h5py._hl.datatype import Datatype
# from pkg_resources import parse_version
from pkg_resources.extern.packaging.version import Version # type: ignore
import enum
import uuid
from numbers import Number
import dataclasses

import numpy as np
from numpy import ndarray
import vigra
import h5py
from ndstructs.utils.json_serializable import JsonValue, ensureJsonString
from webilastik.datasource import FsDataSource
from webilastik.features.ilp_filter import IlpFilter



IlpDatasetContents: TypeAlias = "int | bytes | str | bool | Tuple[int, ...] | ndarray[Any, Any] | np.void"

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
        self.workflowName = workflowName
        self.currentApplet = currentApplet or 0
        self.ilastikVersion = ilastikVersion or "1.3.2post1"
        self.time = time or datetime.now()
        super().__init__()

    def to_ilp_data(self) -> IlpGroup:
        return {
            "currentApplet": self.currentApplet,
            "ilastikVersion": self.ilastikVersion.encode("utf8"),  # FIXME
            "time": self.time.ctime().encode("utf8"),
            "workflowName": self.workflowName.encode("utf8"),
        }

class DisplayMode(enum.Enum):
    DEFAULT = "default"
    GRAYSCALE = "grayscale"
    RGBA = "rgba"
    RANDOM_COLORTABLE = "random-colortable"
    BINARY_MASK = "binary-mask"

    def to_json_value(self) -> str:
        return self.value

    def to_ilp_data(self) -> bytes:
        return self.value.encode("utf8")

    @classmethod
    def from_ilp_data(cls, data: bytes) -> "DisplayMode":
        data_str = data.decode("utf-8")
        return cls.from_json_value(data_str)

    @classmethod
    def from_json_value(cls, value: JsonValue) -> "DisplayMode":
        value_str = ensureJsonString(value)
        for member in cls:
            if member.value == value_str:
                return member
        raise ValueError(f"Can't deserialize value {value_str} into a {cls.__name__}")


@dataclasses.dataclass
class IlpDataSource:
    def __init__(
        self,
        *,
        datasource: FsDataSource,
        nickname: "None | str" = None,
        fromstack: bool = False,
        allowLabels: bool = True,
        datasetId: "None | uuid.UUID" = None,
        display_mode: DisplayMode = DisplayMode.DEFAULT,
        normalizeDisplay: bool = True,
        drange: Optional[Tuple[Number, Number]] = None,
    ):
        self.datasource = datasource
        self.nickname = nickname or datasource.url.path.name
        self.fromstack = fromstack
        self.allowLabels = allowLabels
        self.datasetId = datasetId or uuid.uuid1()
        self.display_mode = display_mode
        self.normalizeDisplay = normalizeDisplay
        self.drange = drange
        super().__init__()


    def to_ilp_data(self) -> IlpGroup:
        return {
            "allowLabels": True,
            "axisorder": self.datasource.c_axiskeys_on_disk.encode("utf8"),
            "axistags": vigra.defaultAxistags(self.datasource.c_axiskeys_on_disk).toJSON().encode("utf8"),
            "datasetId": str(uuid.uuid1()).encode("utf8"),
            "dtype": str(self.datasource.dtype).encode("utf8"),
            "filePath": self.datasource.url.to_ilp_filename().encode("utf8"),
            "fromstack": self.fromstack,
            "location": "FileSystem".encode("utf8"), #FIXME?
            "nickname": self.nickname.encode("utf8"),
            "shape": self.datasource.shape.to_tuple(self.datasource.c_axiskeys_on_disk),
            "display_mode": self.display_mode.to_ilp_data(),
            "normalizeDisplay": self.normalizeDisplay,
            "drange": self.drange,
        }

class IlpLane: #FIXME: generic over TypeVarTuple(..., bound=Literal["Raw Data", "Prediciton Mask", ...])
    def __init__(self, roles: Mapping[str, IlpDataSource]) -> None:
        self.roles = roles
        super().__init__()

    @property
    def Role_Names(self) -> "ndarray[Any, Any]":
        role_names: "ndarray[Any, Any]" = np.asarray([name.encode("utf8") for name in self.roles.keys()]) # pyright: ignore [reportUnknownMemberType]
        return role_names

    def to_ilp_info(self) -> IlpGroup:
        return {
            role_name: role_datasouce.to_ilp_data() for role_name, role_datasouce in self.roles.items()
        }

class IlpInputDataGroup:
    def __init__(self, lanes: Sequence[IlpLane]) -> None:
        self.lanes = lanes
        super().__init__()

    def to_ilp_data(self) -> IlpGroup:
        return {
            "Role Names": self.lanes[0].Role_Names,
            "StorageVersion": b'0.2',
            "infos": {
                f"lane{lane_index:04}": lane.to_ilp_info() for lane_index, lane in enumerate(self.lanes)
            },
            "local_data": {},
        }

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

    def to_ilp_data(self) -> IlpGroup:
        if len(self.feature_extractors) == 0:
            return {}

        out: Dict[str, IlpValue] = {}
        out["FeatureIds"] = np.asarray([ # pyright: ignore [reportUnknownMemberType]
            name.encode("utf8") for name in self.all_feature_names
        ])

        default_scales = [0.3, 0.7, 1.0, 1.6, 3.5, 6.0, 10.0]
        extra_scales = set(fe.ilp_scale for fe in self.feature_extractors if fe.ilp_scale not in default_scales)
        scales = default_scales + sorted(extra_scales)
        out["Scales"] = np.asarray(scales) # pyright: ignore [reportUnknownMemberType]

        SelectionMatrix: "ndarray[Any, Any]" = np.zeros((len(self.all_feature_names), len(scales)), dtype=bool) # pyright: ignore [reportUnknownMemberType]
        for fe in self.feature_extractors:
            name_idx = self.all_feature_names.index(fe.__class__.__name__)
            scale_idx = scales.index(fe.ilp_scale)
            SelectionMatrix[name_idx, scale_idx] = True

        ComputeIn2d: "ndarray[Any, Any]" = np.full(len(scales), True, dtype=bool) # pyright: ignore [reportUnknownMemberType]
        for idx, fname in enumerate(self.all_feature_names):
            ComputeIn2d[idx] = all(fe.axis_2d for fe in self.feature_extractors if fe.__class__.__name__ == fname)

        out["SelectionMatrix"] = SelectionMatrix
        out["ComputeIn2d"] = ComputeIn2d  # [: len(scales)]  # weird .ilp quirk in featureTableWidget.py:524
        out["StorageVersion"] = "0.1"
        return out
