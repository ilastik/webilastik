import tests

def test_pixel_classifier():
    datasource = tests.get_sample_c_cells_datasource()
    classifier = tests.get_sample_c_cells_pixel_classifier()
    for tile in datasource.roi.default_split():
        classifier.compute(tile).show_channels()

if __name__ == "__main__":
    test_pixel_classifier()