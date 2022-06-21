from typing import List, Sequence
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from vigra.learning import RandomForest as VigraRandomForest
from webilastik.datasource import DataRoi, DataSource
import multiprocessing

from webilastik.features.object_feature_extractor import ObjectFeatureExtractor
from webilastik.annotations.object_annotation import ObjectAnnotation


class ObjectClassifier:
    def __init__(self, *, feature_extractor: ObjectFeatureExtractor, forests: List[VigraRandomForest]):
        self.feature_extractor = feature_extractor
        self.forests = forests
        super().__init__()

    @classmethod
    def train(
        cls,
        feature_extractor: ObjectFeatureExtractor,
        annotations: Sequence[ObjectAnnotation],
        *,
        num_trees: int = 100,
        num_forests: int = multiprocessing.cpu_count(),
        random_seed: int = 0,
        strict: bool = False,
    ) -> "ObjectClassifier":
        X, y = ObjectAnnotation.gather_samples(annotations=annotations, feature_extractor=feature_extractor)

        def train_forest(forest_index: int) -> VigraRandomForest:
            ntrees = (num_trees // num_forests) + (forest_index < num_trees % num_forests)
            forest = VigraRandomForest(ntrees)
            _ = forest.learnRF(X, y, random_seed)
            return forest

        with ThreadPoolExecutor() as executor:
            forests = list(executor.map(train_forest, range(num_forests)))

        return cls(feature_extractor=feature_extractor, forests=forests)

    def predict(self, roi: DataRoi):
        pass
