"""
This type stub file was generated by pyright.
"""

from contextlib import contextmanager
from .base import HLObject, MutableMappingHDF5, with_phil
from .vds import vds_support

"""
    Implements support for high"""
class Group(HLObject, MutableMappingHDF5):
    """ Represents an HDF5 group.
    """
    def __init__(self, bind) -> None:
        """ Create a new Group object by bi"""
        ...
    
    _gcpl_crt_order = ...
    def create_group(self, name, track_order=...): # -> Group:
        """ Create and return a new subgrou"""
        ...
    
    def create_dataset(self, name, shape=..., dtype=..., data=..., **kwds): # -> Dataset:
        """ Create a new HDF5 dataset

    """
        ...
    
    if vds_support:
        def create_virtual_dataset(self, name, layout, fillvalue=...): # -> Dataset:
            """Create a new virtual dataset in """
            ...
        
        @contextmanager
        def build_virtual_dataset(self, name, shape, dtype, maxshape=..., fillvalue=...): # -> Generator[VirtualLayout, None, None]:
            """Assemble a virtual dataset in th"""
            ...
        
    def require_dataset(self, name, shape, dtype, exact=..., **kwds): # -> Dataset:
        """ Open a dataset, creating it if """
        ...
    
    def create_dataset_like(self, name, other, **kwupdate): # -> Dataset:
        """ Create a dataset similar to `ot"""
        ...
    
    def require_group(self, name): # -> Group:
        """Return a group, creating it if i"""
        ...
    
    @with_phil
    def __getitem__(self, name): # -> Group | Dataset | Datatype:
        """ Open an object in the file """
        ...
    
    def get(self, name, default=..., getclass=..., getlink=...):
        """ Retrieve an item or other infor"""
        ...
    
    def __setitem__(self, name, obj): # -> None:
        """ Add an object to the group.  Th"""
        ...
    
    @with_phil
    def __delitem__(self, name): # -> None:
        """ Delete (unlink) an item from th"""
        ...
    
    @with_phil
    def __len__(self):
        """ Number of members attached to t"""
        ...
    
    @with_phil
    def __iter__(self): # -> Generator[Unknown | None, None, None]:
        """ Iterate over member names """
        ...
    
    @with_phil
    def __reversed__(self): # -> Generator[Unknown | None, None, None]:
        """ Iterate over member names in re"""
        ...
    
    @with_phil
    def __contains__(self, name): # -> bool:
        """ Test if a member name exists """
        ...
    
    def copy(self, source, dest, name=..., shallow=..., expand_soft=..., expand_external=..., expand_refs=..., without_attrs=...):
        """Copy an object or group.

      """
        ...
    
    def move(self, source, dest): # -> None:
        """ Move a link to a new location i"""
        ...
    
    def visit(self, func):
        """ Recursively visit all names in """
        ...
    
    def visititems(self, func):
        """ Recursively visit names and obj"""
        ...
    
    @with_phil
    def __repr__(self): # -> str:
        ...
    


class HardLink:
    """
        Represents a hard link """
    ...


class SoftLink:
    """
        Represents a symbolic ("""
    @property
    def path(self): # -> str:
        """ Soft link value.  Not guarantee"""
        ...
    
    def __init__(self, path) -> None:
        ...
    
    def __repr__(self): # -> str:
        ...
    


class ExternalLink:
    """
        Represents an HDF5 exte"""
    @property
    def path(self):
        """ Soft link path, i.e. the part i"""
        ...
    
    @property
    def filename(self): # -> str:
        """ Path to the external HDF5 file """
        ...
    
    def __init__(self, filename, path) -> None:
        ...
    
    def __repr__(self): # -> str:
        ...
    


