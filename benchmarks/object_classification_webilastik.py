from pathlib import Path
import time

import vigra
import numpy as np
from fs.osfs import OSFS
from ndstructs.datasource import DataSource, SkimageDataSource, DataSourceSlice
from ndstructs import Slice5D, Shape5D, Array5D, Point5D

import sys
print(sys.path)

from webilastik.classifiers.object_classifier import ObjectClassifier
from webilastik.classifiers.connected_components import Thresholder, ConnectedComponentsExtractor
from webilastik.features.object_feature_extractor import array5d_to_vigra, VigraObjectFeatureExtractor
from webilastik.annotations.object_annotation import ObjectAnnotation


comps_op = ConnectedComponentsExtractor(
    object_channel_idx=0, thresholder=Thresholder(30), expansion_step=Point5D(x=10, y=10)
)

# ds = DataSource.create(Path("/home/tomaz/SampleData/c_cells/cropped/cropped1.png"))

COLOR_ALIVE = 111
COLOR_DEAD = 222

ds = SkimageDataSource(
    Path("/home/tomaz/SampleData/2d_cells_apoptotic_1c/2d_cells_apoptotic_1c.png"),
    filesystem=OSFS("/"),
    tile_shape=Shape5D(x=100, y=100),
)

annotations = [
    ObjectAnnotation(
        position=Point5D.zero(x=760, y=266), color=COLOR_ALIVE, datasource=ds, components_extractor=comps_op
    ),
    ObjectAnnotation(
        position=Point5D.zero(x=432, y=633), color=COLOR_ALIVE, datasource=ds, components_extractor=comps_op
    ),
    ObjectAnnotation(
        position=Point5D.zero(x=1028, y=325), color=COLOR_DEAD, datasource=ds, components_extractor=comps_op
    ),
    ObjectAnnotation(
        position=Point5D.zero(x=234, y=238), color=COLOR_DEAD, datasource=ds, components_extractor=comps_op
    ),
]

classifier = ObjectClassifier.train(
    annotations=annotations, feature_extractor=VigraObjectFeatureExtractor(feature_names=["Kurtosis", "Skewness"])
)