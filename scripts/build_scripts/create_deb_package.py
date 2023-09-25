# pyright: strict

from concurrent.futures import Executor
import shutil
from pathlib import Path
from typing import Final
from scripts.build_scripts.create_deb_tree import CreateDebTree, DebTree

from scripts.build_scripts import ProjectRoot, get_effective_mtime, run_subprocess
from webilastik.scheduling import SerialExecutor
from webilastik.utility.log import Logger

logger = Logger()


class DebPackage:
    def __init__(self, path: Path, _private_marker: None) -> None:
        self.path: Final[Path] = path
        self.mtime: Final[float] = get_effective_mtime(self.path)
        super().__init__()


class CreateDebPackage:
    def __init__(
        self,
        *,
        project_root: ProjectRoot,
        deb_tree: DebTree,
    ) -> None:
        self.project_root = project_root
        self.deb_tree = deb_tree
        self.deb_file_output = project_root.build_dir / project_root.pkg_name
        super().__init__()

    def run(self, use_cache: bool = True) -> "DebPackage | Exception":
        cache = use_cache and self.cached()
        if cache:
            return cache

        logger.debug("Ensuring no changes in the working tree before packing to .deb")
        git_status_result = run_subprocess(
            ["git", "status", "--porcelain"]
        )
        if isinstance(git_status_result, Exception):
            return git_status_result
        status_lines = [line for line in git_status_result.decode("utf8").strip().split("\n") if line]
        if len(status_lines) != 0:
            return Exception(f"There are some modified or untracked files in the working tree: {status_lines}")

        git_revparse_head_result = run_subprocess(["git", "rev-parse", "HEAD"])
        git_revparse_originMaster_result = run_subprocess(["git", "rev-parse", "origin/master"])
        if isinstance(git_revparse_head_result, Exception):
            return git_revparse_head_result
        if isinstance(git_revparse_originMaster_result, Exception):
            return git_revparse_originMaster_result
        if git_revparse_head_result.decode("utf8") != git_revparse_originMaster_result.decode("utf8"):
            return Exception(f"Current revision has not been pushed to origin")

        dpkg_deb_result = run_subprocess(
            ["dpkg-deb", "--build", "-z2", str(self.project_root.deb_tree_path), str(self.deb_file_output)]
        )
        if isinstance(dpkg_deb_result, Exception):
            return dpkg_deb_result

        return DebPackage(path=self.deb_file_output, _private_marker=None)

    def cached(self) -> "DebPackage | Exception | None":
        if not self.deb_file_output.exists():
            return None
        out = DebPackage(path=self.deb_file_output, _private_marker=None)
        if self.deb_tree.mtime > out.mtime:
            return None
        return out

    def clean(self):
        shutil.rmtree(path=self.project_root.deb_tree_path)

    @classmethod
    def execute(cls, project_root: ProjectRoot, executor: Executor) -> "DebPackage | Exception":
        deb_tree = CreateDebTree.execute(project_root=project_root, executor=executor)
        if isinstance(deb_tree, Exception):
            return deb_tree
        return CreateDebPackage(project_root=project_root, deb_tree=deb_tree).run()


if __name__ == "__main__":
    project_root = ProjectRoot()
    executor = SerialExecutor()
    deb_package = CreateDebPackage.execute(project_root=project_root, executor=executor)
    if isinstance(deb_package, Exception):
        raise deb_package