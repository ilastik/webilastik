"""
This type stub file was generated by pyright.
"""

import atexit
from warnings import warn as _warn
from . import h5a, h5d, h5ds, h5f, h5fd, h5g, h5p, h5pl, h5r, h5s, h5t, h5z, version
from ._conv import register_converters as _register_converters, unregister_converters as _unregister_converters
from .h5z import _register_lzf
from ._hl import filters
from ._hl.base import Empty, HLObject, is_hdf5
from ._hl.files import File, register_driver, registered_drivers, unregister_driver
from ._hl.group import ExternalLink, Group, HardLink, SoftLink
from ._hl.dataset import Dataset
from ._hl.datatype import Datatype
from ._hl.attrs import AttributeManager
from ._selector import MultiBlockSlice
from .h5 import get_config
from .h5r import Reference, RegionReference
from .h5t import check_dtype, check_enum_dtype, check_opaque_dtype, check_ref_dtype, check_string_dtype, check_vlen_dtype, enum_dtype, opaque_dtype, ref_dtype, regionref_dtype, special_dtype, string_dtype, vlen_dtype
from .h5s import UNLIMITED
from .version import version as __version__
from ._hl.vds import VirtualLayout, VirtualSource

"""
    This is the h5py package, a"""
if version.hdf5_version_tuple != version.hdf5_built_version_tuple:
    ...
if version.hdf5_version_tuple[: 3] >= get_config().vds_min_hdf5_version:
    ...

__all__ = ["File", "Group", "Dataset"]

