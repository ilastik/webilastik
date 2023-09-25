# pyright: strict

from pathlib import Path
import shutil
from typing import Final, Mapping

from scripts.build_scripts import ProjectRoot, get_effective_mtime, git_checkout, run_subprocess
from webilastik.utility.log import Logger
from webilastik.utility.url import Url

logger = Logger()

class NeuroglancerSource:
    def __init__(self, *, path: Path, _private_marker: None) -> None:
        self.path: Final[Path] = path
        self.mtime: Final[float] = get_effective_mtime(path)
        super().__init__()

class FetchNeuroglancerSource:
    def __init__(self, project_root: ProjectRoot) -> None:
        self.project_root = project_root
        self.commit_hash: Final[str] = "0edaf528000268daea3dd1d1781e53527642b85d"
        self.source_dir: Final[Path] = self.project_root.build_dir / "neuroglancer_source"
        self.git_env: Final[Mapping[str, str]] = {"GIT_HOME": str(self.source_dir)}
        super().__init__()

    def run(self, use_cache: bool = True) -> "NeuroglancerSource | Exception":
        cache = use_cache and self.cached()
        if cache:
            return cache

        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)

        checkout_result = git_checkout(
            url=Url.parse_or_raise("https://github.com/ilastik/neuroglancer"),
            destination=self.source_dir,
            commit_ref=self.commit_hash,
        )
        if isinstance(checkout_result, Exception):
            return checkout_result

        return NeuroglancerSource(path=self.source_dir, _private_marker=None)

    def cached(self) -> "NeuroglancerSource | None | Exception":
        if not self.source_dir.exists(): #FIXME
            return None
        git_revparse_result = run_subprocess(["git", "rev-parse", "HEAD"], cwd=self.source_dir)
        if isinstance(git_revparse_result, Exception):
            return git_revparse_result
        parsed_hash = git_revparse_result.decode("utf8").strip()
        if parsed_hash != self.commit_hash:
            return Exception(f"Expected {self.source_dir} to be at {self.commit_hash} but found {parsed_hash}")
        logger.info(f"Using cached neuroglancer source code at {self.source_dir}")
        return NeuroglancerSource(path=self.source_dir, _private_marker=None)


if __name__ == "__main__":
    fetch_result = FetchNeuroglancerSource(project_root=ProjectRoot()).run()
    if isinstance(fetch_result, Exception):
        raise fetch_result #FIXME