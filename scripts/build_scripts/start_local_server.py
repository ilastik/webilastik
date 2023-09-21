import socket
import os
import subprocess
import textwrap
from build_scripts import PackageSourceFile, ProjectRoot
from build_scripts.create_deb_tree import CreateDebTree, DebTree
from webilastik.config import SessionAllocatorServerConfig
from webilastik.scheduling import SerialExecutor
from webilastik.server.session_allocator import SessionAllocator

from webilastik.utility.log import Logger


logger = Logger()

class LocalServerSystemdServiceDropIn(PackageSourceFile):
    def __init__(self, *, project_root: ProjectRoot) -> None:
        super().__init__(
            target_path=project_root.systemd_unit_config_dir / "output_to_tty.conf",
            contents=textwrap.dedent(f"""
                [Service]
                TTYPath={subprocess.check_output(["tty"]).decode("utf8").strip()}
                StandardOutput=tty
                StandardError=inherit
            """[1:]).encode("utf8")
        )

class StartLocalServer:
    def __init__(self, project_root: ProjectRoot, deb_tree: DebTree) -> None:
        self.project_root = project_root
        self.deb_tree = deb_tree
        super().__init__()

    def run(self) -> "Exception | None":
        logger.debug("Ensuring that app.ilastik.org points to localhost")
        if socket.gethostbyname('app.ilastik.org') != "127.0.0.1":
            return Exception("app.ilastik.org does not map to 127.0.0.1")

        logger.debug("Checking that nginx is running - it redirects requests to compute the sessions")
        if os.system("ps -ef | grep -q nginx | grep -v grep") != 0:
            return Exception("nginx doesn't seem to be running")

        logger.debug("Checking that webilastik.conf is installed in nginx's config files")
        if os.system("nginx -T | grep -q app.ilastik.org") != 0:
            return Exception("webilastik.conf does not seem to be installed in nginx configs")

        # for now this must be via www-data because that's nginx's user, and nginx must
        # be able to open the socket files that go back to the sessions, and having
        # the ssh happen for the user www-data is one way to do that
        # FIXME: investigate "-oStreamLocalBindMask=0111" in tunnel.py
        logger.debug("Checking that www-data can ssh into itself to create local sessions")
        if os.system("sudo -u www-data -g www-data ssh -oBatchMode=yes www-data@localhost echo success") != 0:
            return Exception("www-data can't ssh to itself, so local sessions won't be able to create tunnels")

        logger.debug("Installing the drop in file to log to this tty")
        LocalServerSystemdServiceDropIn(project_root=project_root).install()




if __name__ == "__main__":
    project_root = ProjectRoot()
    executor = SerialExecutor()
    deb_tree  = CreateDebTree.execute(project_root=project_root, executor=executor)
    if isinstance(deb_tree, Exception):
        raise deb_tree
    result = StartLocalServer(project_root=project_root, deb_tree=deb_tree)
    if isinstance(result, Exception):
        raise result

