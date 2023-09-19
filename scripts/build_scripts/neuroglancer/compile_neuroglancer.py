from pathlib import Path
import shutil
from typing import Final
from build_scripts import ProjectRoot, get_dir_effective_mtime, run_subprocess
from build_scripts.neuroglancer.fetch_neuroglancer_source import FetchNeuroglancerSource, NeuroglancerSource
from webilastik.utility.log import Logger


logger = Logger()

class NeuroglancerDistribution:
    def __init__(self, *, bundle_path: Path, _private_marker: None) -> None:
        super().__init__()
        self.bundle_path: Final[Path] = bundle_path

class BuildNeuroglancer:
    def __init__(self, project_root: ProjectRoot, ng_source: NeuroglancerSource) -> None:
        self.project_root: Final[ProjectRoot] = project_root
        self.ng_source: Final[NeuroglancerSource] = ng_source
        self.dist_path: Final[Path] = self.ng_source.path / "dist/min"
        self.bundle_path: Final[Path] = project_root.build_dir / "neuroglancer.bundle.js"
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

        shutil.move(self.dist_path / "main.bundle.js", self.bundle_path)
        shutil.rmtree(self.dist_path)

        return NeuroglancerDistribution(bundle_path=self.bundle_path, _private_marker=None)

    def cached(self) -> "NeuroglancerDistribution | None | Exception":
        if self.bundle_path.stat().st_mtime > get_dir_effective_mtime(self.ng_source.path):
            logger.info("Using cached neuroglancer bundle dist")
            return NeuroglancerDistribution(bundle_path=self.bundle_path, _private_marker=None)
        return None

if __name__ == "__main__":
    project_root = ProjectRoot()
    ng_source = FetchNeuroglancerSource(project_root=project_root).run()
    if isinstance(ng_source, Exception):
        raise ng_source #FIXME?
    neuroglancer_dist = BuildNeuroglancer(project_root=project_root, ng_source=ng_source).run()
    if isinstance(neuroglancer_dist, Exception):
        raise neuroglancer_dist #FIXME?