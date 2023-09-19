#pyright: strict

from pathlib import Path
import shutil
from typing import Final
from build_scripts import ProjectRoot, get_dir_effective_mtime, run_subprocess
from webilastik.utility.log import Logger

logger = Logger()

class OverlayBundle:
    def __init__(self, bundle_path: Path, _private_marker: None) -> None:
        self.bundle_path: Final[Path] = bundle_path
        self.bundle_src_map_path: Final[Path] = Path(str(bundle_path) + ".map")
        super().__init__()

class CompileOverlay:
    def __init__(self, project_root: ProjectRoot) -> None:
        self.project_root: Final[ProjectRoot] = project_root
        self.overlay_source_dir: Final[Path] = project_root.root_path / "overlay"
        self.build_path: Final[Path] = self.overlay_source_dir / "build"
        self.output_bundle: Final[Path] = self.project_root.build_dir / "inject_into_neuroglancer.js"
        self.output_src_map: Final[Path] = self.project_root.build_dir / "inject_into_neuroglancer.js.map"
        super().__init__()

    def run(self, use_cache: bool = True) -> "OverlayBundle | Exception":
        cache = use_cache and self.cached()
        if cache:
            return cache

        npm_ci_result = run_subprocess(
            ["npm", "ci"], cwd=self.overlay_source_dir
        )
        if isinstance(npm_ci_result, Exception):
            return npm_ci_result
        bundle_result = run_subprocess(["npm", "run", "bundle-ng-inject"], cwd=self.overlay_source_dir)
        if isinstance(bundle_result, Exception):
            return bundle_result
        shutil.move(self.build_path / "inject_into_neuroglancer.js", self.output_bundle)
        shutil.move(self.build_path / "inject_into_neuroglancer.js.map", self.output_src_map)
        shutil.rmtree(self.build_path)

        return OverlayBundle(bundle_path=self.output_bundle, _private_marker=None)

    def cached(self) -> "OverlayBundle | Exception | None":
        if not self.output_bundle.exists() or not self.output_src_map.exists():
            logger.warn("Some files don't exist")
            return None
        source_mtime = get_dir_effective_mtime(self.overlay_source_dir)
        if self.output_bundle.lstat().st_mtime < source_mtime:
            logger.warn("Bundle is old")
            return None
        if self.output_src_map.lstat().st_mtime < source_mtime:
            logger.warn("Map is old")
            return None
        logger.info("Using cached overlay bundle")
        return OverlayBundle(bundle_path=self.output_bundle, _private_marker=None)

if __name__ == "__main__":
    project_root = ProjectRoot()
    overlay_bundle_result = CompileOverlay(project_root=project_root).run()
    if isinstance(overlay_bundle_result, Exception):
        raise overlay_bundle_result #FIXME?