from pathlib import PurePosixPath
from tests import get_sample_c_cells_datasource
from webilastik.datasource import DataRoi
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.channelwise_fastfilters import (
    GaussianSmoothing
)
from webilastik.features.feature_extractor import FeatureExtractorCollection
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.filesystem.http_fs import HttpFs

if __name__ == "__main__":
    scales = [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0]

    # datasource = PrecomputedChunksDataSource.try_load(
    #     filesystem=BucketFs(bucket_name="quint-demo"),
    #     path=PurePosixPath("/tg-ArcSwe_mice_precomputed/hbp-00138_122_381_423_s001.precomputed"),
    #     spatial_resolution=(1,1,1),
    # )

    datasource = PrecomputedChunksDataSource.try_load(
        filesystem=HttpFs(protocol="https", hostname="app.ilastik.org", path=PurePosixPath("/public/images/")),
        path=PurePosixPath("/c_cells_2.precomputed"),
        spatial_resolution=(1,1,1),
    )

    assert not isinstance(datasource, Exception), str(datasource)
    print(datasource.interval)

    # fec = FeatureExtractorCollection(
    #     extractors=[
    #         *[GaussianSmoothing.from_ilp_scale(scale=s, axis_2d="z") for s in scales[0:1]],
    #     ]
    # )

    # _ = DataRoi(datasource=datasource, x=(512, 512 + 256), y=(512, 512 + 256), c=(0, 3)).retrieve()
    # _ = DataRoi(datasource=datasource, x=(512, 512 + 256), y=(512, 512 + 256), c=(0, 3)).retrieve()

    for roi in datasource.roi.default_split():
        print(f"Fetching {roi}")
        _ = roi.retrieve()
    for roi in datasource.roi.default_split():
        print(f"Fetching {roi}")
        _ = roi.retrieve()


    # _ = fec(DataRoi(datasource=datasource, x=(512, 512 + 256), y=(512, 512 + 256), c=(0, 3)))
    # _ = fec(DataRoi(datasource=datasource, x=(512, 512 + 256), y=(512, 512 + 256), c=(0, 3)))