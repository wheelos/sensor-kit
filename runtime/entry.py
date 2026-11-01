#!/usr/bin/env python3
"""Prepare relocatable configuration and exec only this product's Cyber tools."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys


TEXT_SUFFIXES = {".dag", ".launch", ".txt", ".conf", ".yaml", ".yml"}


def prepare(root):
    if "WHEELOS_CONFIG_ROOT" in os.environ:
        raise ValueError("WHEELOS_CONFIG_ROOT overrides are not supported by immutable product artifacts")
    root = root.resolve()
    if any(character in str(root) for character in ['"', "'", "&", "<", ">", "\n", "\r"]):
        raise ValueError("runtime path contains characters unsafe for DAG/XML templates")
    manifest_bytes = (root / "manifest.json").read_bytes()
    identity = hashlib.sha256(str(root).encode() + manifest_bytes).hexdigest()
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    work = cache / "sensor-infra" / identity
    if any(character in str(work) for character in ['"', "'", "&", "<", ">", "\n", "\r"]):
        raise ValueError("cache path contains characters unsafe for DAG/XML templates")
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest = json.loads(manifest_bytes)
    for relative, expected in manifest["files"].items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"invalid manifest path: {relative}")
        source = root / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"runtime file checksum mismatch: {relative}")
        if not relative.startswith(("share/", "conf/")):
            continue
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
        if source.suffix in TEXT_SUFFIXES:
            text = source.read_text()
            text = text.replace("@RUNTIME_ROOT@", str(root)).replace("@CONFIG_ROOT@", str(work))
            if re.search(r"/apollo/(?:modules|bazel-bin|cyber|data|conf|pkgs)(?:/|\b)", text):
                raise ValueError(f"unmigrated source-tree path in {relative}")
            temporary.write_text(text)
        else:
            temporary.write_bytes(source.read_bytes())
        temporary.chmod(0o600)
        temporary.replace(target)
    # The launcher resolves PATH before parsing its launch environment.
    binary = work / "bin/mainboard"
    binary.parent.mkdir(parents=True, exist_ok=True)
    if not binary.is_symlink():
        binary.symlink_to(root / "libexec/mainboard")
    elif binary.resolve() != root / "libexec/mainboard":
        raise ValueError("cached mainboard does not match this runtime")
    return work, manifest


def command(root, tool, arguments, work):
    def rendered_path(value, suffix):
        path = Path(value)
        if path.suffix != suffix:
            raise ValueError(f"expected a {suffix} product file: {value}")
        if not path.is_absolute():
            path = root / path
        relative = path.resolve().relative_to(root)
        rendered = work / relative
        if not rendered.is_file():
            raise ValueError(f"DAG/launch is not a declared product file: {value}")
        return str(rendered)

    if tool == "mainboard":
        argv = [str(root / "libexec/mainboard")]
        found_dag = False
        index = 0
        while index < len(arguments):
            value = arguments[index]
            if value in {"-d", "--dag_conf"}:
                index += 1
                if index == len(arguments):
                    raise ValueError(f"{value} requires a DAG filename")
                argv.extend([value, rendered_path(arguments[index], ".dag")])
                found_dag = True
            elif value.startswith("--dag_conf="):
                argv.append("--dag_conf=" + rendered_path(value.split("=", 1)[1], ".dag"))
                found_dag = True
            elif value.startswith("-d") and len(value) > 2:
                argv.append("-d" + rendered_path(value[2:], ".dag"))
                found_dag = True
            else:
                argv.append(value)
            index += 1
        if not found_dag and not set(arguments).intersection({"-h", "--help"}):
            raise ValueError("mainboard requires an explicit -d DAG")
    elif tool == "cyber_launch":
        if arguments in (["-h"], ["--help"], ["start", "-h"], ["start", "--help"],
                         ["stop", "-h"], ["stop", "--help"]):
            return [sys.executable, str(root / "libexec/cyber_launch.py"), *arguments]
        if len(arguments) != 2 or arguments[0] not in {"start", "stop"}:
            raise ValueError("cyber_launch requires start|stop and an explicit launch file")
        argv = [sys.executable, str(root / "libexec/cyber_launch.py"),
                arguments[0], rendered_path(arguments[1], ".launch")]
    elif tool in {"cyber_recorder", "cyber_monitor"}:
        binary = root / "libexec" / tool
        if not binary.is_file():
            raise ValueError(f"runtime tool is not packaged: {tool}")
        argv = [str(binary), *arguments]
    else:
        raise ValueError(f"unknown runtime tool: {tool}")
    return argv


def runtime_environment(root, work):
    environment = dict(os.environ)
    environment["APOLLO_ROOT_DIR"] = str(work)
    environment["CYBER_PATH"] = str(work)
    environment["PATH"] = os.pathsep.join([
        str(work / "bin"), str(root / "bin"), environment.get("PATH", ""),
    ])
    environment["LD_LIBRARY_PATH"] = str(root / "lib") + (
        os.pathsep + environment["WHEELOS_RUNTIME_LIBRARY_PATH"]
        if environment.get("WHEELOS_RUNTIME_LIBRARY_PATH") else ""
    )
    environment.setdefault("GLOG_logtostderr", "1")
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=[
        "mainboard", "cyber_launch", "cyber_recorder", "cyber_monitor", "doctor",
    ])
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        work, manifest = prepare(root)
        if args.tool == "doctor":
            if args.arguments:
                raise ValueError("doctor takes no arguments")
            print(json.dumps({
                "status": "CONFIGURED",
                "product": manifest["product"],
                "sensor_test_client": manifest["sensor_test_client"],
                "scope": "file_integrity_and_template_rendering_only",
            }))
            return 0
        argv = command(root, args.tool, args.arguments, work)
    except (OSError, ValueError) as error:
        print(f"runtime preparation failed: {error}", file=sys.stderr)
        return 2
    if args.tool in {"mainboard", "cyber_launch"}:
        os.chdir(work)
    os.execve(argv[0], argv, runtime_environment(root, work))


if __name__ == "__main__":
    raise SystemExit(main())
