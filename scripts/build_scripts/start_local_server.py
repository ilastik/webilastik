# pyright: strict

import socket
import os
import subprocess
import json

from scripts.build_scripts import ProjectRoot
from scripts.build_scripts.create_deb_tree import CreateDebTree, DebTree
from webilastik.config import WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG, SessionAllocatorServerConfig
from webilastik.scheduling import SerialExecutor

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
        logger.debug("Ensuring that app.ilastik.org points to localhost")
        if socket.gethostbyname('app.ilastik.org') != "127.0.0.1":
            return Exception("app.ilastik.org does not map to 127.0.0.1")

        logger.debug("Checking that nginx is running - it redirects requests to compute the sessions")
        if os.system("ps -ef | grep nginx | grep -q -v grep") != 0:
            return Exception("nginx doesn't seem to be running")

        logger.debug("Checking that webilastik.conf is installed in nginx's config files")
        if os.system("sudo nginx -T | grep -q app.ilastik.org") != 0:
            return Exception("webilastik.conf does not seem to be installed in nginx configs")

        # for now this must be via www-data because that's nginx's user, and nginx must
        # be able to open the socket files that go back to the sessions, and having
        # the ssh happen for the user www-data is one way to do that
        # FIXME: investigate "-oStreamLocalBindMask=0111" in tunnel.py
        logger.debug("Checking that www-data can ssh into itself to create local sessions")
        _ = subprocess.check_call([
            "sudo", "-u", "www-data", "-g", "www-data", "ssh" "-oBatchMode=yes" "www-data@localhost", "true"
        ])

        myenv = {
            # FIXME/BUG: aiohttp must be told where certs are when running from packed environment
            "SSL_CERT_DIR":  "/etc/ssl/certs/",
            "REQUESTS_CA_BUNDLE":  "/etc/ssl/certs/ca-certificates.crt",
            # "PYTHONPATH":  str(self.deb_tree.pythonpath),
            WEBILASTIK_SESSION_ALLOCATOR_SERVER_CONFIG: json.dumps(self.session_allocator_server_config.to_dto().to_json_value()),
        }
        import pprint
        print("-----------------")
        pprint.pprint(myenv)
        print("+++++++++++++++++")

        server_process = subprocess.Popen(
            [
                "sudo",
                "-E",
                "-u", "www-data",
                "-g", "www-data",
                str(self.deb_tree.python_bin_path),
                "-B",
                "-m", "webilastik.server.session_allocator"  #str(self.deb_tree.session_allocator_path),
            ],
            env=myenv,
            cwd=self.deb_tree.pythonpath,
        )
        result = server_process.wait()
        logger.info(f"Server finished with result {result}")


if __name__ == "__main__":
    project_root = ProjectRoot()
    executor = SerialExecutor()

    session_allocator_server_config = SessionAllocatorServerConfig.from_env()
    if isinstance(session_allocator_server_config, Exception):
        raise session_allocator_server_config

    deb_tree  = CreateDebTree.execute(project_root=project_root, executor=executor)
    if isinstance(deb_tree, Exception):
        raise deb_tree

    result = StartLocalServer(
        project_root=project_root, deb_tree=deb_tree, session_allocator_server_config=session_allocator_server_config
    ).run()
    if isinstance(result, Exception):
        raise result

