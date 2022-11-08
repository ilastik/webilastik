from tests import get_sample_c_cells_datasource
from webilastik.features.channelwise_fastfilters import (
    GaussianSmoothing
)

if __name__ == "__main__":
    ds = get_sample_c_cells_datasource()
    feature_extractor = GaussianSmoothing(axis_2d="z", sigma=3.0)
    for tile in ds.roi.get_datasource_tiles():
        _ = feature_extractor(tile)#.show_images()