# pyright: strict

import textwrap
import shutil
from pathlib import Path
from concurrent.futures import Executor
from scripts.build_scripts.assemble_public_dir import PublicDir

from scripts.build_scripts.compile_overlay import CompileOverlay
from scripts.build_scripts.create_conda_env import CreateCondaEnvironment
from scripts.build_scripts.create_packed_conda_env import CreatePackedCondaEnv, PackedCondaEnv
from scripts.build_scripts.neuroglancer.compile_neuroglancer import BuildNeuroglancer
from scripts.build_scripts.neuroglancer.fetch_neuroglancer_source import FetchNeuroglancerSource

from webilastik.config import SessionAllocatorServerConfig

from scripts.build_scripts import PackageSourceFile, ProjectRoot, force_update_dir, get_effective_mtime, run_subprocess
from webilastik.scheduling import SerialExecutor
from webilastik.utility.log import Logger

logger = Logger()

class DebControlFile(PackageSourceFile):
    def __init__(self, project_root: ProjectRoot) -> None:
        super().__init__(
            contents=textwrap.dedent(f"""
                Package: webilastik
                Version: {project_root.pkg_version}
                Section: base
                Priority: optional
                Architecture: amd64
                Depends: nginx
                Maintainer: ilastik Team <team@ilastik.org>
                Description: Webilastik
                 Server and frontend for the web version of ilastik
            """[1:]).encode("utf8"),
        )

class WebilastikServiceFile(PackageSourceFile):
    def __init__(self, *, project_root: ProjectRoot, session_allocator_server_config: SessionAllocatorServerConfig) -> None:
        super().__init__(
            contents=textwrap.dedent(f"""
                # generated at {Path(__file__).relative_to(project_root.root_path)}
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
                # FIXME: forcing 'allow_local_compute_sessions to False for now
                {session_allocator_server_config.updated(allow_local_compute_sessions=False).to_systemd_environment_conf()}

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
            """[1:]).encode("utf8")
        )

class DebTree:
    def __init__(
        self,
        *,
        path: Path,
        python_bin_path: Path,
        session_allocator_path: Path,
        pythonpath: Path,
        _private_marker: None
    ) -> None:
        self.path  = path
        self.mtime = get_effective_mtime(self.path)
        self.pythonpath = pythonpath
        self.python_bin_path = python_bin_path
        self.session_allocator_path = session_allocator_path
        super().__init__()

class CreateDebTree:
    def __init__(
        self,
        *,
        project_root: ProjectRoot,
        packed_conda_env: PackedCondaEnv,
        public_dir: PublicDir,
        session_allocator_server_config: SessionAllocatorServerConfig,
    ) -> None:
        self.project_root = project_root
        self.path = project_root.build_dir / "deb_tree"
        self.opt_webilastik = self.path / "opt/webilastik"
        self.unpacked_conda_env = self.opt_webilastik / "conda_env"
        self.python_bin_path = self.unpacked_conda_env / "bin/python3"
        self.session_allocator_path = self.opt_webilastik / "webilastik/server/session_allocator.py"

        self.packed_conda_env = packed_conda_env
        self.public_dir = public_dir
        self.deb_control_file = DebControlFile(project_root=project_root)
        self.service_file = WebilastikServiceFile(
            project_root=project_root, session_allocator_server_config=session_allocator_server_config
        )
        super().__init__()

    def run(self) -> "DebTree | Exception":
        logger.info('Generating basic package tree')
        force_update_dir(
            source=self.project_root.package_tree_base, dest=self.path, delete_extraneous=False
        )

        logger.debug('Copying webilastik files')
        source_dirs = [
            self.project_root.webilastik_code_dir,
            self.project_root.public_dir,
            self.project_root.caching_impls_dir,
            self.project_root.default_caching_impl_dir,
            self.project_root.executor_getter_impls_dir,
            self.project_root.default_executor_getter_dir,
        ]
        for source_dir in source_dirs:
            force_update_dir(
                source=source_dir,
                dest=self.opt_webilastik / source_dir.name,
                delete_extraneous=True
            )

        self.deb_control_file.install(target_path=self.path / "DEBIAN/control")
        self.service_file.install(target_path=self.path / "lib/systemd/system/webilastik.service")

        if get_effective_mtime(self.packed_conda_env.path) > get_effective_mtime(self.unpacked_conda_env):
            self.unpacked_conda_env.mkdir(parents=True, exist_ok=True)
            unpack_result = run_subprocess(["tar", "--touch", "-xzf", str(self.packed_conda_env.path), "-C", str(self.unpacked_conda_env)])
            if isinstance(unpack_result, Exception):
                return Exception(f"Unpacking packed conda env failed: {unpack_result}")

        return DebTree(
            path=self.path,
            python_bin_path=self.python_bin_path,
            session_allocator_path=self.session_allocator_path,
            pythonpath=self.opt_webilastik,
            _private_marker=None,
        )

    def clean(self):
        shutil.rmtree(path=self.path)

    @classmethod
    def execute(cls, *, project_root: ProjectRoot, executor: Executor) -> "DebTree | Exception":
        session_allocator_server_config = SessionAllocatorServerConfig.from_env()
        if isinstance(session_allocator_server_config, Exception):
            return session_allocator_server_config

        conda_env = CreateCondaEnvironment(project_root=project_root).run()
        if isinstance(conda_env, Exception):
            return conda_env

        packed_conda_env = CreatePackedCondaEnv(project_root=project_root, conda_env=conda_env).run()
        if isinstance(packed_conda_env, Exception):
            return packed_conda_env

        ng_source = FetchNeuroglancerSource(project_root=project_root).run()
        if isinstance(ng_source, Exception):
            return ng_source

        neuroglancer_dist = BuildNeuroglancer(project_root=project_root, ng_source=ng_source).run()
        if isinstance(neuroglancer_dist, Exception):
            return neuroglancer_dist

        overlay_bundle = CompileOverlay(project_root=project_root).run()
        if isinstance(overlay_bundle, Exception):
            return overlay_bundle

        public_dir = PublicDir(project_root=project_root, neuroglancer_bundle=neuroglancer_dist, overlay_bundle=overlay_bundle)

        return CreateDebTree(
            project_root=project_root,
            public_dir=public_dir,
            packed_conda_env=packed_conda_env,
            session_allocator_server_config=session_allocator_server_config,
        ).run()


if __name__ == "__main__":
    result = CreateDebTree.execute(project_root=ProjectRoot(), executor=SerialExecutor())
    if isinstance(result, Exception):
        raise result