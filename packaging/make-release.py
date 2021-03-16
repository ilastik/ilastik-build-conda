from pathlib import Path
from typing import List, Dict, Optional
import click
import json
import logging
import os
import platform
import re
import subprocess

logger = logging.getLogger("make-release")

CONDA_DEFAULT_OPTIONS = ["--yes", "--override-channels", "--strict-channel-priority"]

OS: str = platform.system().lower()

ILASTIK_PACKAGES = {
    "linux": ["ilastik-dependencies-binary"],
    "darwin": ["ilastik-dependencies-binary", "py2app"],
    "windows": ["ilastik-dependencies-binary", "ilastik-exe", "ilastik-package"],
}

OS_SUFFIX = {
    "linux": "linux",
    "darwin": "OSX",
    "windows": "win64",
}

DEFAULT_CHANNELS = ["ilastik-forge", "conda-forge"]


ISS = None
if OS == "windows":
    ISS = os.environ["INNOCC"]
    assert Path(ISS).exists()


class CondaEnv:
    @staticmethod
    def conda_info():
        return json.loads(subprocess.check_output(["conda", "info", "-e", "--json"]))

    def __init__(self, env_name):
        self._name = env_name
        self._is_valid = False

        self._create(channels=DEFAULT_CHANNELS, packages=ILASTIK_PACKAGES[OS])

    @property
    def name(self):
        return self._name

    @classmethod
    def envs(cls) -> List[Path]:
        return [
            Path(x)
            for x in json.loads(
                subprocess.check_output(["conda", "env", "list", "--json"])
            )["envs"]
        ]

    @property
    def path(self) -> Path:
        return Path(self.conda_info()["envs_dirs"][0]) / self.name

    def _create(self, channels: List[str], packages: List[str]) -> None:
        logger.info(
            f"creating environment {self.name} with channels: {channels} and packages {packages}"
        )
        if self.path.exists():
            subprocess.check_call(["conda", "env", "remove", "--name", self.name])
            if self.path.exists():
                self.path.unlink()

        chans = []
        for channel in channels:
            chans += ["--channel", channel]
        subprocess.check_call(
            [
                "conda",
                "create",
                "--name",
                self.name,
                *CONDA_DEFAULT_OPTIONS,
                *chans,
                *packages,
            ]
        )
        self._is_valid = True
        logger.info("created environment successfully")

    def package_info(self, package_name: str) -> Dict[str, str]:
        package_list = json.loads(
            subprocess.check_output(["conda", "list", "--name", self.name, "--json"])
        )
        package_info = [x for x in package_list if x["name"] == package_name]
        assert (
            len(package_info) == 1
        ), f"Could not find unique package info for {package_name}; found {len(package_info)}."
        return package_info[0]

    @property
    def is_valid(self):
        return self._is_valid


class IlastikRelease:
    def __init__(self, release_env: CondaEnv, tiktorch_archive: Path):
        assert release_env.is_valid
        self._release_env = release_env
        self._tiktorch_archive = tiktorch_archive

        imeta_version = self._release_env.package_info("ilastik-meta")["version"]
        # ilastik-${ILASTIK_PKG_VERSION}${SOLVERS_SUFFIX}${TIKTORCH_SUFFIX}-`uname`
        self._release_name = f"ilastik-{imeta_version}-cpu-{OS_SUFFIX[OS]}"
        self._release_path: Optional[Path] = None

        self._unpack_tiktorch()
        self._prepare_package()
        self._package()

    @property
    def release_path(self):
        return self._release_path

    def _unpack_tiktorch(self) -> None:
        target_dir = self._release_env.path
        logger.info(
            f"Unpacking tiktorch from {self._tiktorch_archive} to {target_dir}."
        )
        if self._tiktorch_archive.suffix == ".zip":
            subprocess.check_call(["unzip", str(self._tiktorch_archive), "-d", str(target_dir)])
        elif self._tiktorch_archive.suffix in [".tar", ".bz2"]:
            subprocess.check_call(
                ["tar", "-xvf", str(self._tiktorch_archive), "-C", str(target_dir)]
            )

    def _prepare_package(self) -> None:
        logger.info("preparing package")
        if OS == "windows":
            self._prepare_windows()
        elif OS == "linux":
            self._prepare_linux()
        elif OS == "darwin":
            self._prepare_darwin()
        else:
            raise NotImplementedError(f"Not implemented for OS {OS}")

    def _prepare_windows(self) -> None:
        iss_in = self._release_env.path / "package" / "ilastik.iss.in"
        iss_out = iss_in.parent / "ilastik.iss"

        iss_out.write_text(re.sub("@VERSION@", self._release_name, iss_in.read_text()))

    def _prepare_darwin(self) -> None:
        pass

    def _prepare_linux(self) -> None:
        pass

    def _package(self) -> None:
        logger.info("packaging")
        if OS == "windows":
            self._package_windows()
        elif OS == "linux":
            self._package_linux()
        elif OS == "darwin":
            self._package_darwin()
        else:
            raise NotImplementedError(f"Not implemented for OS {OS}")

    def _package_windows(self) -> None:
        iss_path = self._release_env.path / "package" / "ilastik.iss"
        subprocess.check_call([ISS, f"/O{os.getcwd()}", str(iss_path)])
        self._release_path = Path(os.getcwd()) / f"{self._release_name}.exe"

    def _package_linux(self) -> None:
        package_cmd = Path(__file__).parent / "linux" / "create-tarball.sh"
        subprocess.check_call([package_cmd, self._release_name])
        self._release_path = Path(os.getcwd()) / f"{self._release_name}.tar.bz2"

    def _package_darwin(self) -> None:
        package_cmd = Path(__file__).parent / "osx" / "create-osx-app.sh"
        subprocess.check_call([package_cmd, self._release_name])
        self._release_path = Path(os.getcwd()) / f"{self._release_name}.tar.bz2"


@click.command()
@click.argument("tiktorch_archive", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode")
def main(tiktorch_archive: str, verbose: bool):
    level = verbose and logging.DEBUG or logging.INFO
    logging.basicConfig()
    logger.setLevel(level)
    ilastik_env = CondaEnv("ilastik-release")
    ilastik_release = IlastikRelease(ilastik_env, Path(tiktorch_archive))
    assert ilastik_release.release_path.exists()
    logger.info(f"created ilastik package at: {ilastik_release.release_path}.")


if __name__ == "__main__":
    main()
