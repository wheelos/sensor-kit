#!/usr/bin/env python3
"""Build a product tree using declared files only; never scan Bazel outputs."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys


def destination_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"invalid runtime destination: {value}")
    return path


def assemble(spec, output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for source, relative, kind in spec["files"]:
        destination_path(relative)
        data = Path(source).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if relative in hashes:
            if hashes[relative] != digest:
                raise ValueError(f"conflicting runtime files: {relative}")
            continue
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if kind == "binary" else 0o644)
        hashes[relative] = digest

    for command in ["mainboard", "cyber_launch", "doctor", *sorted(spec.get("tools", {}))]:
        target = root / "bin" / command
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            'root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"\n'
            f'exec python3 "${{root}}/libexec/entry.py" {command} "$@"\n'
        )
        target.chmod(0o755)
    if spec["product"] == "sensors":
        dags = [
            (root / name).read_text()
            for name in hashes
            if name.startswith("share/sensors/") and name.endswith(".dag")
        ]
        if not dags:
            raise ValueError("sensors product requires at least one selected DAG")
        selected = "share/sensors/selected.dag"
        data = ("\n".join(dags) + "\n").encode()
        (root / selected).write_bytes(data)
        (root / selected).chmod(0o644)
        hashes[selected] = hashlib.sha256(data).hexdigest()
    manifest = {
        "product": spec["product"],
        "components": spec["components"],
        "configs": spec["configs"],
        "tools": spec.get("tools", {}),
        "files": hashes,
        "module_sha256": hashlib.sha256(Path(spec["module_file"]).read_bytes()).hexdigest(),
        "module_declarations": Path(spec["module_file"]).read_text(),
        "lock_sha256": (
            hashlib.sha256(Path(spec["lockfile"]).read_bytes()).hexdigest()
            if spec.get("lockfile") else None
        ),
        "sensor_test_client": "not_integrated",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (root / "manifest.json").chmod(0o644)


def split_package(source, output):
    source, output = Path(source), Path(output)
    for name in ["bin", "lib", "libexec", "conf", "share"]:
        destination = output / name
        destination.mkdir(parents=True, exist_ok=True)
        if (source / name).is_dir():
            shutil.copytree(source / name, destination, dirs_exist_ok=True)
    shutil.copyfile(source / "manifest.json", output / "manifest.json")


if __name__ == "__main__":
    if sys.argv[1] == "--package":
        split_package(sys.argv[2], sys.argv[3])
    else:
        assemble(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
