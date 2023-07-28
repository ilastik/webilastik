# pyright: strict

from pathlib import PurePosixPath
import time
import json
from typing import List

import numpy as np

from tests import create_precomputed_chunks_sink, get_sample_c_cells_datasource, get_sample_c_cells_pixel_annotations, get_sample_dzip_c_cells_datasource
from webilastik.classic_ilastik.ilp.pixel_classification_ilp import IlpPixelClassificationWorkflowGroup
from webilastik.datasink import FsDataSink
from webilastik.filesystem.zip_fs import ZipFs
from webilastik.datasink.deep_zoom_sink import DziLevelSink
from webilastik.datasource import DataRoi
from webilastik.features.ilp_filter import (
    IlpDifferenceOfGaussians, IlpGaussianGradientMagnitude, IlpGaussianSmoothing,
    IlpHessianOfGaussianEigenvalues, IlpLaplacianOfGaussian, IlpStructureTensorEigenvalues,
)
from webilastik.features.ilp_filter import IlpFilter
from webilastik.filesystem.os_fs import OsFs
from webilastik.scheduling.job import PriorityExecutor
from webilastik.server.rpc.dto import DziLevelSinkDto, JobCanceledDto, JobFinishedDto, JobIsPendingDto
from webilastik.ui.applet import dummy_prompt
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow
from executor_getter import get_executor

def wait_until_jobs_completed(workflow: PixelClassificationWorkflow, timeout: float = 50):
    wait_time = 0.5
    while timeout > 0:
        export_state = workflow.export_applet.get_state_dto()
        for job in export_state.jobs:
            num_args = job.num_args
            print("checkign,....")
            print(f"job {job.status=}")
            if isinstance(job.status, (JobCanceledDto, JobFinishedDto)):
                continue
            if isinstance(job.status, JobIsPendingDto):
                print(f"Some jobs still pending...")
                continue
            if job.status.num_completed_steps < (num_args or float("inf")):
                print(f"Jobs not done yet. Waiting...")
                time.sleep(wait_time)
                timeout -= wait_time
                break
        else:
            return
    raise TimeoutError("Waiting on jobs timed out!")


def test_pixel_classification_workflow():
    executor = get_executor(hint="server_tile_handler")
    priority_executor = PriorityExecutor(executor=executor, max_active_job_steps=8)

    workflow = PixelClassificationWorkflow(
        on_async_change=lambda : None, #print(json.dumps(workflow.export_applet._get_json_state(), indent=4)),
        executor=executor,
        priority_executor=priority_executor,
    )

    # GUI turns on live update
    _ = workflow.pixel_classifier_applet.set_live_update(dummy_prompt, live_update=True)

    # GUI creates some feature extractors

    all_feature_extractors: List[IlpFilter] = []
    for scale in [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0][0:3]:
        all_feature_extractors.append(IlpGaussianSmoothing(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpLaplacianOfGaussian(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpGaussianGradientMagnitude(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpDifferenceOfGaussians(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpStructureTensorEigenvalues(ilp_scale=scale, axis_2d="z"))
        all_feature_extractors.append(IlpHessianOfGaussianEigenvalues(ilp_scale=scale, axis_2d="z"))



    _ = workflow.feature_selection_applet.add_feature_extractors(
        user_prompt=dummy_prompt,
        feature_extractors=all_feature_extractors,
    )

    pixel_annotations = get_sample_c_cells_pixel_annotations(get_sample_dzip_c_cells_datasource())
    for label_name, label in zip(workflow.brushing_applet.label_names(), pixel_annotations):
        for a in label.annotations:
            result = workflow.brushing_applet.add_annotation(
                user_prompt=dummy_prompt,
                label_name=label_name,
                annotation=a,
            )
            assert result.is_ok()

    while workflow.pixel_classifier_applet.pixel_classifier() is None:
        time.sleep(0.2)

    classifier = workflow.pixel_classifier_applet.pixel_classifier()
    assert classifier != None




    fs = OsFs.create_scratch_dir()
    assert not isinstance(fs, Exception)
    ilp_path = PurePosixPath("my_test_output_proj.ilp")

    # import pydevd; pydevd.settrace()
    _ = workflow.save_project(fs=fs, path=ilp_path)

    # import pydevd; pydevd.settrace()
    workflow_ilp_group = IlpPixelClassificationWorkflowGroup.from_file(ilp_fs=fs, path=ilp_path)
    assert not isinstance(workflow_ilp_group, Exception), str(workflow_ilp_group)
    loaded_workflow = PixelClassificationWorkflow.from_ilp(
        workflow_group=workflow_ilp_group,
        on_async_change=lambda : print(json.dumps(workflow.export_applet._get_json_state(), indent=4)), # pyright: ignore [reportPrivateUsage]
        executor=executor,
        priority_executor=priority_executor,
    )
    print(loaded_workflow)
    if isinstance(loaded_workflow, Exception):
        raise loaded_workflow
    print(f"Loaded workflow and state pixel aplet description is {loaded_workflow.pixel_classifier_applet._state.description}") # pyright: ignore [reportPrivateUsage]





    # # calculate predictions on an entire data source
    raw_data_source = get_sample_c_cells_datasource()
    preds_future = executor.submit(classifier, raw_data_source.roi)
    _local_predictions = preds_future.result()
    # _local_predictions.as_uint8().show_channels()

    # # calculate predictions on just a piece of arbitrary data
    _exported_tile = executor.submit(classifier, DataRoi(datasource=raw_data_source, x=(100, 200), y=(100, 200)))
    # _exported_tile.result().show_channels()

###################################


#######################################33

    sink_fs = OsFs.create(); assert not isinstance(sink_fs, Exception)

    def run_an_export_job(): # pyright: ignore [reportUnusedFunction]
        predictions_export_datasink = create_precomputed_chunks_sink(
            fs=sink_fs,

            shape=raw_data_source.shape.updated(c=classifier.num_classes),
            dtype=np.dtype("float32"),
            chunk_size=raw_data_source.tile_shape.updated(c=classifier.num_classes),
        )

        print(f"Sending predictions job request??????")
        result = workflow.export_applet.launch_pixel_probabilities_export_job(
            datasource=raw_data_source,
            datasink=predictions_export_datasink
        )
        assert result is None

        print(f"---> Job successfully scheduled? Waiting for a while")
        wait_until_jobs_completed(workflow=workflow)
        print(f"Done waiting. Checking outputs")

        # predictions_output = predictions_export_datasink.to_datasource()
        # for tile in predictions_output.roi.get_datasource_tiles():
        #     _ = tile.retrieve().cut(c=1).as_uint8(normalized=True).show_channels()
    # run_an_export_job()

##################################333

    def run_a_simple_segmentation_job():  # pyright: ignore [reportUnusedFunction]
        simple_segmentation_datasink = create_precomputed_chunks_sink(
            fs=sink_fs,
            shape=raw_data_source.shape.updated(c=3),
            dtype=np.dtype("uint8"),
            chunk_size=raw_data_source.tile_shape.updated(c=3),
        )

        print(f"Sending simple segmentation job request??????")
        result = workflow.export_applet.launch_simple_segmentation_export_job(
            datasource=raw_data_source,
            datasink=simple_segmentation_datasink,
            label_name=pixel_annotations[0].name,
        )
        assert not isinstance(result, Exception)

        print(f"---> Job successfully scheduled? Waiting for a while")
        wait_until_jobs_completed(workflow=workflow)
        print(f"Done waiting. Checking outputs")

        # segmentation_output_1 = simple_segmentation_datasink.to_datasource()
        # for tile in segmentation_output_1.roi.get_datasource_tiles():
        #     _ = tile.retrieve().show_images()
    # run_a_simple_segmentation_job()

####################################3

    def run_dzi_export_job():
        # zip_file_path = PurePosixPath("my_output.dzip")
        # xml_path = PurePosixPath("/my_output.dzi")

        # output_fs = OsFs.create_scratch_dir()
        # assert not isinstance(output_fs, Exception)

        # zip_fs = ZipFs.create(zip_file_fs=output_fs, zip_file_path=zip_file_path)
        # assert not isinstance(zip_fs, Exception), str(zip_fs)
        # output_dzi_image = DziImageElement(
        #     Format="png",
        #     Overlap=0,
        #     Size=DziSizeElement(Width=raw_data_source.shape.x, Height=raw_data_source.shape.y),
        #     TileSize=max(raw_data_source.tile_shape.x, raw_data_source.tile_shape.y),
        # )
        # sink = DziLevelSink(
        #     dzi_image=output_dzi_image,
        #     filesystem=zip_fs,
        #     xml_path=xml_path,
        #     level_index=output_dzi_image.max_level_index,
        #     num_channels=3,
        #     spatial_resolution=None,
        # )

        datasink_dto = DziLevelSinkDto.from_json_value(json.loads(
            """{
                "__class__": "DziLevelSinkDto",
                "filesystem": {
                    "__class__": "ZipFsDto",
                    "zip_file_fs": {
                        "__class__": "BucketFSDto",
                        "bucket_name": "hbp-image-service"
                    },
                    "zip_file_path": "/zip_sink_test/c_cells_1.png_simple_segmentation.dzip"
                },
                "xml_path": "/c_cells_1.png_simple_segmentation.dzi",
                "dzi_image": {
                    "__class__": "DziImageElementDto",
                    "Format": "png",
                    "Overlap": 0,
                    "TileSize": 256,
                    "Size": {
                        "__class__": "DziSizeElementDto",
                        "Width": 697,
                        "Height": 450
                    }
                },
                "num_channels": 3,
                "level_index": 10
            }"""
        ))
        assert not isinstance(datasink_dto, Exception), str(datasink_dto)
        # import pydevd; pydevd.settrace()
        sink = DziLevelSink.from_dto(datasink_dto)
        assert not isinstance(sink, Exception), str(sink)





        res = workflow.export_applet.launch_simple_segmentation_export_job(
            datasource=raw_data_source,
            datasink=sink,
            label_name="Foreground",
        )
        assert not isinstance(res, Exception), str(res)

        for _ in range(99999999):
            time.sleep(2)
            for job in workflow.export_applet.get_state_dto().jobs:
                if isinstance(job.status, JobFinishedDto):
                    if job.status.error_message:
                        print(f"oooooooooo A job failed: {job.name}: {job.status.error_message}")
                        exit(1)
                elif isinstance(job.status, JobCanceledDto):
                    print(f"oooooooooo A job was canceled: {job.name}: {job.status.message}")
                    exit(1)
                else:
                    print(f"ooooooooooo {time.time()} Jobs are not done yet: {job.status.to_json_value()}")
                    break
            else:
                assert isinstance(sink, FsDataSink)
                zip_fs = sink.filesystem
                assert isinstance(zip_fs, ZipFs)

                output_url = zip_fs.zip_file_fs.geturl(zip_fs.zip_file_path)
                print(f"~~~~~~``>>> Checking if this exists: {output_url.raw}")
                output_exists = zip_fs.zip_file_fs.exists(zip_fs.zip_file_path)
                assert not isinstance(output_exists, Exception), str(output_exists)
                if output_exists:
                    print(f"====>>>>> I think we're done")
                    break
                else:
                    print(f"ooooooooooo Output doesn't seem to exist yet")
                    continue

        # import pydevd; pydevd.settrace()
        # zip_fs = ZipFs.create(zip_file_fs=output_fs, zip_file_path=zip_file_path)
        # assert not isinstance(zip_fs, Exception)

        # pyramid = DziLevelDataSource.try_load_as_pyramid(
        #     filesystem=zip_fs,
        #     dzi_path=xml_path,
        # )
        # assert not isinstance(pyramid, (Exception, type(None))), str(pyramid)
        # for level_index in reversed(range(pyramid[0].dzi_image.max_level_index + 1)):
        #     level = pyramid[level_index]
        #     _ = level.retrieve().show_images(name_suffix=f"__{level_index}")


    run_dzi_export_job()

    priority_executor.shutdown()

##################################################3333
if __name__ == "__main__":
    test_pixel_classification_workflow()
