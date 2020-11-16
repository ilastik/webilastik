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

wf = PixelClassificationWorkflow()

@app.route("/data_selection_applet/add", methods=["POST"])
def add_lane() -> str:
# GUI creates a datasource somewhere...
    for lane_data in flask.request.get_json():
        lane = PixelClassificationLane.from_json_value(lane_data)
        wf.data_selection_applet.add([lane], confirmer=dummy_confirmer)
    return "ok"

@app.route("/feature_selection_applet/add", methods=["POST"])
def get_feature_extractors() -> str:
    extractors = []
    for extractor_data in flask.request.get_json():
        ex = IlpFilter.from_json_data(extractor_data)
        extractors.append(ex)
    wf.feature_selection_applet.add(extractors, confirmer=dummy_confirmer)
    return "ok"

@app.route("/feature_selection_applet/items", methods=["GET"])
def add_feature_extractors() -> str:
    return flask.jsonify(to_json_data(wf.feature_selection_applet.items()))

@app.route("/brushing_applet/add", methods=["POST"])
def add_annotations() -> str:
    annotations = []
    for annot_data in flask.request.get_json():
        annot_data["raw_data"] = url_to_datasource(annot_data["raw_data"])
        annotations.append(Annotation.from_json_data(annot_data))
    wf.brushing_applet.add(annotations, confirmer=dummy_confirmer)
    return "ok"

@app.route("/brushing_applet/remove", methods=["POST"])
def reove_annotation() -> str:
    annot_data = flask.request.get_json()
    annot_data["raw_data"] = url_to_datasource(annot_data["raw_data"])
    annotation = Annotation.from_json_data(annot_data)
    wf.brushing_applet.remove(annotation, confirmer=dummy_confirmer)
    return "ok"

# https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#unsharded-chunk-storage
@app.route("/pixel_classifier_applet/<int:lane_index>/data/<int:xBegin>-<int:xEnd>_<int:yBegin>-<int:yEnd>_<int:zBegin>-<int:zEnd>")
def ng_predict(lane_index: int, xBegin: int, xEnd: int, yBegin: int, yEnd: int, zBegin: int, zEnd: int):
    requested_roi = Slice5D(x=slice(xBegin, xEnd), y=slice(yBegin, yEnd), z=slice(zBegin, zEnd))
    predictions = wf.predictions_export_applet.compute_lane(lane_index, slc=requested_roi)

    # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
    # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
    resp = flask.make_response(predictions.as_uint8().raw("xyzc").tobytes("F"))
    resp.headers["Content-Type"] = "application/octet-stream"
    return resp

if __name__ == "__main__":
    app.run()
