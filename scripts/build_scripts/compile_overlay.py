#pyright: strict

from pathlib import Path
import shutil
from typing import Final
from scripts.build_scripts import ProjectRoot, get_effective_mtime, run_subprocess
from webilastik.utility.log import Logger

logger = Logger()

class OverlayBundle:
    def __init__(self, bundle_path: Path, project_root: ProjectRoot, _private_marker: None) -> None:
        self.bundle_path: Final[Path] = bundle_path
        self.installation_dir = project_root.deb_tree_path / "opt/webilastik/public/js"
        self.bundle_mtime = get_effective_mtime(bundle_path)
        self.src_map_path: Final[Path] = Path(str(bundle_path) + ".map")
        self.src_map_mtime = get_effective_mtime(self.src_map_path)
        self.mtime = max(self.bundle_mtime, self.src_map_mtime)
        super().__init__()

    def install(self, use_cache: bool = True):
        if use_cache and self.is_current():
            return
        logger.info("Copying overlay bundle to package tree")
        self.installation_dir.mkdir(parents=True)
        shutil.copy(self.bundle_path, self.installation_dir)
        shutil.copy(self.src_map_path, self.installation_dir)

    def is_current(self) -> bool:
        target_bundle_path = self.installation_dir / self.bundle_path.name
        target_src_map_path = self.installation_dir / self.src_map_path.name
        if not target_bundle_path.exists() or self.bundle_mtime > get_effective_mtime(target_bundle_path):
            logger.debug("overlay is not current!! 1")
            return False
        if not target_src_map_path.exists() or self.src_map_mtime > get_effective_mtime(target_src_map_path):
            logger.debug("overlay is not current!! 2")
            return False
        return True

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

        npm_ci_result = run_subprocess(["npm", "ci"], cwd=self.overlay_source_dir)
        if isinstance(npm_ci_result, Exception):
            return npm_ci_result
        bundle_result = run_subprocess(["npm", "run", "bundle-ng-inject"], cwd=self.overlay_source_dir)
        if isinstance(bundle_result, Exception):
            return bundle_result
        shutil.move(self.build_path / "inject_into_neuroglancer.js", self.output_bundle)
        shutil.move(self.build_path / "inject_into_neuroglancer.js.map", self.output_src_map)
        shutil.rmtree(self.build_path)

        return OverlayBundle(bundle_path=self.output_bundle, project_root=self.project_root, _private_marker=None)

    def cached(self) -> "OverlayBundle | Exception | None":
        if not self.output_bundle.exists() or not self.output_src_map.exists():
            return None
        source_mtime = get_effective_mtime(self.overlay_source_dir)
        if get_effective_mtime(self.output_bundle) < source_mtime:
            return None
        if get_effective_mtime(self.output_src_map) < source_mtime:
            return None
        logger.info("Using cached overlay bundle")
        return OverlayBundle(bundle_path=self.output_bundle, project_root=self.project_root, _private_marker=None)

if __name__ == "__main__":
    project_root = ProjectRoot()
    overlay_bundle_result = CompileOverlay(project_root=project_root).run()
    if isinstance(overlay_bundle_result, Exception):
        raise overlay_bundle_result #FIXME?