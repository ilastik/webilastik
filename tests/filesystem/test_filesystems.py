from pathlib import PurePosixPath
from webilastik.filesystem.os_fs import OsFs
from webilastik.filesystem.bucket_fs import BucketFs
import uuid
from tests import get_ebrains_credentials, run_all_tests

def test_filesystems():
    osfs = OsFs.create()
    assert not isinstance(osfs, Exception)
    for fs in [osfs, BucketFs(bucket_name="hbp-image-service", ebrains_user_credentials=get_ebrains_credentials())]:
        file_path = PurePosixPath(f"/tmp/test-{uuid.uuid4()}/test_file.txt")
        contents = "lalala".encode('utf8')

        assert not isinstance(fs.create_file(path=file_path, contents=contents), Exception)

        retrieved_contents = fs.read_file(file_path)
        assert(retrieved_contents == contents)

        listing_result = fs.list_contents(file_path.parent)
        assert not isinstance(listing_result, Exception)
        assert file_path in listing_result.files

        assert not isinstance(fs.delete(file_path), Exception)
        listing_result = fs.list_contents(file_path.parent)
        assert not isinstance(listing_result, Exception)
        assert file_path not in listing_result.files


if __name__ == "__main__":
    import sys
    run_all_tests(module=sys.modules[__name__])