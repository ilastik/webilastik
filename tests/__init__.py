# pyright: strict

from datetime import datetime
import os
from pathlib import Path, PurePosixPath
import time
from typing import Any, Dict, Literal, Mapping, Sequence, Tuple
import uuid
import json
from collections.abc import Mapping as MappingAbc

import h5py
from h5py import AttributeManager

from ndstructs.point5D import Point5D, Shape5D
import numpy as np
from ndstructs.utils.json_serializable import JsonObject, JsonValue
from cryptography.fernet import Fernet


from webilastik.annotations.annotation import Annotation, Color
from webilastik.classifiers.pixel_classifier import VigraPixelClassifier
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource import FsDataSource
from webilastik.datasource.precomputed_chunks_info import RawEncoder
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.ilp_filter import IlpGaussianSmoothing, IlpHessianOfGaussianEigenvalues
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.os_fs import OsFs
from webilastik.filesystem.http_fs import HttpFs
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.ui.applet.brushing_applet import Label
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.utility import get_now_string

from webilastik.config import (
    WEBILASTIK_ALLOW_LOCAL_FS,
    WEBILASTIK_SCRATCH_DIR,
    WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS,
    WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY,
    WEBILASTIK_EXTERNAL_URL,
    EBRAINS_CLIENT_ID,
    EBRAINS_CLIENT_SECRET,
    # EBRAINS_USER_ACCESS_TOKEN,
    # EBRAINS_USER_REFRESH_TOKEN,
    WEBILASTIK_JOB_MAX_DURATION_MINUTES,
    WEBILASTIK_JOB_LISTEN_SOCKET,
    WEBILASTIK_JOB_SESSION_URL,
    WEBILASTIK_SESSION_ALLOCATOR_HOST,
    WEBILASTIK_SESSION_ALLOCATOR_USERNAME,
    WEBILASTIK_SESSION_ALLOCATOR_SOCKET_PATH,
)

os.environ[WEBILASTIK_ALLOW_LOCAL_FS] = "true"
os.environ[WEBILASTIK_SCRATCH_DIR] = "/tmp/webilastik_tests_scratch"
os.environ[WEBILASTIK_ALLOW_LOCAL_COMPUTE_SESSIONS] = "true"
os.environ[WEBILASTIK_SESSION_ALLOCATOR_FERNET_KEY] = Fernet.generate_key().decode("utf8") # dummy
os.environ[WEBILASTIK_EXTERNAL_URL] = "https://app.ilastik.org"
os.environ[EBRAINS_CLIENT_ID] = "webilastik"
os.environ[EBRAINS_CLIENT_SECRET] = "dummy_secret"
# os.environ[EBRAINS_USER_ACCESS_TOKEN] = "you can set this in your env"
# os.environ[EBRAINS_USER_REFRESH_TOKEN] = "you can set this in your env"
os.environ[WEBILASTIK_JOB_MAX_DURATION_MINUTES] = "10"
os.environ[WEBILASTIK_JOB_LISTEN_SOCKET] = "/tmp/webilastik_tests_scratch/compute_session.socket"
os.environ[WEBILASTIK_JOB_SESSION_URL] = "https://app.ilastik.org/dummy/url"
os.environ[WEBILASTIK_SESSION_ALLOCATOR_HOST] = "app.ilastik.org"
os.environ[WEBILASTIK_SESSION_ALLOCATOR_USERNAME] = "www-data"
os.environ[WEBILASTIK_SESSION_ALLOCATOR_SOCKET_PATH] = "/tmp/webilastik_tests_scratch/tunnel_to_compute_session.socket"


def get_project_root_dir() -> PurePosixPath:
    return PurePosixPath(__file__).parent.parent

def get_project_test_dir() -> PurePosixPath:
    return get_project_root_dir() / "tests"

def get_tmp_dir() -> PurePosixPath:
    return get_project_test_dir() / "tmp"

def create_tmp_dir(prefix: str) -> PurePosixPath:
    path = get_tmp_dir() / f"prefix_{uuid.uuid4()}"
    Path(path).mkdir(parents=True)
    return path

def get_sample_c_cells_datasource() -> PrecomputedChunksDataSource:
    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    ds = PrecomputedChunksDataSource.try_load(
        filesystem=fs,
        spatial_resolution=(1,1,1),
        path=PurePosixPath(get_project_root_dir()) / "public/images/c_cells_2.precomputed",
    )
    assert ds and not isinstance(ds, Exception)
    return ds
    # return SkimageDataSource(
    #     filesystem=fs, path=PurePosixPath(get_project_root_dir()) / "public/images/c_cells_1.png"
    # )

def get_sample_dzip_c_cells_datasource() -> FsDataSource:
    fs = OsFs.create()
    assert not isinstance(fs, Exception)
    datasources = try_get_datasources_from_url(
        url=fs.geturl(
            PurePosixPath(get_project_root_dir() / "public/images/c_cells_2.dzip")
        ).updated_with(hash_="level=10")
    )
    assert isinstance(datasources, tuple) and len(datasources) == 1, str(datasources)
    return datasources[0]

def get_test_output_path() -> PurePosixPath:
    test_dir_path = get_tmp_dir() / f"test-{time.monotonic()}/"
    os.makedirs(test_dir_path, exist_ok=True)
    return test_dir_path

def get_test_output_bucket_fs() -> Tuple[BucketFs, PurePosixPath]:
    now = datetime.now()
    now_str = f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"
    return (BucketFs(bucket_name="hbp-image-service"), PurePosixPath(f"/tmp/test-{now_str}"))

def create_precomputed_chunks_sink(
    *, shape: Shape5D, dtype: "np.dtype[Any]", chunk_size: Shape5D, fs: "OsFs | HttpFs | BucketFs | None" = None
) -> PrecomputedChunksSink:
    default_fs, path = get_test_output_bucket_fs()
    return PrecomputedChunksSink(
        filesystem=fs or default_fs,
        path=path / f"{get_now_string()}.precomputed",
        dtype=dtype,
        scale_key=PurePosixPath("some_data"),
        encoding=RawEncoder(),
        interval=shape.to_interval5d(),
        tile_shape=chunk_size,
        resolution=(1,1,1),
    )

def get_sample_c_cells_pixel_annotations(override_datasource: "FsDataSource | None" = None) -> Sequence[Label]:
    raw_data_source = override_datasource or get_sample_c_cells_datasource()
    return [
        Label(
            name="Foreground",
            color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
            annotations=[
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=191, y=276), Point5D.zero(x=201, y=310)],
                    raw_data=raw_data_source
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=102, y=291), Point5D.zero(x=137, y=281)],
                    raw_data=raw_data_source
                ),
            ]
        ),
        Label(
            name="Background",
            color=Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0)),
            annotations=[
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=273, y=246), Point5D.zero(x=314, y=218)],
                    raw_data=raw_data_source
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=306, y=263), Point5D.zero(x=331, y=275)],
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
    classifier_result = VigraPixelClassifier[IlpFilter].train(
        feature_extractors=get_sample_feature_extractors(),
        label_classes=[label.annotations for label in get_sample_c_cells_pixel_annotations()],
    )
    if isinstance(classifier_result, Exception):
        raise classifier_result
    return classifier_result



def compare_values(v1: Any, v2: Any) -> bool:
    if isinstance(v1, np.ndarray) and isinstance(v2, np.ndarray):
        return bool(np.array_equal(v1, v2)) # pyright: ignore [reportUnknownArgumentType]
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
