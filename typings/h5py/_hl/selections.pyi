"""
This type stub file was generated by pyright.
"""

"""
    High-level access to HDF5 dataspace selections
"""
def select(shape, args, dsid):
    """ High-level routine to generate a selection from arbitrary arguments
    to __getitem__.  The arguments should be the following:

    shape
        Shape of the "source" dataspace.

    args
        Either a single argument or a tuple of arguments.  See below for
        supported classes of argument.

    dsid
        A h5py.h5d.DatasetID instance representing the source dataset.

    Argument classes:

    Single Selection instance
        Returns the argument.

    numpy.ndarray
        Must be a boolean mask.  Returns a PointSelection instance.

    RegionReference
        Returns a Selection instance.

    Indices, slices, ellipses only
        Returns a SimpleSelection instance

    Indices, slices, ellipses, lists or boolean index arrays
        Returns a FancySelection instance.
    """
    ...

class _RegionProxy(object):
    """
        Thin proxy object which takes __getitem__-style index arguments and
        produces RegionReference objects.  Example:

        >>> dset = myfile['dataset']
        >>> myref = dset.regionref[0:100,20:30]
        >>> data = dset[myref]

    """
    def __init__(self, dsid) -> None:
        """ Supply a h5py.h5d.DatasetID instance """
        ...
    
    def __getitem__(self, args):
        """ Takes arbitrary selection terms and produces a RegionReference
        object.  Selection must be compatible with the dataset.
        """
        ...
    


class Selection(object):
    """
        Base class for HDF5 dataspace selections.  Subclasses support the
        "selection protocol", which means they have at least the following
        members:

        __init__(shape)   => Create a new selection on "shape"-tuple
        __getitem__(args) => Perform a selection with the range specified.
                             What args are allowed depends on the
                             particular subclass in use.

        id (read-only) =>      h5py.h5s.SpaceID instance
        shape (read-only) =>   The shape of the dataspace.
        mshape  (read-only) => The shape of the selection region.
                               Not guaranteed to fit within "shape", although
                               the total number of points is less than
                               product(shape).
        nselect (read-only) => Number of selected points.  Always equal to
                               product(mshape).

        broadcast(target_shape) => Return an iterable which yields dataspaces
                                   for read, based on target_shape.

        The base class represents "unshaped" selections (1-D).
    """
    def __init__(self, shape, spaceid=...) -> None:
        """ Create a selection.  Shape may be None if spaceid is given. """
        ...
    
    @property
    def id(self):
        """ SpaceID instance """
        ...
    
    @property
    def shape(self):
        """ Shape of whole dataspace """
        ...
    
    @property
    def nselect(self):
        """ Number of elements currently selected """
        ...
    
    @property
    def mshape(self):
        """ Shape of selection (always 1-D for this class) """
        ...
    
    def broadcast(self, target_shape):
        """ Get an iterable for broadcasting """
        ...
    
    def __getitem__(self, args):
        ...
    


class PointSelection(Selection):
    """
        Represents a point-wise selection.  You can supply sequences of
        points to the three methods append(), prepend() and set(), or a
        single boolean array to __getitem__.
    """
    def __getitem__(self, arg):
        """ Perform point-wise selection from a NumPy boolean array """
        ...
    
    def append(self, points):
        """ Add the sequence of points to the end of the current selection """
        ...
    
    def prepend(self, points):
        """ Add the sequence of points to the beginning of the current selection """
        ...
    
    def set(self, points):
        """ Replace the current selection with the given sequence of points"""
        ...
    


class SimpleSelection(Selection):
    """ A single "rectangular" (regular) selection composed of only slices
        and integer arguments.  Can participate in broadcasting.
    """
    @property
    def mshape(self):
        """ Shape of current selection """
        ...
    
    def __init__(self, shape, *args, **kwds) -> None:
        ...
    
    def __getitem__(self, args):
        ...
    
    def broadcast(self, target_shape):
        """ Return an iterator over target dataspaces for broadcasting.

        Follows the standard NumPy broadcasting rules against the current
        selection shape (self.mshape).
        """
        ...
    


class FancySelection(Selection):
    """
        Implements advanced NumPy-style selection operations in addition to
        the standard slice-and-int behavior.

        Indexing arguments may be ints, slices, lists of indicies, or
        per-axis (1D) boolean arrays.

        Broadcasting is not supported for these selections.
    """
    @property
    def mshape(self):
        ...
    
    def __init__(self, shape, *args, **kwds) -> None:
        ...
    
    def __getitem__(self, args):
        ...
    
    def broadcast(self, target_shape):
        ...
    


def guess_shape(sid):
    """ Given a dataspace, try to deduce the shape of the selection.

    Returns one of:
        * A tuple with the selection shape, same length as the dataspace
        * A 1D selection shape for point-based and multiple-hyperslab selections
        * None, for unselected scalars and for NULL dataspaces
    """
    ...

