# pyright: strict

import os
from pathlib import Path

from build_scripts import ProjectRoot, run_subprocess
from build_scripts.create_deb_tree import DebTree


class StopLocalServer:
    def __init__(self, project_root: ProjectRoot, deb_tree: DebTree) -> None:
        self.project_root = project_root
        self.deb_tree = deb_tree
        super().__init__()

    def run(self, use_cache: bool = True) -> "None | Exception":
        if os.geteuid() != 0:
            return Exception("Must run as root")

        result = run_subprocess(["systemctl", "stop", "webilastik.service"])
        if isinstance(result, Exception):
            return result
        result = run_subprocess(["systemctl", "reset-failed", "webilastik.service"])
        if isinstance(result, Exception):
            return result
        self.project_root.systemd_unit_config_dir.joinpath("output_to_tty.conf").unlink(missing_ok=True)
        self.project_root.systemd_unit_install_path.unlink(missing_ok=True)
        Path("/opt/webilastik").unlink(missing_ok=True)

        _ = os.system("ps -ef | grep ws_pixel_classification_workflow.py | awk '{print $2}' | xargs kill -9")
        _ = os.system("ps -ef | ag ssh.*batchmode | awk '{print $2}' | sudo xargs kill -9")