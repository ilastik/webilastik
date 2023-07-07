#pyright: strict

from pathlib import PurePosixPath
from webilastik.filesystem import create_filesystem_from_url
from webilastik.filesystem.os_fs import OsFs
from webilastik.filesystem.bucket_fs import BucketFs
import uuid
from zipfile import ZipFile, ZIP_STORED

from webilastik.filesystem.zip_fs import ZipFs

def test_osfs_bucketfs():
    osfs = OsFs.create()
    assert not isinstance(osfs, Exception)
    for fs in [osfs, BucketFs(bucket_name="hbp-image-service")]:
        file_path = PurePosixPath(f"/tmp/test-{uuid.uuid4()}/test_file.txt")
        contents = "0123456789".encode('utf8')

        create_file_result = fs.create_file(path=file_path, contents=contents)
        assert not isinstance(create_file_result, Exception), str(create_file_result)

        get_size_result = fs.get_size(path=file_path)
        assert not isinstance(get_size_result, Exception), str(get_size_result)
        assert get_size_result == len(contents)

        retrieved_contents = fs.read_file(file_path)
        assert(retrieved_contents == contents)

        retrieved_piece = fs.read_file(file_path, offset=2, num_bytes=3)
        assert(retrieved_piece == contents[2:2+3])

        listing_result = fs.list_contents(file_path.parent)
        assert not isinstance(listing_result, Exception)
        assert file_path in listing_result.files

        assert not isinstance(fs.delete(file_path), Exception)
        listing_result = fs.list_contents(file_path.parent)
        assert not isinstance(listing_result, Exception)
        assert file_path not in listing_result.files


def test_zip_fs():
    temp_fs = OsFs.create_scratch_dir()
    assert not isinstance(temp_fs, Exception), str(temp_fs)
    tmp_zip_file_path = PurePosixPath("/bla.zip")
    zip_file = ZipFile(temp_fs.resolve_path(tmp_zip_file_path), mode="w", compresslevel=ZIP_STORED)

    entry1_contents = b"01234566789"
    entry1_path = "entry1.txt"
    zip_file.writestr(entry1_path, entry1_contents)

    entry2_contents = b"abcdefghijk"
    entry2_path = "a/b/entry2.txt"
    zip_file.writestr(entry2_path, entry2_contents)

    zip_file.close()


    zip_fs = ZipFs.create(zip_file_fs=temp_fs, zip_file_path=tmp_zip_file_path)
    assert not isinstance(zip_fs, Exception), str(zip_fs)

    root_contents = zip_fs.list_contents(PurePosixPath("/"))
    assert not isinstance(root_contents, Exception)
    assert root_contents.files == [PurePosixPath("/") / entry1_path]
    assert root_contents.directories == [PurePosixPath("/a")]

    slash_a_contents = zip_fs.list_contents(PurePosixPath("/a"))
    assert not isinstance(slash_a_contents, Exception)
    assert slash_a_contents.files == []
    assert slash_a_contents.directories == [PurePosixPath("/a/b")]

    slash_a_slash_b_contents = zip_fs.list_contents(PurePosixPath("/a/b"))
    assert not isinstance(slash_a_slash_b_contents, Exception)
    assert slash_a_slash_b_contents.files == [PurePosixPath("/a/b/entry2.txt")]
    assert slash_a_slash_b_contents.directories == []

    assert isinstance(zip_fs.list_contents(PurePosixPath("/does/not/exist")), Exception)

    entry1_retrieved_contents = zip_fs.read_file(PurePosixPath(entry1_path))
    assert not isinstance(entry1_retrieved_contents, Exception)
    assert entry1_retrieved_contents == entry1_contents

    entry1_partial_retrieved_contents = zip_fs.read_file(PurePosixPath(entry1_path), offset=2, num_bytes=3)
    assert not isinstance(entry1_partial_retrieved_contents, Exception), str(entry1_partial_retrieved_contents)
    assert entry1_partial_retrieved_contents == entry1_contents[2:2+3]


    entry2_retrieved_contents = zip_fs.read_file(PurePosixPath(entry2_path))
    assert not isinstance(entry2_retrieved_contents, Exception)
    assert entry2_retrieved_contents == entry2_contents

    entry2_partial_retrieved_contents = zip_fs.read_file(PurePosixPath(entry2_path), offset=2, num_bytes=3)
    assert not isinstance(entry2_partial_retrieved_contents, Exception), str(entry2_partial_retrieved_contents)
    assert entry2_partial_retrieved_contents == entry2_contents[2:2+3]


    zip_fs_and_path_result = create_filesystem_from_url(
        url=temp_fs.geturl(tmp_zip_file_path).joinpath(entry2_path)
    )
    assert not isinstance(zip_fs_and_path_result, Exception), str(zip_fs_and_path_result)
    zip_fs, entry_path_from_url = zip_fs_and_path_result
    assert zip_fs.read_file(entry_path_from_url) == entry2_contents

    zip_fs = ZipFs.create(zip_file_fs=temp_fs, zip_file_path=tmp_zip_file_path)
    assert not isinstance(zip_fs, Exception), str(zip_fs)
    assert zip_fs.read_file(PurePosixPath(entry1_path)) == entry1_contents


if __name__ == "__main__":
    import inspect
    import sys
    for item_name, item in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(item) and item_name.startswith('test'):
            print(f"Running test: {item_name}")
            item()