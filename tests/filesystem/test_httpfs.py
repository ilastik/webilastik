#!/usr/bin/env python

from fs.errors import ResourceNotFound
import uuid
import sys
from pathlib import Path
from threading import Thread
import functools

from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler

from webilastik.filesystem.http_fs import HttpFs
from webilastik.utility.url import Url
from tests import create_tmp_dir, get_project_test_dir


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def start_test_server(tmp_path: Path, port: int) -> HTTPServer:
    dir1 = tmp_path / "dir1"
    dir1.mkdir(parents=True)
    with open(dir1 / "file1.txt", "wb") as f:
        _ = f.write("file1_contents".encode("ascii"))

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    with open(dir2 / "file2.txt", "wb") as f:
        _ = f.write("file2_contents".encode("ascii"))

    dir3 = tmp_path / "dir3"
    dir3.mkdir()
    with open(dir3 / "file3.txt", "wb") as f:
        _ = f.write("file3_contents".encode("ascii"))

    dir4 = dir3 / "dir4"
    dir4.mkdir()
    with open(dir4 / "file4.txt", "wb") as f:
        _ = f.write("file4_contents".encode("ascii"))

    server_address = ("", port)
    httpd = HTTPServer(server_address, functools.partial(SimpleHTTPRequestHandler, directory=tmp_path.as_posix()))
    Thread(target=httpd.serve_forever).start()
    return httpd


def test_httpfs():
    httpd = start_test_server(create_tmp_dir(prefix="http_fs_test"), port=8123)
    try:
        fs = HttpFs(read_url=Url.parse_or_raise("http://localhost:8123/"))

        eprint("  -->  Opening some file...")
        with fs.openbin("/dir1/file1.txt", "r") as f:
            assert f.read() == "file1_contents".encode("ascii")

        eprint("  --> Verifying that opendir works nested dirs...")
        dir1 = fs.opendir("dir2")
        assert dir1.openbin("file2.txt", "r").read() == "file2_contents".encode("ascii")

        fs2 = HttpFs(read_url=Url.parse_or_raise("http://localhost:8123/dir1"))
        assert fs2.desc("file2.txt") == "http://localhost:8123/dir1/file2.txt"

        # check that "/" maps to the base url that was used to create the filesystem
        assert fs2.desc("/file2.txt") == "http://localhost:8123/dir1/file2.txt"

        #check that .. works even when creating the fs
        fs_updir = HttpFs(read_url=Url.parse_or_raise("http://localhost:8123/dir1/.."))
        with fs_updir.openbin("dir1/file1.txt", "r") as f:
            assert f.read() == "file1_contents".encode("ascii")

    finally:
        httpd.shutdown()

if __name__ == "__main__":
    test_httpfs()