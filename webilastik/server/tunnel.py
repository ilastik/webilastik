from os import remove
from pathlib import Path
import subprocess
from subprocess import Popen
import os


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
        self.remote_unix_socket = remote_unix_socket
        self.local_unix_socket = local_unix_socket
        self.tunnel_control_socket = Path(str(local_unix_socket) + ".control")

    def __enter__(self):
        subprocess.run(
            ["ssh", f"{self.remote_username}@{self.remote_host}", "--", "rm", "-fv", self.remote_unix_socket],
        )
        self.tunnel_process = Popen(
            [
                "ssh", "-fnNT",
                "-M", "-S", self.tunnel_control_socket,
                "-R", f"{self.remote_unix_socket}:{self.local_unix_socket}",
                f"{self.remote_username}@{self.remote_host}"
            ],
        )

    def __exit__(self, *args):
        print(f"--> Closing tunnel via {self.tunnel_control_socket}")
        subprocess.run(
            ["ssh", "-S", self.tunnel_control_socket, "-O", "exit", f"{self.remote_username}@{self.remote_host}"]
        )
        subprocess.run(
            ["ssh", f"{self.remote_username}@{self.remote_host}", "--", "rm", "-fv", self.remote_unix_socket],
        )
