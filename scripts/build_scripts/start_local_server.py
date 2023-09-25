import socket
import os
import sys
import subprocess
from scripts.build_scripts import PackageSourceFile, ProjectRoot
from scripts.build_scripts.create_deb_tree import CreateDebTree, DebTree
from webilastik.config import SessionAllocatorServerConfig
from webilastik.scheduling import SerialExecutor
from webilastik.server.session_allocator import SessionAllocator

from webilastik.utility.log import Logger


logger = Logger()


class StartLocalServer:
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

    def run(self) -> "Exception | None":
        if os.geteuid() != 0:
            return Exception("Must run as root")

        logger.debug("Ensuring that app.ilastik.org points to localhost")
        if socket.gethostbyname('app.ilastik.org') != "127.0.0.1":
            return Exception("app.ilastik.org does not map to 127.0.0.1")

        logger.debug("Checking that nginx is running - it redirects requests to compute the sessions")
        if os.system("ps -ef | grep nginx | grep -q -v grep") != 0:
            return Exception("nginx doesn't seem to be running")

        logger.debug("Checking that webilastik.conf is installed in nginx's config files")
        if os.system("nginx -T | grep -q app.ilastik.org") != 0:
            return Exception("webilastik.conf does not seem to be installed in nginx configs")

        # for now this must be via www-data because that's nginx's user, and nginx must
        # be able to open the socket files that go back to the sessions, and having
        # the ssh happen for the user www-data is one way to do that
        # FIXME: investigate "-oStreamLocalBindMask=0111" in tunnel.py
        logger.debug("Checking that www-data can ssh into itself to create local sessions")
        _ = subprocess.check_call(["sudo", "-u", "www-data", "-g", "www-data", "ssh" "-oBatchMode=yes" "www-data@localhost", "true"])

        result = self.deb_tree.fake_install(action="install", session_allocator_server_config=self.session_allocator_server_config)
        if isinstance(result, Exception):
            return result

        logger.debug(f"Reloading systemd configs")
        _ = subprocess.check_call(["systemctl", "daemon-reload"])
        logger.debug(f"Enabling webilastik.service")
        _ = subprocess.check_call(["systemctl", "enable", "webilastik.service"])
        logger.debug(f"Restarting webilastik service")
        _ = subprocess.check_call(["systemctl", "restart", "webilastik.service"])


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


    result = StartLocalServer(
        project_root=project_root, deb_tree=deb_tree, session_allocator_server_config=session_allocator_server_config
    ).run()
    if isinstance(result, Exception):
        raise result

