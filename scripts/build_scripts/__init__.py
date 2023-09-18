# pyright: strict

from dataclasses import dataclass
import re
from pathlib import Path
from sys import stderr
from typing import Final, Sequence
import subprocess

PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent

try:
    git_raw_version = subprocess.check_output(["git", "describe", "--tags",  "HEAD"], cwd=PROJECT_ROOT).decode("utf8").strip()
except Exception as e:
    print(f"Could not run git describe: {e}", file=stderr)
    exit(1)

PKG_VERSION: Final[str] = re.sub("^[a-zA-Z]+|-[^-]*$", "", git_raw_version)

BUILD_DIR: Final[Path] = PROJECT_ROOT / "build"
PKG_NAME: Final[str] = f"webilastik_{PKG_VERSION}"
ENV_PATH: Final[Path] = BUILD_DIR / "webilastik_conda_env"
ENV_CHECKSUM_PATH: Final[Path] = BUILD_DIR / "environment.yml.sha256"
PACKED_ENV_PATH: Final[Path] = Path(str(ENV_PATH) + ".tar.gz")
WEBILASTIK_UNIT_INSTALL_PATH: Final[Path] = Path("/lib/systemd/system/webilastik.service")
WEBILASTIK_DEV_UNIT_CONFIG_DIR: Final[Path] = Path("/etc/systemd/system/webilastik.service.d")
DEB_PKG_PATH: Final[Path] = BUILD_DIR / f"{PKG_NAME}.deb"
REMOTE_PACKAGE_PATH: Final[Path] = Path(f"/home/ubuntu/{PKG_NAME}.deb")
NEUROGLANCER_GIT_DIR: Final[Path] = BUILD_DIR / "neuroglancer"
NEUROGLANCER_BUILD_PATH: Final[Path] = NEUROGLANCER_GIT_DIR / "dist/min"
NEUROGLANCER_BUNDLE_PATH: Final[Path] = NEUROGLANCER_BUILD_PATH / "main.bundle.js"
OVERLAY_DIR: Final[Path] = PROJECT_ROOT / "overlay"
OVERLAY_BUNDLE_PATH: Final[Path] = OVERLAY_DIR / "build/inject_into_neuroglancer.js"
SOURCES_DIRS: Final[Sequence[Path]] = [
    PROJECT_ROOT / dir_name
    for dir_name in ("webilastik", "caching", "executor_getters")
]

class ProjectRoot:
    def __init__(self) -> None:
        self.root_path: Final[Path] = Path(__file__).parent.parent.parent
        print(f"root path: {self.root_path}")
        self.build_dir: Final[Path] = self.root_path / "build"
        self.environment_file: Final[Path] = self.root_path / "environment.yml"
        super().__init__()


@dataclass
class OverlayBundle:
    path: Final[Path]


def force_update_dir(*, source: Path, dest: Path, exclude_pattern: "str | None" = None):
    assert source.is_dir()
    assert dest.is_dir()
    _  = subprocess.check_output([
        "rsync",
        "-av",
        "--delete",
        *(["--exclude", exclude_pattern] if exclude_pattern else []),
        str(source).rstrip("/") + "/",
        str(dest).rstrip("/") + "/"
    ])


def _do_get_dir_effective_mtime(path: Path) -> float:
    return max(
        _do_get_dir_effective_mtime(child) if child.is_dir() else child.lstat().st_mtime
        for child in path.iterdir()
    )

def get_dir_effective_mtime(path: Path) -> "float":
    if not path.exists():
        return 0
    return _do_get_dir_effective_mtime(path)