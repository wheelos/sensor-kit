#!/usr/bin/env python3
"""Install a built product into a new directory; never overwrite customer data."""

import argparse
from pathlib import Path
import shutil
import tempfile


def install(source, destination):
    if not destination.is_absolute() or destination.exists():
        raise ValueError("destination must be an absolute, nonexistent directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".runtime-install-", dir=destination.parent) as staging:
        tree = Path(staging) / "runtime"
        shutil.copytree(source, tree)
        # Bazel tree artifacts are read-only and normalize file permissions.
        tree.chmod(0o755)
        for path in tree.rglob("*"):
            if path.is_dir():
                path.chmod(0o755)
            else:
                section = path.relative_to(tree).parts[0]
                path.chmod(0o755 if section in {"bin", "lib", "libexec"} else 0o644)
        if destination.exists():
            raise ValueError("destination was created during installation")
        tree.rename(destination)


def main():
    from python.runfiles import runfiles

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime")
    parser.add_argument("--destdir", type=Path, required=True)
    args = parser.parse_args()
    if not args.destdir.is_absolute() or args.destdir.exists():
        parser.error("--destdir must be an absolute, nonexistent directory")
    source = runfiles.Create().Rlocation(args.runtime)
    if not source or not Path(source).is_dir():
        parser.error(f"built runtime not found: {args.runtime}")
    install(Path(source), args.destdir)


if __name__ == "__main__":
    main()
