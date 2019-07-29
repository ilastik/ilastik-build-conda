#!/usr/bin/env python

import argparse
import contextlib
import shutil
import json
import os
import sys
import pathlib
import subprocess
from typing import Optional, List

parser = argparse.ArgumentParser(description="Create ilastik package")
parser.add_argument("--skip-tar", help="skip compression", action="store_true")
parser.add_argument("--git-latest", help="use latest git master", action="store_true")
parser.add_argument("--no-solvers", help="package without solvers support", action="store_true")
parser.add_argument("--include-tests", help="include tests", action="store_true")
parser.add_argument("-c", "--channel", help="conda channels to use when creating package", action="append", dest="channels", default=("ilastik-forge", "conda-forge", "defaults"))
parser.add_argument("--git-branch", type=str, help="use git branch to clone")
parser.add_argument("--extra-packages", type=str, help="extra packages to install to the release env", nargs="*")


SOLVER_FILES = ("libcplex*", "libilocplex*", "libconcert*", "libgurobi*")


class PackageNotFoundError(Exception):
    pass


class Conda:
    class Env:
        def __init__(self, name, conda) -> None:
            self.name = name
            self._conda = conda
            self._info_cache = None

        def exists(self) -> bool:
            """Does this environment exist?"""
            try:
                _path = self.path
                return True
            except ValueError:
                return False

        def remove(self) -> None:
            """Remove this environment."""
            run("conda", "env", "remove", "--yes", "--name", self.name)
            self._info_cache = None

        def create(self, *, packages: List[str]) -> None:
            """Create this environment.
            Args:
                packages: Package specs to install (package names and versions).
            """
            packages_with_versions = ["%s=%s" % (p, self._conda.get_pkg_version(p)) for p in packages]

            self._print_packages(packages_with_versions)

            run("conda", "create", "--yes", "--name", self.name, *self._conda._chan_args, *packages_with_versions)

        @property
        def path(self) -> pathlib.Path:
            """Installation directory for this environment.
            Raises:
                ValueError: The current environment does not exist.
            """
            prefixes = [pathlib.Path(d) for d in self._info["envs_dirs"]]
            for env in self._info["envs"]:
                env = pathlib.Path(env)
                for prefix in prefixes:
                    with contextlib.suppress(ValueError):
                        if str(env.relative_to(prefix)) == self.name:
                            return env
            raise ValueError("environment does not exist")

        @property
        def _info(self):
            if self._info_cache is not None:
                return self._info_cache
            info_raw = run_stdout("conda", "info", "--json")
            info_json = json.loads(info_raw)
            if not isinstance(info_json, dict):
                raise json.JSONDecodeError("not a JSON dictionary", doc=info_raw, pos=0)
            self._info_cache = info_json
            return self._info_cache

        def _print_packages(self, packages) -> None:
            print("Creating environment %s with following packages:" % self.name)
            for p in packages:
                print("*", p)


    def __init__(self, channels: List[str]) -> None:
        self._chan_args = []
        for ch in channels:
            self._chan_args.extend(["--channel", ch])

    def env(self, name):
        return self.Env(name, self)

    def get_pkg_version(self, pkg_name):
        out = run_stdout("conda", "search", "-f", pkg_name, *self._chan_args)
        if not out:
            raise PackageNotFoundError(pkg_name)

        non_empty_lines = [l.strip() for l in out.split('\n') if l.strip()]
        last = non_empty_lines[-1]

        # Columns: package name, version, build, channel
        pkg_name, version, *_ = last.split()

        return version


def remove_files(path: pathlib.Path, files: List[str]) -> None:
    for f in files:
        for path in path.glob("**/%s" % f):
            print("Removing", str(path))
            os.unlink(path)


def run(*args: Optional[str]) -> None:
    """Execute the command; fail on non-zero exit code.
    Arguments that are None are omitted from the command's argument list.
    """
    args = [arg for arg in args if arg is not None]
    subprocess.run(args, check=True, encoding="utf-8")


def run_stdout(*args: Optional[str]) -> str:
    """:func:`run` that returns the standard output and ignores the standard error."""
    args = [arg for arg in args if arg is not None]
    proc = subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8")
    return proc.stdout


@contextlib.contextmanager
def workdir(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


def clone_and_compile(dst, branch):
    run("git", "clone", "https://github.com/ilastik/ilastik-meta", dst)
    with workdir(dst):
        run("git", "submodule", "init")
        run("git", "submodule", "update")
        run("git", "submodule", "foreach", "git checkout %s" % branch)
        run("python", "-m", "compileall", "lazyflow", "volumina", "ilastik")


def remove_directory(path: str) -> None:
    if not path:
        raise ValueError("Empty path")

    print("Removing:", path)
    shutil.rmtree(path)


def get_release_name(version, suffix, os):
    return "ilastik-{pkg_version}{suffix}-{os}".format(pkg_version=version, suffix=suffix, os=os)


def create_archive(name: str, path: str) -> str:
    root_path = os.path.dirname(path)
    return shutil.make_archive(name, 'bztar', root_dir=root_path, base_dir=name)


def main():
    args = parser.parse_args()

    branch = None

    if args.git_latest:
        branch = "master"

    if args.git_branch:
        branch = args.git_branch

    version = branch
    if not version:
        version = conda.get_pkg_version("ilastik-meta")

    conda = Conda(args.channels)
    release_name = get_release_name(version, "-no-solvers" if args.no_solvers else "", sys.platform)
    release_env = conda.env(release_name)

    if release_env.exists:
        release_env.remove()

    ilastik_deps_pkg = "ilastik-dependencies"
    if args.no_solvers:
        ilastik_deps_pkg = "ilastik-dependencies-no-solvers"

    packages = [ilastik_deps_pkg, "ilastik-meta"]

    if args.extra_packages:
        packages.extend(args.extra_packages)

    release_env.create(packages=packages)

    meta_path = release_env.path / "ilastik-meta"

    if branch:
        remove_directory(meta_path)
        clone_and_compile(meta_path, branch=branch)

    if not args.include_tests:
        for test_dir in meta_path.glob("*/tests"):
            remove_directory(test_dir)

    print("Removing solver files")
    remove_files(release_env.path, SOLVER_FILES)

    if args.skip_tar:
        print("Skipping tarball creation.")
        print("Release env created in", release_env.path)
    else:
        archive = create_archive(release_name, release_env.path)
        print("Created:", archive)

    return 0


if __name__ == "__main__":
    sys.exit(main())
