# pyright: strict

import re
from pathlib import Path
from typing import Final, List, Mapping, Optional
import subprocess

from webilastik.utility.log import Logger
from webilastik.utility.url import Url

logger = Logger()

class ProjectRoot:
    def __init__(self) -> None:
        self.root_path: Final[Path] = Path(__file__).parent.parent.parent
        self.build_dir: Final[Path] = self.root_path / "build"
        self.deb_tree_path = self.build_dir / "deb_tree"
        self.environment_file: Final[Path] = self.root_path / "environment.yml"

        git_raw_version = subprocess.check_output(["git", "describe", "--tags",  "HEAD"], cwd=self.root_path).decode("utf8").strip()
        self.pkg_version: Final[str] = re.sub("^[a-zA-Z]+|-[^-]*$", "", git_raw_version)

        super().__init__()


class PackageSourceFile:
    def __init__(self, *, contents: bytes, target_path: Path) -> None:
        self.contents = contents
        self.target_path = target_path
        super().__init__()

    def install(self, use_cached: bool = True):
        if self.is_current():
            return
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.target_path, "wb") as f:
            _ = f.write(self.contents)

    def is_current(self) -> bool:
        if not self.target_path.exists():
            return False
        with open(self.target_path, "rb") as f:
            return f.read() == self.contents

def force_update_dir(*, source: Path, dest: Path, delete_extraneous: bool, exclude_pattern: "str | None" = None):
    if not dest.exists():
        dest.mkdir(parents=True)
    assert source.is_dir()
    assert dest.is_dir()
    _  = subprocess.check_output([
        "rsync",
        "-av",
        *(["--delete"] if delete_extraneous else []),
        *(["--exclude", exclude_pattern] if exclude_pattern else []),
        str(source).rstrip("/") + "/",
        str(dest).rstrip("/") + "/"
    ])

npm_package_mtime = 499162500.0 # mtime used by npm for reproducible builds

def _do_get_dir_effective_mtime(path: Path) -> float:
    if path.name == "__pycache__":
        return 0
    if path.suffix == "pyc":
        return 0

    out: float = 0
    for child in path.iterdir():
        if child.is_dir():
            child_mtime = _do_get_dir_effective_mtime(child)
        else:
            child_stat = child.lstat()
            child_mtime = child_stat.st_ctime if child_stat.st_mtime == npm_package_mtime else child_stat.st_mtime
        if child_mtime > out:
            out = child_mtime
    # if out != 0:
    #     logger.debug(f"mtime for {path} is {datetime.datetime.fromtimestamp(out)}")

    return out

def get_dir_effective_mtime(path: Path) -> "float":
    if not path.exists():
        return 0
    return _do_get_dir_effective_mtime(path)

def run_subprocess(
    args: List[str], env: Optional[Mapping[str, str]] = None, cwd: Optional[Path] = None
) -> "bytes | subprocess.CalledProcessError":
    try:
        return subprocess.check_output(args, env=env, cwd=cwd)
    except subprocess.CalledProcessError as e:
        return e

def git_checkout(*, url: Url, destination: Path, commit_ref: str) -> "None | Exception":
    clone_result = run_subprocess(["git", "clone", url.raw, str(destination)])
    if isinstance(clone_result, Exception):
        return clone_result

    fetch_result = run_subprocess(
        ["git", "fetch"], cwd=destination
    )
    if isinstance(fetch_result, Exception):
        return fetch_result

    checkout_result = run_subprocess(
        ["git", "checkout", commit_ref], cwd=destination
    )
    if isinstance(checkout_result, Exception):
        return checkout_result
