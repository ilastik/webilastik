#pyright: strict

from pathlib import Path
from typing import Final
from scripts.build_scripts import ProjectRoot, get_effective_mtime, run_subprocess
from webilastik.utility.log import Logger

logger = Logger()

class OverlayBundle:
    def __init__(self, bundle_path: Path, project_root: ProjectRoot, _private_marker: None) -> None:
        self.bundle_path: Final[Path] = bundle_path
        self.bundle_mtime = get_effective_mtime(bundle_path)
        self.src_map_path: Final[Path] = Path(str(bundle_path) + ".map")
        self.src_map_mtime = get_effective_mtime(self.src_map_path)
        self.mtime = max(self.bundle_mtime, self.src_map_mtime)
        super().__init__()

class CompileOverlay:
    def __init__(self, project_root: ProjectRoot) -> None:
        self.project_root: Final[ProjectRoot] = project_root
        self.public_js = self.project_root.public_dir / "js"
        self.output_bundle: Final[Path] = self.public_js / "inject_into_neuroglancer.js"
        self.output_src_map: Final[Path] = self.public_js / "inject_into_neuroglancer.js.map"
        super().__init__()

    def run(self, use_cache: bool = True) -> "OverlayBundle | Exception":
        cache = use_cache and self.cached()
        if cache:
            return cache

        npm_ci_result = run_subprocess(["npm", "ci"], cwd=self.project_root.overlay_src_dir)
        if isinstance(npm_ci_result, Exception):
            return npm_ci_result

        overlay_typecheck = run_subprocess(["npx", "tsc", "--noEmit"], cwd=self.project_root.overlay_src_dir)
        if isinstance(overlay_typecheck, Exception):
            return Exception(f"Typechecking overlay failed: {overlay_typecheck}")

        overlay_build = run_subprocess(
            [
                "npx",
                "esbuild",
                "src/injection/inject_into_neuroglancer.ts",
                "--bundle",
                "--loader:.ts=ts",
                "--sourcemap",
                f"--outfile={self.output_bundle.as_posix()}",
            ],
            cwd=self.project_root.overlay_src_dir,
        )
        if isinstance(overlay_build, Exception):
            return Exception(f"building overlay failed: {overlay_build}")

        return OverlayBundle(bundle_path=self.output_bundle, project_root=self.project_root, _private_marker=None)

    def cached(self) -> "OverlayBundle | Exception | None":
        if not self.output_bundle.exists() or not self.output_src_map.exists():
            return None
        source_mtime = get_effective_mtime(self.project_root.overlay_src_dir)
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