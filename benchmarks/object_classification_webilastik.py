from pathlib import Path
import time
from ndstructs.datasource.DataRoi import DataRoi

import vigra
import numpy as np
from fs.osfs import OSFS
from ndstructs.datasource import SkimageDataSource
from ndstructs import Shape5D, Point5D

import sys
print(sys.path)

from webilastik.classifiers.object_classifier import ObjectClassifier
from webilastik.connected_components import ConnectedComponentsExtractor
from webilastik.thresholder import Thresholder
from webilastik.features.object_feature_extractor import VigraObjectFeatureExtractor, VigraFeatureName
from webilastik.annotations.object_annotation import ObjectAnnotation


ds = SkimageDataSource(
    Path("sample_data/2d_cells_apoptotic_1c.png").absolute(),
    filesystem=OSFS("/"),
    tile_shape=Shape5D(x=100, y=100),
)


thresholder_op = Thresholder(threshold=30)
thresholder_op.compute(DataRoi(ds))#.show_channels()

comps_op = ConnectedComponentsExtractor(
    preprocessor=thresholder_op, object_channel_idx=0, expansion_step=Shape5D.zero(x=10, y=10)
)
comps_op.compute(DataRoi(ds, x=(100, 200), y=(200, 300)))#.show_color_mapped()

CLASS_ALIVE = 111
CLASS_DEAD = 222

annotations = [
    ObjectAnnotation(
        position=Point5D.zero(x=760, y=266), klass=CLASS_ALIVE, datasource=ds, components_extractor=comps_op
    ),
    ObjectAnnotation(
        position=Point5D.zero(x=432, y=633), klass=CLASS_ALIVE, datasource=ds, components_extractor=comps_op
    ),
    ObjectAnnotation(
        position=Point5D.zero(x=1028, y=325), klass=CLASS_DEAD, datasource=ds, components_extractor=comps_op
    ),
    ObjectAnnotation(
        position=Point5D.zero(x=234, y=238), klass=CLASS_DEAD, datasource=ds, components_extractor=comps_op
    ),
]

# for a in annotations:
#     a.show()


obj_feature_extractor = VigraObjectFeatureExtractor(feature_names=[VigraFeatureName.Kurtosis, VigraFeatureName.Skewness, VigraFeatureName.RegionCenter])
feature_map = obj_feature_extractor.get_timewise_feature_map(
    (DataRoi(ds, x=(100, 200), y=(200, 300)), comps_op)
)

print(f"Key: ", list(feature_map.keys())[0])
print(list(feature_map.values())[0]["RegionCenter"].raw("xc"))


features = obj_feature_extractor.compute(
    (DataRoi(ds, x=(100, 200), y=(200, 300)), comps_op)
)


# classifier = ObjectClassifier.train(
#     annotations=annotations, feature_extractor=obj_feature_extractor
# )
