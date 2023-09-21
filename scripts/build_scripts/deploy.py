from pathlib import Path
from typing import Final
from concurrent.futures import Executor


from build_scripts import ProjectRoot, run_subprocess
from build_scripts.create_deb_package import CreateDebPackage, DebPackage
from webilastik.scheduling import SerialExecutor


class Deployment:
    def __init__(self) -> None:
        super().__init__()


class Deploy:
    def __init__(self, project_root: ProjectRoot, deb_package: DebPackage) -> None:
        self.project_root = project_root
        self.deb_package = deb_package
        self.package_path_on_remote: Final[Path] = Path()
        super().__init__()

    def run(self, use_cache: bool = True) -> "Deployment | Exception":
        scp_result = run_subprocess(
            [
                "scp",
                str(self.deb_package.path),
                f"{self.project_root.web_server_user}@{self.project_root.web_server_ip}:{self.package_path_on_remote}",
            ]
        )
        if isinstance(scp_result, Exception):
            return scp_result

        apt_install_result = run_subprocess(
            [
                "ssh",
                f"{self.project_root.web_server_user}@{self.project_root.web_server_ip}",
                f"sudo apt-get --assume-yes remove webilastik && sudo apt-get --assume-yes install {self.package_path_on_remote}",
            ]
        )
        if isinstance(apt_install_result, Exception):
            return apt_install_result

        git_fetch_jusuf = run_subprocess(
            [
                "ssh",
                "webilastik@jusuf.fz-juelich.de",

                "cd /p/home/jusers/webilastik/jusuf/webilastik.git && git fetch",
            ]
        )
        if isinstance(git_fetch_jusuf, Exception):
            return git_fetch_jusuf

        # git_fetch_cscs = run_subprocess(
        #     [
        #         "ssh",
        #         "bp000188@ela.cscs.ch",
        #         "-oCheckHostIP=no",
        #         "-oBatchMode=yes",

        #         "cd /users/bp000188/source/webilastik.git && git fetch",
        #     ]
        # )
        # if isinstance(git_fetch_cscs, Exception):
        #     return git_fetch_cscs

        return Deployment()

    @classmethod
    def execute(cls, project_root: ProjectRoot, executor: Executor) -> "Deployment | Exception":
        deb_package = CreateDebPackage.execute(project_root=project_root, executor=executor)
        if isinstance(deb_package, Exception):
            return deb_package
        return Deploy(project_root=project_root, deb_package=deb_package).run()

if __name__ == "__main__":
    deployment = Deploy.execute(project_root=ProjectRoot(), executor=SerialExecutor())
    if isinstance(deployment, Exception):
        raise deployment


