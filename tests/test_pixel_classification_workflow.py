from pathlib import Path
from typing import Tuple
from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
from webilastik.datasource.precomputed_chunks_info import PrecomputedChunksInfo, PrecomputedChunksScale, RawEncoder
from webilastik.filesystem.osfs import OsFs
from webilastik.scheduling.hashing_executor import HashingExecutor
# from webilastik.scheduling.multiprocess_runner import MultiprocessRunner
from ndstructs.point5D import Shape5D
import uuid

from ndstructs.point5D import Point5D
from webilastik.datasource import DataRoi
from webilastik.datasource import SkimageDataSource

from webilastik.annotations import Annotation, Color
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.ui.applet.datasource_batch_processing_applet import DatasourceBatchProcessingApplet
from webilastik.ui.applet.feature_selection_applet import FeatureSelectionApplet
from webilastik.ui.applet.brushing_applet import BrushingApplet
from webilastik.ui.applet.pixel_classifier_applet import PixelClassificationApplet
from webilastik.ui.applet import dummy_prompt
from webilastik.filesystem.bucket_fs import BucketFs



def test_pixel_classification_workflow(
    raw_data_source: SkimageDataSource, pixel_annotations: Tuple[Annotation, ...], bucket_fs: BucketFs
):
    brushing_applet = BrushingApplet("brushing_applet")
    feature_selection_applet = FeatureSelectionApplet("feature_selection_applet", datasources=brushing_applet.datasources)
    pixel_classifier_applet = PixelClassificationApplet(
        "pixel_classifier_applet",
        feature_extractors=feature_selection_applet.feature_extractors,
        annotations=brushing_applet.annotations
    )
    batch_applet = DatasourceBatchProcessingApplet(
        name="batch applet",
        executor=HashingExecutor(max_workers=8, name="batch executor"),
        operator=pixel_classifier_applet.pixel_classifier
    )

    # GUI creates some feature extractors
    _ = feature_selection_applet.add_feature_extractors(
        dummy_prompt,
        [
            GaussianSmoothing.from_ilp_scale(scale=0.3, axis_2d="z"),
            HessianOfGaussianEigenvalues.from_ilp_scale(scale=0.7, axis_2d="z"),
        ],
    )
    assert len(feature_selection_applet.feature_extractors()) == 2

    # GUI creates some annotations
    _ = brushing_applet.add_annotations(
        dummy_prompt,
        pixel_annotations,
    )

    classifier = pixel_classifier_applet.pixel_classifier()
    assert classifier != None
    executor = batch_applet.executor


    # calculate predictions on the entire data source
    preds_future = executor.submit(classifier.compute, raw_data_source.roi)
    preds_future.result().as_uint8().show_channels()

    # calculate predictions on just a piece of arbitrary data
    exported_tile = executor.submit(classifier.compute, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    exported_tile.result().show_channels()

    # try running an export job
    basic_pixel_classification_test_path = Path("basic_pixel_classification_test")
    sink = PrecomputedChunksSink.create(
        base_path=basic_pixel_classification_test_path,
        filesystem=bucket_fs,
        info=PrecomputedChunksInfo(
            data_type=raw_data_source.dtype,
            type_="image",
            num_channels=classifier.num_classes,
            scales=tuple([
                PrecomputedChunksScale(
                    key=Path("exported_data"),
                    size=(raw_data_source.shape.x, raw_data_source.shape.y, raw_data_source.shape.z),
                    chunk_sizes=tuple([
                        (raw_data_source.tile_shape.x, raw_data_source.tile_shape.y, raw_data_source.tile_shape.z)
                    ]),
                    encoding=RawEncoder(),
                    voxel_offset=(raw_data_source.location.x, raw_data_source.location.y, raw_data_source.location.z),
                    resolution=raw_data_source.spatial_resolution
                )
            ]),
        )
    ).scale_sinks[0]

    def on_progress(job_id: uuid.UUID, step_index: int):
        print(f"===>>> Job {job_id} completed step {step_index}")

    def on_complete(job_id: uuid.UUID):
        print(f"===>>> Job {job_id} is finished!")

    job = batch_applet.start_export_job(
        user_prompt=dummy_prompt,
        source=raw_data_source,
        sink=sink,
        on_progress=on_progress,
        on_complete=on_complete
    )

    import time
    while job.status in ("pending", "running"):
        time.sleep(1)
    assert job.status == "succeeded"


    #try removing a brush stroke
    _ = brushing_applet.remove_annotations(dummy_prompt, pixel_annotations[0:1])
    assert tuple(brushing_applet.annotations()) == tuple(pixel_annotations[1:])



    # for png_bytes in preds.to_z_slice_pngs():
    #     path = f"/tmp/junk_test_image_{uuid.uuid4()}.png"
    #     with open(path, "wb") as outfile:
    #         outfile.write(png_bytes.getbuffer())
    #     os.system(f"gimp {path}")

    executor.shutdown()