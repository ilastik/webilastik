from pathlib import Path
import shutil
import subprocess
from typing import Final, Optional

from build_scripts import ProjectRoot, get_dir_effective_mtime, run_subprocess
from webilastik.utility.log import Logger

logger = Logger()

class CondaEnvironment:
    def __init__(self, path: Path, _private_marker: None) -> None:
        self.path : Final[Path] = path
        self.mtime: Final[float] = get_dir_effective_mtime(self.path)
        super().__init__()

class CreateCondaEnvironment:
    def __init__(self, project_root: ProjectRoot) -> None:
        self.project_root = project_root
        self.conda_env_path = self.project_root.build_dir / "webilastik_conda_env"
        super().__init__()

    def run(self, *, use_cache: bool = True) -> "CondaEnvironment | Exception":
        cached = use_cache and self.cached()
        if cached:
            return cached

        if self.conda_env_path.exists():
            logger.info(f"Removing old conda env dir at {self.conda_env_path}")
            shutil.rmtree(self.conda_env_path)

        logger.info(f"Creating conda env at {self.conda_env_path} at {self.project_root.environment_file}")
        mamba_result = run_subprocess([
            "mamba", "env", "create", "--prefix", str(self.conda_env_path), "-f", str(self.project_root.environment_file)
        ])
        if isinstance(mamba_result, Exception):
            return mamba_result

        return CondaEnvironment(path=self.conda_env_path, _private_marker=None)

    def cached(self) -> Optional[CondaEnvironment]:
        if get_dir_effective_mtime(self.conda_env_path) > self.project_root.environment_file.lstat().st_mtime:
            logger.info(f"Using cached conda environment at {self.conda_env_path}")
            return CondaEnvironment(path=self.conda_env_path, _private_marker=None)
        return None

if __name__ == "__main__":
    result = CreateCondaEnvironment(project_root=ProjectRoot()).run(use_cache=True)
    if isinstance(result, Exception):
        raise result