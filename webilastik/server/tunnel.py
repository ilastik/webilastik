from os import remove
from pathlib import Path
import subprocess
from subprocess import CalledProcessError, Popen
import os

import logging

logger = logging.getLogger(__name__)

class ReverseSshTunnel:
    def __init__(
        self,
        *,
        remote_username: str,
        remote_host: str,
        local_unix_socket: Path,
        remote_unix_socket: Path,
    ):
        self.remote_username = remote_username
        self.remote_host = remote_host
        self.remote_unix_socket = ("" if remote_unix_socket.anchor else "./") + str(remote_unix_socket)
        self.local_unix_socket = ("" if local_unix_socket.anchor else "./") + str(local_unix_socket)
        self.tunnel_control_socket = self.local_unix_socket + ".control"

    def _delete_sockets(self):
        result = subprocess.run(
            ["ssh", f"{self.remote_username}@{self.remote_host}", "--", "rm", "-v", self.remote_unix_socket],
        )
        if result.returncode != 0:
            logger.warning(f"Removing socket {self.remote_host}:{self.remote_unix_socket} failed: {result.stderr.decode('utf8')}")


    def __enter__(self):
        _ = subprocess.run(
            ["ssh", f"{self.remote_username}@{self.remote_host}", "--", "rm", "-fv", self.remote_unix_socket],
        )
        self.tunnel_process = Popen(
            [
                "ssh", "-fnNT",
                "-oBatchMode=yes",
                # "-o", "StreamLocalBindMask=0111",
                "-M", "-S", self.tunnel_control_socket,
                "-R", f"{self.remote_unix_socket}:{self.local_unix_socket}",
                f"{self.remote_username}@{self.remote_host}"
            ],
        )

    def __exit__(self, *args):
        print(f"--> Closing tunnel via {self.tunnel_control_socket}")
        result = subprocess.run(
            ["ssh", "-S", self.tunnel_control_socket, "-O", "exit", f"{self.remote_username}@{self.remote_host}"]
        )
        if result.returncode != 0:
            logging.warning(f"Closing tunnel with via {self.tunnel_control_socket} failed ({result.returncode}): {result.stderr.decode('utf8')}")
        self._delete_sockets()
