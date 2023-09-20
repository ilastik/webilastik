from dataclasses import dataclass
import subprocess
from sys import stderr
import textwrap
import shutil
from pathlib import Path
from typing import Final, Mapping
from build_scripts.compile_overlay import CompileOverlay, OverlayBundle
from build_scripts.create_conda_env import CreateCondaEnvironment
from build_scripts.create_packed_conda_env import CreatePackedCondaEnv, PackedCondaEnv
from build_scripts.neuroglancer.compile_neuroglancer import BuildNeuroglancer, NeuroglancerDistribution
from build_scripts.neuroglancer.fetch_neuroglancer_source import FetchNeuroglancerSource

from webilastik.config import SessionAllocatorServerConfig

from build_scripts import PackageSourceFile, ProjectRoot, force_update_dir, get_dir_effective_mtime
from webilastik.utility.log import Logger

logger = Logger()


class DebTree:
    def __init__(self, project_root: ProjectRoot, _private_marker: None) -> None:
        self.project_root = project_root
        super().__init__()

class DebControlFile(PackageSourceFile):
    def __init__(self, project_root: ProjectRoot) -> None:
        super().__init__(
            target_path=project_root.deb_tree_path / "DEBIAN/control",
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
            target_path=project_root.deb_tree_path / "lib/systemd/system/webilastik.service",
            contents=textwrap.dedent(f"""
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
            """[1:]).encode("utf8")
        )

class CreateDebTree:
    def __init__(
        self,
        *,
        project_root: ProjectRoot,
        packed_conda_env: PackedCondaEnv,
        neuroglancer_dist: NeuroglancerDistribution,
        overlay_bundle: OverlayBundle,
        session_allocator_server_config: SessionAllocatorServerConfig,
    ) -> None:
        self.project_root = project_root
        self.packed_conda_env = packed_conda_env
        self.neuroglancer_dist = neuroglancer_dist
        self.overlay_bundle = overlay_bundle
        self.package_tree_base = project_root.root_path / "package_tree"
        self.deb_control_file = DebControlFile(project_root=project_root)
        self.service_file = WebilastikServiceFile(
            project_root=project_root, session_allocator_server_config=session_allocator_server_config
        )
        self.src_to_dest: Mapping[Path, Path] = {
            **{
                project_root.root_path / dir_name: project_root.deb_tree_path / f"opt/webilastik/{dir_name}"
                for dir_name in ("webilastik", "caching", "executor_getters", "public")
            },
        }
        super().__init__()

    def run(self, use_cache: bool = True) -> "DebTree | Exception":
        cache = use_cache and self.cached()
        if cache:
            return cache
        logger.info('Generating basic package tree')
        force_update_dir(
            source=self.package_tree_base, dest=self.project_root.deb_tree_path, delete_extraneous=False
        )

        logger.debug('Copying webilastik files')
        for src_dir, dest_dir in self.src_to_dest.items():
            dest_dir.mkdir(parents=True, exist_ok=True)
            force_update_dir(
                source=src_dir, dest=dest_dir, exclude_pattern="__pycache__", delete_extraneous=True
            )

        self.overlay_bundle.install()
        self.deb_control_file.install()
        self.service_file.install()
        self.packed_conda_env.install()
        self.neuroglancer_dist.install()

        return DebTree(project_root=self.project_root, _private_marker=None)

    def cached(self) -> "DebTree | Exception | None":
        if not self.project_root.deb_tree_path.exists():
            return None
        deb_tree_mtime = get_dir_effective_mtime(self.project_root.deb_tree_path)
        if deb_tree_mtime < get_dir_effective_mtime(self.package_tree_base):
            return None

        for src_dir, dest_dir in self.src_to_dest.items():
            if not dest_dir.exists():
                logger.error(f"dewst dir doesn't exit:> {dest_dir}")
                return None
            dest_dir_mtime = get_dir_effective_mtime(dest_dir)
            src_dir_mtime = get_dir_effective_mtime(src_dir)
            if src_dir_mtime > dest_dir_mtime:
                logger.error(f"Outdated dest: {dest_dir_mtime=} {src_dir_mtime=} at {dest_dir}")
                return None

        if any(not artifact.is_current() for artifact in [
            self.overlay_bundle,
            self.deb_control_file,
            self.service_file,
            self.packed_conda_env,
            self.neuroglancer_dist,
        ]):
            return None
        return DebTree(project_root=self.project_root, _private_marker=None)

    def clean(self):
        shutil.rmtree(path=self.project_root.deb_tree_path)


if __name__ == "__main__":
    project_root = ProjectRoot()

    session_allocator_server_config = SessionAllocatorServerConfig.from_env()
    if isinstance(session_allocator_server_config, Exception):
        raise session_allocator_server_config

    conda_env = CreateCondaEnvironment(project_root=project_root).run()
    if isinstance(conda_env, Exception):
        raise conda_env

    packed_conda_env = CreatePackedCondaEnv(project_root=project_root, conda_env=conda_env).run()
    if isinstance(packed_conda_env, Exception):
        raise packed_conda_env

    ng_source = FetchNeuroglancerSource(project_root=project_root).run()
    if isinstance(ng_source, Exception):
        raise ng_source

    neuroglancer_dist = BuildNeuroglancer(project_root=project_root, ng_source=ng_source).run()
    if isinstance(neuroglancer_dist, Exception):
        raise neuroglancer_dist

    overlay_bundle = CompileOverlay(project_root=project_root).run()
    if isinstance(overlay_bundle, Exception):
        raise overlay_bundle

    deb_tree = CreateDebTree(
        project_root=project_root,
        overlay_bundle=overlay_bundle,
        neuroglancer_dist=neuroglancer_dist,
        packed_conda_env=packed_conda_env,
        session_allocator_server_config=session_allocator_server_config,
    ).run()
    if isinstance(deb_tree, Exception):
        raise deb_tree