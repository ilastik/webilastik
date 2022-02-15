import numpy as np
from ndstructs.array5D import Array5D
from global_cache import global_cache

def test_global_cache():
    @global_cache
    def make_some_random_array(seed: int) -> Array5D:
        return Array5D(np.random.rand(5, 5), axiskeys="yx")

    a = make_some_random_array(17)
    b = make_some_random_array(17)

    assert np.all(a.raw("yx") == b.raw("yx"))

    class SomeClass:
        @global_cache
        def some_method(self, a: int) -> str:
            return str(np.random.rand(5, 5))

    x: str = SomeClass().some_method(123)
    y: str = SomeClass().some_method(123)

    assert x == y