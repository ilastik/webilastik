from pathlib import Path
import shutil
import subprocess
from typing import Final, Optional
from concurrent.futures import Future

from build_scripts import ProjectRoot, run_subprocess
from build_scripts.create_conda_env import CondaEnvironment, CreateCondaEnvironment
from webilastik.utility.log import Logger

logger = Logger()

class PackedCondaEnv:
    def __init__(self, path: Path, _private_marker: None) -> None:
        self.path: Final[Path] = path
        self.mtime = path.lstat().st_mtime
        super().__init__()

class CreatePackedCondaEnv:
    def __init__(self, project_root: ProjectRoot, conda_env: CondaEnvironment) -> None:
        self.project_root: Final[ProjectRoot] = project_root
        self.conda_env = conda_env
        self.packed_env_path = Path(str(self.conda_env.path) + ".tar.gz")
        super().__init__()

    def run(self, use_cache: bool = True) -> "PackedCondaEnv | Exception":
        cache = use_cache and self.cached()
        if cache:
            logger.info(f"Using cached packed env at {self.packed_env_path}")
            return cache
        if self.packed_env_path.exists():
            logger.info(f"Deleting old packed env at {self.packed_env_path}")
            self.packed_env_path.unlink()

        pack_result = run_subprocess([
            "conda", "pack", "-p", str(self.conda_env.path), "-o", str(self.packed_env_path)
        ])
        if isinstance(pack_result, Exception):
            return pack_result

        return PackedCondaEnv(path=self.packed_env_path, _private_marker=None)

    def cached(self) -> Optional[PackedCondaEnv]:
        if self.packed_env_path.exists() and self.packed_env_path.lstat().st_mtime > self.conda_env.mtime:
            return PackedCondaEnv(path=self.packed_env_path, _private_marker=None)
        return None

if __name__ == "__main__":
    project_root = ProjectRoot()
    conda_env = CreateCondaEnvironment(project_root=project_root).run()
    if isinstance(conda_env, Exception):
        raise conda_env #FIXME?

    packed_env = CreatePackedCondaEnv(project_root=ProjectRoot(), conda_env=conda_env).run()
    if isinstance(packed_env, Exception):
        raise packed_env #FIXME?