from dataclasses import dataclass
import subprocess
from sys import stderr
import textwrap
import shutil
from pathlib import Path
from typing import Final

from webilastik.config import SessionAllocatorServerConfig

from build_scripts import (
    BUILD_DIR, NEUROGLANCER_BUILD_PATH, OVERLAY_BUNDLE_PATH, PKG_VERSION, PROJECT_ROOT, SOURCES_DIRS,
    WEBILASTIK_UNIT_INSTALL_PATH, ProjectRoot, force_update_dir
)
from webilastik.utility.log import Logger

logger = Logger()


class DebTree:
    def __init__(self, path: Path) -> None:
        self.path: Final[Path] = path
        super().__init__()



class PackedCondaEnv:
    @classmethod
    def create(cls, *, project_root: ProjectRoot):
        pass

class CreateDebTree:
    def __init__(self, project_root: ProjectRoot, packed_conda_env: Path) -> None:
        self.project_root = project_root
        self.deb_tree_path: Final[Path] = self.project_root.build_dir / "deb_tree"
        self.packed_conda_env: Final[Path] = packed_conda_env
        super().__init__()


    def run(self, *, packed_conda_env: Path) -> "DebTree | Exception":
        session_allocator_server_config = SessionAllocatorServerConfig.from_env()
        if isinstance(session_allocator_server_config, Exception):
            print(f"Could not get session allocator config form environment: {session_allocator_server_config}", file=stderr)
            exit(1)

        logger.info('Generating basic package tree')
        force_update_dir(source=PROJECT_ROOT / "package_tree", dest=self.deb_tree_path)

        logger.debug('Generating DEBIAN/control file')
        with open(self.deb_tree_path / "DEBIAN/control", "w") as control_file:
            _ = control_file.write(textwrap.dedent(f"""
                Package: webilastik
                Version: {PKG_VERSION}
                Section: base
                Priority: optional
                Architecture: amd64
                Depends: nginx
                Maintainer: ilastik Team <team@ilastik.org>
                Description: Webilastik
                Server and frontend for the web version of ilastik
            """[1:]))

        logger.debug('Generating webilastik.service file')
        service_file_path = self.deb_tree_path / str(WEBILASTIK_UNIT_INSTALL_PATH).lstrip("/")
        service_file_path.mkdir(parents=True)
        with open(service_file_path, "w") as service_file:
            _ = service_file.write(textwrap.dedent(f"""
                [Unit]
                Description=Webilastik session allocator server
                Documentation=https://github.com/ilastik/webilastik
                Wants=nginx.service

                [Install]
                WantedBy=multi-user.target

                [Service]
                Type=simple
                # FIXME/BUG: aiohttp must be told where certs are when running from packed environment
                Environment=SSL_CERT_DIR=/etc/ssl/certs/
                Environment=REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
                {session_allocator_server_config.to_systemd_environment_conf()}

                Environment=PYTHONPATH=/opt/webilastik/
                ExecStart=/opt/webilastik/conda_env/bin/python3 -B /opt/webilastik/webilastik/server/session_allocator.py

                TimeoutStopSec=30
                KillMode=mixed
                Restart=on-failure
                User=www-data
                Group=www-data
                KillSignal=SIGQUIT
                NotifyAccess=all

                [Install]
                WantedBy=multi-user.target
            """[1:]))

        logger.debug('Unpacking conda environment')
        conda_env_path = self.deb_tree_path.joinpath("opt/webilastik/conda_env")
        conda_env_path.mkdir(parents=True)
        _ = subprocess.check_output([
            "tar", "-xzf", str(packed_conda_env), "-C", str(conda_env_path)
        ])

        logger.debug('Copying webilastik files')
        webilastik_code_dir = self.deb_tree_path / "opt/webilastik"
        webilastik_code_dir.mkdir(parents=True)

        for source_dir_path in list(SOURCES_DIRS) + [PROJECT_ROOT / "public"]:
            dest_dir_path = webilastik_code_dir.joinpath(source_dir_path.name)
            dest_dir_path.mkdir(parents=True)
            force_update_dir(source=source_dir_path, dest=dest_dir_path, exclude_pattern="__pycache__")

        logger.debug('Copying overlay bundle to public dir')
        public_js_dir = self.deb_tree_path / "opt/webilastik/public/js"
        public_js_dir.mkdir(parents=True)
        shutil.copy(OVERLAY_BUNDLE_PATH, public_js_dir)
        shutil.copy(str(OVERLAY_BUNDLE_PATH) + ".map", public_js_dir)

        logger.debug('Copying nehuba to public dir')
        shutil.copy(NEUROGLANCER_BUILD_PATH, self.deb_tree_path / "opt/webilastik/public/nehuba")

        return DebTree(path=self.deb_tree_path)

    def clean(self):
        shutil.rmtree(path=self.deb_tree_path)
