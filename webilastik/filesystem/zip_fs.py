from pathlib import PurePosixPath
from webilastik.filesystem import IFilesystem

import numpy as np

class ZipFs(IFilesystem):
    def __init__(self, zip_file_fs: IFilesystem, zip_file_path: PurePosixPath) -> None:
        self.zip_file_fs: IFilesystem = zip_file_fs
        self.zip_file_path: PurePosixPath = zip_file_path
        super().__init__()

    @classmethod
    def create(cls, zip_file_fs: IFilesystem, zip_file_path: PurePosixPath) -> "ZipFs | Exception":
        EOCD_dtype = np.dtype(npheader_types = [
            ("signature", "<u4"),
            ("disk_number", "<u2"),
            ("central_directory_start_disk_index", "<u2"),
            ("num_central_directories_on_disk", "<u2"),
            ("total_num_central_directories", "<u2"),
            ("size_bytes", "<u4"),
            ("offset", "<u4"), # Offset of start of central directory, relative to start of archive (or 0xffffffff for ZIP64)
            ("comment_length", "<u2"),
            ("comment", "<u2"),
        ]) # pyright: ignore

        local_file_header_dtype = np.dtype(npheader_types = [
            ("signature", "4B"),
            ("min_version", "<u2"),
            ("flags", "<u2"),
            ("compression_method", "<u2"),
            ("last_modification_time", "<u2"),
            ("last_modification_date", "<u2"),
            ("crc_32_of_uncompressed_data", "<u4"),
            ("compressed_size", "<u4"),
            ("uncompressed_size", "<u4"),
            ("file_name_length", "<u2"),
        ]) # pyright: ignore