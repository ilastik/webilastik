# pyright: strict

import os
import subprocess

from scripts.build_scripts import ProjectRoot
from scripts.build_scripts.create_deb_tree import DebTree
from webilastik.config import SessionAllocatorServerConfig
from webilastik.utility.log import Logger

logger = Logger()

class StopLocalServer:
    def __init__(
        self,
        *,
        project_root: ProjectRoot,
        deb_tree: DebTree,
        session_allocator_server_config: SessionAllocatorServerConfig,
    ) -> None:
        self.project_root = project_root
        self.deb_tree = deb_tree
        self.session_allocator_server_config = session_allocator_server_config
        super().__init__()

    def run(self, use_cache: bool = True) -> "None | Exception":
        if os.geteuid() != 0:
            return Exception("Must run as root")

        logger.debug(f"Stopping webilastik.service")
        _ = subprocess.check_call(["systemctl", "stop", "webilastik.service"])
        _ = subprocess.check_call(["systemctl", "reset-failed", "webilastik.service"])

        result = self.deb_tree.fake_install(action="uninstall", session_allocator_server_config=self.session_allocator_server_config)
        if isinstance(result, Exception):
            return result

        logger.debug(f"Killing any lingering compute sessions")
        _ = os.system("ps -ef | grep ws_pixel_classification_workflow.py | awk '{print $2}' | sudo xargs kill -9 || true")
        logger.debug(f"Killing any lingering ssh tunnels")
        _ = os.system("ps -ef | ag ssh.*batchmode | awk '{print $2}' | sudo xargs kill -9 || true")