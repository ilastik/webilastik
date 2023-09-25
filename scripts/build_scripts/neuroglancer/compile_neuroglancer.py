# pyright: strict

from pathlib import Path
import shutil
from typing import Final
from scripts.build_scripts import ProjectRoot, get_effective_mtime, run_subprocess
from scripts.build_scripts.neuroglancer.fetch_neuroglancer_source import FetchNeuroglancerSource, NeuroglancerSource
from webilastik.utility.log import Logger


logger = Logger()

class NeuroglancerDistribution:
    def __init__(self, *, bundle_path: Path, project_root: ProjectRoot, _private_marker: None) -> None:
        super().__init__()
        self.bundle_path: Final[Path] = bundle_path
        self.installation_dir = project_root.deb_tree_path / "opt/webilastik/public/nehuba"
        self.mtime = get_effective_mtime(self.bundle_path)

    def install(self, use_cache: bool = True):
        if use_cache and self.is_current():
            return
        logger.debug('Copying nehuba to public dir')
        self.installation_dir.mkdir(parents=True)
        shutil.copy(self.bundle_path, self.installation_dir)

    def is_current(self) -> bool:
        target_bundle_path = self.installation_dir / self.bundle_path.name
        if not target_bundle_path.exists() or self.mtime > get_effective_mtime(target_bundle_path):
            return False
        return True

class BuildNeuroglancer:
    def __init__(self, project_root: ProjectRoot, ng_source: NeuroglancerSource) -> None:
        self.project_root: Final[ProjectRoot] = project_root
        self.ng_source: Final[NeuroglancerSource] = ng_source
        self.dist_path: Final[Path] = self.ng_source.path / "dist/min"
        self.output_bundle_path: Final[Path] = project_root.build_dir / "neuroglancer.bundle.js"
        super().__init__()

    def run(self, use_cache: bool = True) -> "NeuroglancerDistribution | Exception":
        cache = use_cache and self.cached()
        if cache:
            return cache

        npm_ci_result = run_subprocess(["npm", "ci"], cwd=self.ng_source.path)
        if isinstance(npm_ci_result, Exception):
            return npm_ci_result

        if self.dist_path.exists():
            shutil.rmtree(self.dist_path)
        build_result = run_subprocess(
            ["npm", "run", "build-with-ilastik-overlay"],
            env={"ILASTIK_URL": "https://app.ilastik.org/"},
            cwd=self.ng_source.path,
        )
        if isinstance(build_result, Exception):
            return build_result

        shutil.move(self.dist_path / "main.bundle.js", self.output_bundle_path)
        shutil.rmtree(self.dist_path)

        return NeuroglancerDistribution(bundle_path=self.output_bundle_path, project_root=self.project_root, _private_marker=None)

    def cached(self) -> "NeuroglancerDistribution | None | Exception":
        if not self.output_bundle_path.exists() or get_effective_mtime(self.ng_source.path) > self.output_bundle_path.stat().st_mtime:
            return None
        logger.info("Using cached neuroglancer bundle dist")
        return NeuroglancerDistribution(bundle_path=self.output_bundle_path, project_root=self.project_root, _private_marker=None)

    @classmethod
    def execute(cls) -> "NeuroglancerDistribution | Exception":
        project_root = ProjectRoot()
        ng_source = FetchNeuroglancerSource(project_root=project_root).run()
        if isinstance(ng_source, Exception):
            return  ng_source #FIXME?
        return BuildNeuroglancer(project_root=project_root, ng_source=ng_source).run()

if __name__ == "__main__":
    result = BuildNeuroglancer.execute()
    if isinstance(result, Exception):
        raise result