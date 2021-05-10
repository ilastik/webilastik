"""
This type stub file was generated by pyright.
"""

if h5py:
    def convert_to_h5(in_path, out_path, in_path_in_file, out_path_in_file, n_threads, chunks=..., block_shape=..., roi=..., fit_to_roi=..., **h5_kwargs):
        """ Convert n5 ot zarr dataset to hdf5 dataset.

        The chunks of the output dataset must be spcified.
        The dataset is converted to hdf5 in parallel over the chunks.
        Note that hdf5 does not support parallel write access, so more threads
        may not speed up the conversion.
        Datatype and compression can be specified, otherwise defaults will be used.

        Args:
            in_path (str): path to n5 or zarr file.
            out_path (str): path to output hdf5 file.
            in_path_in_file (str): name of input dataset.
            out_path_in_file (str): name of output dataset.
            n_threads (int): number of threads used for converting.
            chunks (tuple): chunks of output dataset.
                By default input datase's chunks are used. (default: None)
            block_shape (tuple): block shape used for converting, must be multiple of ``chunks``.
                If None, the chunk size will be used (default: None).
            roi (tuple[slice]): region of interest that will be copied. (default: None)
            fit_to_roi (bool): if given a roi, whether to set the shape of
                the output dataset to the roi's shape
                and align chunks with the roi's origin. (default: False)
            **h5_kwargs: keyword arguments for ``h5py`` dataset, e.g. datatype or compression.
        """
        ...
    
    def convert_from_h5(in_path, out_path, in_path_in_file, out_path_in_file, n_threads, chunks=..., block_shape=..., use_zarr_format=..., roi=..., fit_to_roi=..., **z5_kwargs):
        """ Convert hdf5 dataset to n5 or zarr dataset.

        The chunks of the output dataset must be spcified.
        The dataset is converted in parallel over the chunks.
        Datatype and compression can be specified, otherwise defaults will be used.

        Args:
            in_path (str): path to hdf5 file.
            out_path (str): path to output zarr or n5 file.
            in_path_in_file (str): name of input dataset.
            out_path_in_file (str): name of output dataset.
            n_threads (int): number of threads used for converting.
            chunks (tuple): chunks of output dataset.
             By default input dataset's chunks are used. (default: None)
            block_shape (tuple): block shape used for converting, must be multiple of ``chunks``.
                If None, the chunk shape will be used (default: None).
            use_zarr_format (bool): flag to indicate zarr format.
                If None, an attempt will be made to infer the format from the file extension,
                otherwise zarr will be used (default: None).
            roi (tuple[slice]): region of interest that will be copied. (default: None)
            fit_to_roi (bool): if given a roi, whether to set the shape of
                the output dataset to the roi's shape
                and align chunks with the roi's origin. (default: False)
            **z5_kwargs: keyword arguments for ``z5py`` dataset, e.g. datatype or compression.
        """
        ...
    
if imageio:
    def convert_to_tif():
        ...
    
    def is_int(string):
        ...
    
    def default_index_parser(fname):
        ...
    
    def convert_from_tif(in_path, out_path, out_path_in_file, chunks, n_threads, use_zarr_format=..., parser=..., preprocess=..., **z5_kwargs):
        """ Convert tif stack or folder of tifs to n5 or zarr dataset.

        The chunks of the output dataset must be specified.
        The dataset is converted in parallel over the chunks.
        Datatype and compression can be specified, otherwise defaults will be used.

        Args:
            in_path (str): path to tif stack or folder of tifs.
            out_path (str): path to output zarr or n5 file.
            out_path_in_file (str): name of output dataset.
            chunks (tuple): chunks of output dataset.
            n_threads (int): number of threads used for converting.
            use_zarr_format (bool): flag to indicate zarr format.
                If None, an attempt will be made to infer the format from the file extension,
                otherwise zarr will be used (default: None).
            parser (callable): function to parse the image indices for tifs in a folder.
                If None, some default patterns are tried (default: None)
            process (callable): function to preprocess chunks before wrting to n5/zarr
                Must take np.ndarray and int as arguments. (default: None)
            **z5_kwargs: keyword arguments for ``z5py`` dataset, e.g. datatype or compression.
        """
        ...
    