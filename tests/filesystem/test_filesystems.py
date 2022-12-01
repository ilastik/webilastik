from pathlib import PurePosixPath
from webilastik.filesystem import SystemFs, BucketFs
import json
import uuid

for fs in [SystemFs(), BucketFs(bucket_name="hbp-image-service")]:
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


