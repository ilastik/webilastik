# pyright: strict

import os
import sys
import subprocess

from scripts.build_scripts import ProjectRoot
from scripts.build_scripts.create_deb_tree import CreateDebTree
from webilastik.scheduling import SerialExecutor
from webilastik.utility.log import Logger

logger = Logger()

class StopLocalServer:
    def __init__(self) -> None:
        super().__init__()

    def run(self, use_cache: bool = True) -> "None | Exception":
        if os.geteuid() != 0:
            return Exception("Must run as root")

        logger.debug(f"Killing any lingering compute sessions")
        _ = os.system("ps -ef | grep ws_pixel_classification_workflow.py | awk '{print $2}' | sudo xargs kill -9 || true")
        logger.debug(f"Killing any lingering ssh tunnels")
        _ = os.system("ps -ef | ag ssh.*batchmode | awk '{print $2}' | sudo xargs kill -9 || true")

if __name__ == "__main__":
    project_root = ProjectRoot()
    executor = SerialExecutor()

    deb_tree  = CreateDebTree.execute(project_root=project_root, executor=executor)
    if isinstance(deb_tree, Exception):
        raise deb_tree

    if os.geteuid() != 0:
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!1 {__loader__.name}")
        exit(subprocess.check_call(
            ["sudo", "--preserve-env", sys.executable, "-m", __loader__.name, *sys.argv]
        ))

    result = StopLocalServer().run()
    if isinstance(result, Exception):
        raise result

