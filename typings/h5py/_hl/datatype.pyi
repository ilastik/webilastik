"""
This type stub file was generated by pyright.
"""

from .base import HLObject, with_phil

"""
    Implements high-level acces"""
class Datatype(HLObject):
    """
        Represents an HDF5 name"""
    @property
    @with_phil
    def dtype(self):
        """Numpy dtype equivalent for this """
        ...
    
    @with_phil
    def __init__(self, bind) -> None:
        """ Create a new Datatype object by"""
        ...
    
    @with_phil
    def __repr__(self): # -> str:
        ...
    


