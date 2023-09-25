# pyright: strict

import os
import sys
import subprocess

from scripts.build_scripts import ProjectRoot
from scripts.build_scripts.create_deb_tree import CreateDebTree, DebTree
from webilastik.config import SessionAllocatorServerConfig
from webilastik.scheduling import SerialExecutor
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
        _ = os.system("systemctl stop webilastik.service")
        _ = os.system("systemctl reset-failed webilastik.service")
        _ = os.system("systemctl disable webilastik.service")

        result = self.deb_tree.fake_install(action="uninstall", session_allocator_server_config=self.session_allocator_server_config)
        if isinstance(result, Exception):
            return result

        logger.debug(f"Killing any lingering compute sessions")
        _ = os.system("ps -ef | grep ws_pixel_classification_workflow.py | awk '{print $2}' | sudo xargs kill -9 || true")
        logger.debug(f"Killing any lingering ssh tunnels")
        _ = os.system("ps -ef | ag ssh.*batchmode | awk '{print $2}' | sudo xargs kill -9 || true")

if __name__ == "__main__":
    project_root = ProjectRoot()
    executor = SerialExecutor()

    session_allocator_server_config = SessionAllocatorServerConfig.from_env()
    if isinstance(session_allocator_server_config, Exception):
        raise session_allocator_server_config

    deb_tree  = CreateDebTree.execute(project_root=project_root, executor=executor)
    if isinstance(deb_tree, Exception):
        raise deb_tree

    if os.geteuid() != 0:
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!1 {__loader__.name}")
        exit(subprocess.check_call(
            ["sudo", "--preserve-env", sys.executable, "-m", __loader__.name, *sys.argv]
        ))

    result = StopLocalServer(
        project_root=project_root, deb_tree=deb_tree, session_allocator_server_config=session_allocator_server_config
    ).run()
    if isinstance(result, Exception):
        raise result

