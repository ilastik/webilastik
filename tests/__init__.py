from datetime import datetime
import os
from pathlib import Path, PurePosixPath
import time
from typing import Any, Dict, Literal, Mapping, Dict, Sequence
import uuid
import json
from collections.abc import Mapping as MappingAbc

import h5py
from h5py import AttributeManager

from ndstructs.point5D import Point5D, Shape5D
import numpy as np
from ndstructs.utils.json_serializable import JsonObject, JsonValue

from webilastik.annotations.annotation import Annotation, Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink import FsDataSink
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksScaleSink
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksScale, RawEncoder
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.features.ilp_filter import IlpGaussianSmoothing, IlpHessianOfGaussianEigenvalues
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem import JsonableFilesystem
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.osfs import OsFs
from webilastik.libebrains.user_token import UserToken
from webilastik.ui.applet.brushing_applet import Label

def get_project_root_dir() -> Path:
    return Path(__name__).parent

def get_tmp_dir() -> Path:
    return Path(__name__) / "tmp"

def get_sample_c_cells_datasource() -> SkimageDataSource:
    return SkimageDataSource(
        filesystem=OsFs(get_project_root_dir().as_posix()), path=PurePosixPath("public/images/c_cells_1.png")
    )

def get_test_output_osfs() -> OsFs:
    test_dir_path = get_tmp_dir() / f"test-{time.monotonic()}/"
    os.makedirs(test_dir_path, exist_ok=True)
    return OsFs(str(test_dir_path))

def get_test_output_bucket_fs() -> BucketFs:
    now = datetime.now()
    now_str = f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"
    return BucketFs(
        bucket_name="hbp-image-service",
        prefix=PurePosixPath(f"/test-{now_str}"),
        ebrains_user_token=UserToken.get_global_token_or_raise(),
    )

def create_precomputed_chunks_sink(*, shape: Shape5D, dtype: "np.dtype[Any]", chunk_size: Shape5D, fs: "JsonableFilesystem | None" = None) -> FsDataSink:
    return PrecomputedChunksScaleSink(
        filesystem=fs or get_test_output_osfs(),
        info_dir=PurePosixPath(f"{uuid.uuid4()}.precomputed"),
        dtype=dtype,
        num_channels=shape.c,
        scale=PrecomputedChunksScale(
            key=PurePosixPath("some_data"),
            size=(shape.x, shape.y, shape.z),
            resolution=(1,1,1),
            voxel_offset=(0,0,0),
            chunk_sizes=tuple([
                (chunk_size.x, chunk_size.y, chunk_size.z)
            ]),
            encoding=RawEncoder(),
        )
    )

def get_sample_c_cells_pixel_annotations() -> Sequence[Label]:
    raw_data_source = get_sample_c_cells_datasource()
    return [
        Label(
            name="Foreground",
            color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
            annotations=[
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
                    raw_data=raw_data_source
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
                    raw_data=raw_data_source
                ),
            ]
        ),
        Label(
            name="Background",
            color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
            annotations=[
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
                    raw_data=raw_data_source
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
                    raw_data=raw_data_source
                ),
            ]
        ),
    ]

def get_sample_feature_extractors() -> Sequence[IlpFilter]:
    return (
        IlpGaussianSmoothing(ilp_scale=0.3, axis_2d="z"),
        IlpGaussianSmoothing(ilp_scale=0.7, axis_2d="z"),
        IlpGaussianSmoothing(ilp_scale=1.0, axis_2d="z"),
        IlpGaussianSmoothing(ilp_scale=1.6, axis_2d="z"),
        IlpGaussianSmoothing(ilp_scale=3.5, axis_2d="z"),
        IlpGaussianSmoothing(ilp_scale=5.0, axis_2d="z"),
        IlpGaussianSmoothing(ilp_scale=10.0, axis_2d="z"),
        IlpHessianOfGaussianEigenvalues(ilp_scale=0.7, axis_2d="z"),
    )

def get_sample_c_cells_pixel_classifier() -> VigraPixelClassifier[IlpFilter]:
    classifier_result = VigraPixelClassifier.train(
        feature_extractors=get_sample_feature_extractors(),
        label_classes=[label.annotations for label in get_sample_c_cells_pixel_annotations()],
    )
    if isinstance(classifier_result, Exception):
        raise classifier_result
    return classifier_result



def compare_values(v1: Any, v2: Any) -> bool:
    if isinstance(v1, np.ndarray) and isinstance(v2, np.ndarray):
        return bool(np.array_equal(v1, v2))
    return bool(v1 == v2)

def strip_json_obj(obj: JsonObject) -> JsonObject:
    out: Dict[str, JsonValue] = {}
    for k, v in obj.items():
        if isinstance(v, MappingAbc):
            v = strip_json_obj(v)
        if v in (True, None, {}):
            continue
        if k.startswith("Forest"):
            continue #FIXME!!!!!!!!!!!!!!
        out[k] = v
    return out

class AttrComparison:
    comparisons: Mapping[str, bool]

    def __init__(self, attrs1: AttributeManager, attrs2: AttributeManager):
        super().__init__()
        comparisons: Dict[str, bool] = {}
        for key in set(list(attrs1.keys()) + list(attrs2.keys())):
            if key not in attrs1 or key not in attrs2:
                comparisons[key] = False
                continue
            val1 = attrs1[key]
            val2 = attrs2[key]
            comparisons[key] = compare_values(val1, val2)
        self.comparisons = comparisons

    def to_json_data(self) -> JsonValue:
        return self.comparisons

class DatasetComparison:
    attributes_comparison: AttrComparison
    data_comparison: bool

    def __init__(self,ds1: h5py.Dataset, ds2: h5py.Dataset) -> None:
        super().__init__()
        data1 = ds1[()]
        data2 = ds2[()]
        self.attributes_comparison = AttrComparison(ds1.attrs, ds2.attrs)
        self.data_comparison = compare_values(data1, data2)

    def to_json_data(self) -> JsonValue:
        return {
            "attributes_comparison": self.attributes_comparison.to_json_data(),
            "data_comparison": self.data_comparison,
        }

class GroupComparison:
    attributes_comparison: AttrComparison
    member_comparisons: Mapping[str, "DatasetComparison | GroupComparison | Literal[False]"]

    def __init__(self, group1: h5py.Group, group2: h5py.Group):
        super().__init__()
        member_comparisons: Dict[str, "DatasetComparison | GroupComparison | Literal[False]"] = {}
        for key in set(list(group1.keys()) + list(group2.keys())):
            if key not in group1 or key not in group2:
                member_comparisons[key] = False
                continue
            value1 = group1[key]
            value2 = group2[key]

            if isinstance(value1, h5py.Group) and isinstance(value2, h5py.Group):
                member_comparisons[key] = GroupComparison(value1, value2)
            elif isinstance(value1, h5py.Dataset) and isinstance(value2, h5py.Dataset):
                member_comparisons[key] =  DatasetComparison(value1, value2)
            else:
                member_comparisons[key] = False
        self.attributes_comparison = AttrComparison(group1.attrs, group2.attrs)
        self.member_comparisons = member_comparisons

    def to_json_data(self) -> JsonObject:
        return {
            "attributes_comparison": self.attributes_comparison.to_json_data(),
            "member_comparisons": {
                key: value if isinstance(value, bool) else value.to_json_data()
                for key, value in self.member_comparisons.items()
            }
        }

def compare_projects(project1_path: Path, project2_path: Path):
    with h5py.File(project1_path, "r") as p1:
        with h5py.File(project2_path, "r") as p2:
            data = GroupComparison(p1, p2).to_json_data()
            stripped_data = strip_json_obj(data)
            print(json.dumps(stripped_data, indent=4))
