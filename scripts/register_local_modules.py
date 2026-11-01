#!/usr/bin/env python3
"""Publish local hardware snapshots for registry-only development validation."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


MODULES = {
    "hardware.build": "pkgs/hardware/build",
    "hardware.camera": "pkgs/hardware/camera",
    "hardware.lidar": "pkgs/hardware/lidar",
    "wheelos_transform": "pkgs/transform",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--module", action="append", choices=sorted(MODULES))
    args = parser.parse_args()
    source = args.source.resolve()
    registry = args.registry.resolve()
    archives = args.archives.resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    selected = args.module or list(MODULES)
    paths = [MODULES[name] for name in selected]
    if subprocess.check_output(
        ["git", "-C", str(source), "status", "--porcelain", "--", *paths], text=True
    ).strip():
        parser.error("module sources must be clean before creating snapshots")
    archives.mkdir(parents=True, exist_ok=True)
    for name in selected:
        relative = MODULES[name]
        module = source / relative
        declaration = (module / "MODULE.bazel").read_text()
        version = "0.1.0"
        entry = registry / "modules" / name / version
        if entry.exists():
            parser.error(f"refusing to overwrite existing registry version: {entry}")
        archive = archives / f"{name}-{version}-{revision}.tar.gz"
        prefix = f"{name}-{version}"
        with tarfile.open(archive, "w:gz") as output:
            output.add(module, arcname=prefix, filter=lambda info: None if ".git" in Path(info.name).parts else info)
            license_file = source / "LICENSE"
            if license_file.is_file() and not (module / "LICENSE").exists():
                output.add(license_file, arcname=prefix + "/LICENSE")
        integrity = "sha256-" + base64.b64encode(hashlib.sha256(archive.read_bytes()).digest()).decode()
        entry.mkdir(parents=True)
        (entry / "MODULE.bazel").write_text(declaration)
        (entry / "source.json").write_text(json.dumps({
            "url": archive.as_uri(), "integrity": integrity, "strip_prefix": prefix,
        }, indent=2) + "\n")
        (entry.parent / "metadata.json").write_text(json.dumps({
            "versions": [version], "yanked_versions": {},
        }, indent=2) + "\n")
        (entry / "local-snapshot.json").write_text(json.dumps({
            "development_only": True, "source_revision": revision,
            "source_module": relative,
        }, indent=2) + "\n")
        print(f"registered {name}@{version}: {integrity}")


if __name__ == "__main__":
    main()
