from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Tuple, Sequence, List, Dict
from webilastik.ui.applet.data_selection_applet import url_to_datasource

import flask
from flask import Flask
import pytest
import numpy as np
from ndstructs import Point5D, Slice5D
from ndstructs.datasource import DataSource, DataSourceSlice
from ndstructs.utils import JsonSerializable, from_json_data, to_json_data, JsonReference

from webilastik.annotations import Annotation, Color
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.ui.applet import CancelledException
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane
from webilastik.classifiers.pixel_classifier import PixelClassifier, Predictions
from webilastik.features.ilp_filter import IlpFilter

dummy_confirmer = lambda msg: True

app = Flask("PixelClassificationServer")
@app.route("/hello", methods=["GET"])
def hello():
    return "eaeeae"

class WorkerConfig(JsonSerializable):
    def __init__(self, num_workers:int = 4):
        self.num_workers = num_workers
config = WorkerConfig(num_workers=4)
executors = [ProcessPoolExecutor(max_workers=1) for i in range(config.num_workers)]
wf = PixelClassificationWorkflow()

@app.route("/data_selection_applet/add", methods=["POST"])
def add_lane() -> str:
# GUI creates a datasource somewhere...
    for lane_data in flask.request.get_json():
        lane = PixelClassificationLane.from_json_value(lane_data)
        wf.data_selection_applet.add([lane], confirmer=dummy_confirmer)
    return "ok"

@app.route("/feature_selection_applet/add", methods=["POST"])
def add_feature_extractors() -> str:
    # GUI creates some feature extractors
    extractors = []
    for extractor_data in flask.request.get_json():
        # if extractor_data['__class__'] == GaussianSmoothing.__name__:
        #     import pydevd; pydevd.settrace()
        #     ex = GaussianSmoothing.from_json_data(extractor_data)
        # elif extractor_data['__class__'] == HessianOfGaussianEigenvalues.__name__:
        #     ex = HessianOfGaussianEigenvalues.from_json_data(extractor_data)
        # else:
        #     raise ValueError(f"bad extractor class: {extractor_data['__class__']}")
        ex = IlpFilter.from_json_data(extractor_data)
        extractors.append(ex)

    wf.feature_selection_applet.add(extractors, confirmer=dummy_confirmer)
    return "ok"

@app.route("/brushing_applet/add", methods=["POST"])
def add_annotations() -> str:
    annotations = []
    for annot_data in flask.request.get_json():
        annot_data["raw_data"] = url_to_datasource(annot_data["raw_data"])
        annotations.append(Annotation.from_json_data(annot_data))
    wf.brushing_applet.add(annotations, confirmer=dummy_confirmer)
    return "ok"

# https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#unsharded-chunk-storage
@app.route("/pixel_classifier_applet/<int:lane_index>/data/<int:xBegin>-<int:xEnd>_<int:yBegin>-<int:yEnd>_<int:zBegin>-<int:zEnd>")
def ng_predict(
    lane_index: int, xBegin: int, xEnd: int, yBegin: int, yEnd: int, zBegin: int, zEnd: int
):
    requested_roi = Slice5D(x=slice(xBegin, xEnd), y=slice(yBegin, yEnd), z=slice(zBegin, zEnd))
    classifier = wf.pixel_classifier_applet.pixel_classifier()
    if classifier is None:
        raise ValueError("No classifier trained yet")
    datasource = wf.data_selection_applet.lanes()[lane_index].get_raw_data()
    backed_roi = DataSourceSlice(datasource, **requested_roi.to_dict()).defined()
    predictions = classifier.allocate_predictions(backed_roi)
    slc_batches : Dict[int, List[DataSourceSlice]]= defaultdict(list)
    for slc in backed_roi.get_tiles():
        batch_idx = hash(slc) % config.num_workers
        slc_batches[batch_idx].append(slc)

    result_batch_futures = []
    for idx, batch in slc_batches.items():
        executor = executors[idx]
        result_batch_futures.append(executor.submit(do_worker_predict, (classifier, batch)))
    for future in result_batch_futures:
        for result in future.result():
            predictions.set(result)

    # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
    # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
    resp = flask.make_response(predictions.as_uint8().raw("xyzc").tobytes("F"))
    resp.headers["Content-Type"] = "application/octet-stream"
    return resp

def do_worker_predict(slice_batch: Tuple[PixelClassifier, Sequence[DataSourceSlice]]) -> List[Predictions]:
    classifier = slice_batch[0]
    out = []
    for datasource_slc in slice_batch[1]:
        pred_tile = classifier.predict(datasource_slc)
        out.append(pred_tile)
    return out


app.run()
