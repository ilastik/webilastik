from typing import List, Sequence

import numpy as np
from vigra.learning import RandomForest as VigraRandomForest
from ndstructs.datasource import DataRoi, DataSource
import multiprocessing

from webilastik.features.object_feature_extractor import ObjectFeatureExtractor
from webilastik.annotations.object_annotation import ObjectAnnotation


class ObjectClassifier:
    def __init__(self, *, feature_extractor: ObjectFeatureExtractor, forests: List[VigraRandomForest]):
        self.feature_extractor = feature_extractor

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

        tree_counts = np.array([num_trees // num_forests] * num_forests)
        tree_counts[: num_trees % num_forests] += 1
        tree_counts = list(map(int, tree_counts))

        forests = [VigraRandomForest(tree_counts[forest_index]) for forest_index in range(num_forests)]

        def train_forest(forest_index):
            forests[forest_index].learnRF(X, y, random_seed)

        # FIXME: do it in thread pool
        for i in range(num_forests):
            train_forest(i)

        return cls(feature_extractor=feature_extractor, forests=forests)

    def predict(self, roi: DataRoi):
        pass
