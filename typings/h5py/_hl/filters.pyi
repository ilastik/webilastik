"""
This type stub file was generated by pyright.
"""

from .. import h5z

"""
    Implements support for HDF5 compression filters via the high-level
    interface.  The following types of filter are available:

    "gzip"
        Standard DEFLATE-based compression, at integer levels from 0 to 9.
        Built-in to all public versions of HDF5.  Use this if you want a
        decent-to-good ratio, good portability, and don't mind waiting.

    "lzf"
        Custom compression filter for h5py.  This filter is much, much faster
        than gzip (roughly 10x in compression vs. gzip level 4, and 3x faster
        in decompressing), but at the cost of a worse compression ratio.  Use
        this if you want cheap compression and portability is not a concern.

    "szip"
        Access to the HDF5 SZIP encoder.  SZIP is a non-mainstream compression
        format used in space science on integer and float datasets.  SZIP is
        subject to license requirements, which means the encoder is not
        guaranteed to be always available.  However, it is also much faster
        than gzip.

    The following constants in this module are also useful:

    decode
        Tuple of available filter names for decoding

    encode
        Tuple of available filter names for encoding
"""
_COMP_FILTERS = { 'gzip': h5z.FILTER_DEFLATE,'szip': h5z.FILTER_SZIP,'lzf': h5z.FILTER_LZF,'shuffle': h5z.FILTER_SHUFFLE,'fletcher32': h5z.FILTER_FLETCHER32,'scaleoffset': h5z.FILTER_SCALEOFFSET }
DEFAULT_GZIP = 4
DEFAULT_SZIP = ('nn', 8)
def fill_dcpl(plist, shape, dtype, chunks, compression, compression_opts, shuffle, fletcher32, maxshape, scaleoffset, external):
    """ Generate a dataset creation property list.

    Undocumented and subject to change without warning.
    """
    ...

def get_filters(plist):
    """ Extract a dictionary of active filters from a DCPL, along with
    their settings.

    Undocumented and subject to change without warning.
    """
    ...

CHUNK_BASE = 16 * 1024
CHUNK_MIN = 8 * 1024
CHUNK_MAX = 1024 * 1024
def guess_chunk(shape, maxshape, typesize):
    """ Guess an appropriate chunk layout for a dataset, given its shape and
    the size of each element in bytes.  Will allocate chunks only as large
    as MAX_SIZE.  Chunks are generally close to some power-of-2 fraction of
    each axis, slightly favoring bigger values for the last index.

    Undocumented and subject to change without warning.
    """
    ...

