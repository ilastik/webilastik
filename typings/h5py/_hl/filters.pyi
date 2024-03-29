"""
This type stub file was generated by pyright.
"""

from collections.abc import Mapping

"""
    Implements support for HDF5"""
_COMP_FILTERS = ...
DEFAULT_GZIP = ...
DEFAULT_SZIP = ...
class FilterRefBase(Mapping):
    """Base class for referring to an H"""
    filter_id = ...
    filter_options = ...
    def __hash__(self) -> int:
        ...
    
    def __eq__(self, other) -> bool:
        ...
    
    def __len__(self): # -> int:
        ...
    
    def __iter__(self): # -> Iterator[str]:
        ...
    
    def __getitem__(self, item):
        ...
    


class Gzip(FilterRefBase):
    filter_id = ...
    def __init__(self, level=...) -> None:
        ...
    


def fill_dcpl(plist, shape, dtype, chunks, compression, compression_opts, shuffle, fletcher32, maxshape, scaleoffset, external, allow_unknown_filter=...):
    """ Generate a dataset creation pro"""
    ...

def get_filters(plist): # -> dict[Unknown, Unknown]:
    """ Extract a dictionary of active """
    ...

CHUNK_BASE = ...
CHUNK_MIN = ...
CHUNK_MAX = ...
def guess_chunk(shape, maxshape, typesize): # -> tuple[int, ...]:
    """ Guess an appropriate chunk layo"""
    ...

