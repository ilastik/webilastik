from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Tuple, Sequence, List, Dict
from webilastik.ui.applet.data_selection_applet import url_to_datasource
from collections.abc import Mapping as BaseMapping
import functools

import flask
from flask import Flask
import pytest
import numpy as np
from ndstructs import Point5D, Slice5D
from ndstructs.datasource import DataSource, DataSourceSlice
from ndstructs.utils import from_json_data, to_json_data, Dereferencer

from webilastik.annotations import Annotation, Color
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.ui.applet import CancelledException, SequenceProviderApplet
from webilastik.ui.workflow.pixel_classification_workflow import PixelClassificationWorkflow, PixelClassificationLane
from webilastik.classifiers.pixel_classifier import PixelClassifier, Predictions
from webilastik.features.ilp_filter import IlpFilter


#FIXME: can we do this without the monkey patching?
@classmethod
#@functools.lru_cache(maxsize=128)
def datasource_from_json_data(cls, data, dereferencer: Dereferencer = None):
    if isinstance(data, str):
        url = data
    elif isinstance(data, BaseMapping):
        url = data["url"]
    else:
        raise ValueError(f"Can't deserialize a datasource from {data}")
    return url_to_datasource(url)
DataSource.from_json_data = datasource_from_json_data


app = Flask("PixelClassificationServer")
wf = PixelClassificationWorkflow()
dummy_confirmer = lambda msg: True

def expose_sequence_applet(applet_name: str, applet: SequenceProviderApplet, item_class):
    def add() -> str:
        payload = flask.request.get_json()
        items = [from_json_data(item_class, item) for item in payload["items"]]
        applet.add(items, confirmer=dummy_confirmer)
        return flask.jsonify(to_json_data(applet.items()))
    add.__name__ = f"{applet_name}_add"
    app.route(f"/{applet_name}/add", methods=["POST"])(add)

    def remove() -> str:
        payload = flask.request.get_json()
        items = [from_json_data(item_class, item) for item in payload["items"]]
        applet.remove(items, confirmer=dummy_confirmer)
        return flask.jsonify(to_json_data(applet.items()))
    remove.__name__ = f"{applet_name}_remove"
    app.route(f"/{applet_name}/remove", methods=["POST"])(remove)

    def clear() -> str:
        applet.clear(confirmer=dummy_confirmer)
        return "ok"
    clear.__name__ = f"{applet_name}_clear"
    app.route(f"/{applet_name}/clear", methods=["POST"])(clear)

    def items() -> str:
        return flask.jsonify(to_json_data(applet.items()))
    items.__name__ = f"{applet_name}_items"
    app.route(f"/{applet_name}/items", methods=["GET"])(items)

expose_sequence_applet(applet_name="data_selection_applet", applet=wf.data_selection_applet, item_class=PixelClassificationLane)
expose_sequence_applet(applet_name="feature_selection_applet", applet=wf.feature_selection_applet, item_class=IlpFilter)
expose_sequence_applet(applet_name="brushing_applet", applet=wf.brushing_applet, item_class=Annotation)

@app.route("/pixel_classifier_applet/predictions_shader", methods=["GET"])
def get_predictions_shader():
    color_map = wf.pixel_classifier_applet.color_map()
    if color_map is None:
        raise ValueError("Classifier is not ready yet")

    color_lines: List[str] = []
    colors_to_mix: List[str] = []

    for idx, color in enumerate(color_map.keys()):
        color_line = (
            f"vec3 color{idx} = (vec3({color.r}, {color.g}, {color.b}) / 255.0) * toNormalized(getDataValue({idx}));"
        )
        color_lines.append(color_line)
        colors_to_mix.append(f"color{idx}")

    shader_lines = [
        "void main() {",
        "    " + "\n    ".join(color_lines),
        "    emitRGBA(",
        f"        vec4({' + '.join(colors_to_mix)}, 1.0)",
        "    );",
        "}",
    ]
    return flask.Response("\n".join(shader_lines), mimetype="text/plain")

# https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#unsharded-chunk-storage
@app.route("/predictions_export_applet/<int:lane_index>/data/<int:xBegin>-<int:xEnd>_<int:yBegin>-<int:yEnd>_<int:zBegin>-<int:zEnd>")
def ng_predict(lane_index: int, xBegin: int, xEnd: int, yBegin: int, yEnd: int, zBegin: int, zEnd: int):
    requested_roi = Slice5D(x=slice(xBegin, xEnd), y=slice(yBegin, yEnd), z=slice(zBegin, zEnd))
    predictions = wf.predictions_export_applet.compute_lane(lane_index, slc=requested_roi)

    # https://github.com/google/neuroglancer/tree/master/src/neuroglancer/datasource/precomputed#raw-chunk-encoding
    # "(...) data for the chunk is stored directly in little-endian binary format in [x, y, z, channel] Fortran order"
    resp = flask.make_response(predictions.as_uint8().raw("xyzc").tobytes("F"))
    resp.headers["Content-Type"] = "application/octet-stream"
    return resp

@app.route("/predictions_export_applet/<int:lane_index>/info/")
def info_dict(lane_index: int) -> Dict:
    #FIXME: do not access pixel_classifier_applet
    classifier = wf.pixel_classifier_applet.pixel_classifier()
    color_map = wf.pixel_classifier_applet.color_map()
    if classifier is None or color_map is None:
        raise ValueError("No classifier trained yet")
    expected_num_channels = len(color_map)
    datasource = wf.data_selection_applet.items()[lane_index].get_raw_data()

    resp = flask.jsonify(
        {
            "@type": "neuroglancer_multiscale_volume",
            "type": "image",
            "data_type": "uint8",  # DONT FORGET TO CONVERT PREDICTIONS TO UINT8!
            "num_channels": expected_num_channels,
            "scales": [
                {
                    "key": "data",
                    "size": [int(v) for v in datasource.shape.to_tuple("xyz")],
                    "resolution": [1, 1, 1],
                    "voxel_offset": [0, 0, 0],
                    "chunk_sizes": [datasource.tile_shape.to_tuple("xyz")],
                    "encoding": "raw",
                }
            ],
        }
    )
    return resp

if __name__ == "__main__":
    app.run()
