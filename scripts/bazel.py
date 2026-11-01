#!/usr/bin/env python3
"""Run the repository's Bazel build without implicit registries or overrides."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_SOURCE_COMMANDS = {
    "aquery",
    "build",
    "cquery",
    "mod",
    "query",
    "run",
    "test",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bazel", default="bazel")
    args, bazel_args = parser.parse_known_args(argv)
    if not bazel_args:
        parser.error("provide a Bazel command, for example: test //runtime:tests")

    bazel = shutil.which(args.bazel)
    if bazel is None:
        parser.error(f"Bazel executable not found: {args.bazel}")

    command = bazel_args[0]
    if command not in SUPPORTED_SOURCE_COMMANDS:
        parser.error(f"unsupported Bazel command for source overrides: {command}")
    result = subprocess.run(
        [bazel, *bazel_args],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
