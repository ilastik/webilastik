import ast
from pathlib import Path
from typing import Any, Union, Sequence, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import math


from ndstructs import Array5D, Slice5D, Shape5D, Point5D
from ndstructs.datasource import DataSource, N5DataSource, DataSourceSlice
from webilastik.features.feature_extractor import FeatureExtractor
from webilastik.features import (
    GaussianSmoothing,
    HessianOfGaussianEigenvalues,
    GaussianGradientMagnitude,
    LaplacianOfGaussian,
    DifferenceOfGaussians,
    StructureTensorEigenvalues,
)
from webilastik.annotations import Annotation
from webilastik.classifiers.pixel_classifier import PixelClassifier, ScikitLearnPixelClassifier, Predictions
from webilastik.classifiers.ilp_pixel_classifier import IlpVigraPixelClassifier
import argparse

classifier_registry = {
    IlpVigraPixelClassifier.__name__: IlpVigraPixelClassifier,
    ScikitLearnPixelClassifier.__name__: ScikitLearnPixelClassifier,
}


def make_label_offset(value):
    coords = ast.literal_eval(value)
    if not isinstance(coords, dict):
        raise ValueError("Label offset must be  dict with keys in xyztc")
    return Point5D.zero(**coords)


parser = argparse.ArgumentParser(description="Apply inheritance by template")
parser.add_argument(
    "--classifier-class", required=True, choices=list(classifier_registry.keys()), help="Which pixel classifier to use"
)
parser.add_argument("--data-url", required=True, help="Url to the test data")
parser.add_argument(
    "--label-urls", required=True, nargs="+", help="Url to the uint8, single-channel label images", type=Path
)
parser.add_argument(
    "--label-offsets",
    required=True,
    nargs="+",
    help="Url to the uint8, single-channel label images",
    type=make_label_offset,
)
parser.add_argument(
    "--tile-size", required=False, type=int, default=None, help="Side of the raw data tile to use when predicting"
)

parser.add_argument(
    "--num-workers", required=False, type=int, default=8, help="Number of process workers to run predictions"
)
parser.add_argument("--orchestrator", required=True, choices=["sequential", "thread-pool", "process-pool"])
args = parser.parse_args()


# features = list(FeatureExtractor.from_ilp("/home/tomaz/unicore_stuff/UnicoreProject.ilp"))
# print(features)
# tile_shape = args.tile_size if args.tile_size is None else Shape5D.hypercube(args.tile_size)
datasource = DataSource.create(Path(args.data_url))
# print(datasource.full_shape)
print(f"Processing {datasource}")

extractors = [
    GaussianSmoothing.from_ilp_scale(scale=0.3, axis_2d="z"),
    HessianOfGaussianEigenvalues.from_ilp_scale(scale=0.7, axis_2d="z"),
    GaussianGradientMagnitude.from_ilp_scale(scale=0.7, axis_2d="z"),
    LaplacianOfGaussian.from_ilp_scale(scale=0.7, axis_2d="z"),
    DifferenceOfGaussians.from_ilp_scale(scale=0.7, axis_2d="z"),
    StructureTensorEigenvalues.from_ilp_scale(scale=1.0, axis_2d="z"),
]

annotations = []
for label_url, label_offset in zip(args.label_urls, args.label_offsets):
    annotations += list(Annotation.from_file(label_url, raw_data=datasource, location=label_offset))


classifier = classifier_registry[args.classifier_class].train(
    feature_extractors=extractors, annotations=annotations, random_seed=123
)
print(f"Finished training {classifier.__class__.__name__}")

import pickle

pickled_classifier = pickle.dumps(classifier)
classifier = pickle.loads(pickled_classifier)

predictions = classifier.allocate_predictions(datasource.roi)

if args.orchestrator == "sequential":
    def do_predict(datasource_slc: DataSourceSlice):
        print(f">>>>>>>> Predicting on {datasource_slc.roi}")
        pred_tile = classifier.predict(datasource_slc)
        print(f"<<<<<<<< DONE Predicting on {datasource_slc.roi}")
        predictions.set(pred_tile)

    for datasource_slc in DataSourceSlice(datasource).split():
        do_predict(datasource_slc)

elif args.orchestrator == "thread-pool":
    def do_predict(datasource_slc: DataSourceSlice):
        print(f">>>>>>>> Predicting on {datasource_slc.roi}")
        pred_tile = classifier.predict(datasource_slc)
        print(f"<<<<<<<< DONE Predicting on {datasource_slc.roi}")
        predictions.set(pred_tile)

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        for datasource_slc in DataSourceSlice(datasource).split():
            executor.submit(do_predict, datasource_slc)

elif args.orchestrator == "process-pool":
    def do_predict(slice_batch: Tuple[PixelClassifier, Sequence[DataSourceSlice]]):
        print(f"Stating batch with {len(slice_batch[1])} items")
        classifier = slice_batch[0]
        out = []
        for datasource_slc in slice_batch[1]:
            print(f">>>>>>>> Predicting on {datasource_slc.roi}")
            pred_tile = classifier.predict(datasource_slc)
            print(f"<<<<<<<< DONE Predicting on {datasource_slc.roi}")
            out.append(pred_tile)
        return out

    executor = ProcessPoolExecutor(max_workers=args.num_workers)
    all_slices = list(DataSourceSlice(datasource).split())
    batch_size = math.ceil(len(all_slices) / args.num_workers)
    batches = [(classifier, all_slices[start : start + batch_size]) for start in range(0, len(all_slices), batch_size)]
    for result_batch in executor.map(do_predict, batches):
        for result in result_batch:
            predictions.set(result)

else:
    raise NotImplementedError(f"Please implement orchestraiton for {args.orchestrator}")

#    executor = ProcessPoolExecutor(initializer=worker_initializer, initargs=(classifier,))
#    #worker_initializer(classifier)
#    futures = [executor.submit(do_prediction, raw_tile) for raw_tile in datasource.roi.split(datasource.tile_shape)]
#    #futures = [do_prediction(raw_tile) for raw_tile in datasource.roi.split(datasource.tile_shape)]
#    #executor.shutdown(wait=True)
#    for f in futures:
#        result = f.result()
#        predictions.set(result)
#        #predictions.set(f)
print(f"Finished prediction with {classifier.__class__.__name__}")
predictions.as_uint8().show_channels()
