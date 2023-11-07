# pyright: strict

from typing import Final
from scripts.build_scripts import ProjectRoot
from scripts.build_scripts.compile_overlay import OverlayBundle
from scripts.build_scripts.neuroglancer.compile_neuroglancer import NeuroglancerDistribution


class PublicDir:
    def __init__(
        self,
        *,
        project_root: ProjectRoot,
        overlay_bundle: OverlayBundle,
        neuroglancer_bundle: NeuroglancerDistribution,
    ) -> None:
        self.project_root: Final[ProjectRoot] = project_root
        super().__init__()