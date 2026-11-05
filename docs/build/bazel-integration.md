# Build and development workflow

## Development mode

The supported clean-checkout workflow imports pinned source repositories with
VCS, builds with the `dev` profile, and then uses the direct Core commands
described in the [Vanjee operation guide](../operations/sensor-runtime.md).
Building does not start hardware.

### Requirements

- Linux development host with Git, curl, a C++ build toolchain, and Ninja.
- `python3-vcstool` (`vcs` command).
- [Bazelisk](https://github.com/bazelbuild/bazelisk#installation), or Bazel
  8.8.1. The repository pins 8.8.1 in `.bazelversion`.
- Network access to the pinned Git repositories and the Bazel registries in
  `.bazelrc.registry`.

Install the system packages and import source dependencies once from the
repository root:

```bash
sudo apt update
sudo apt install git curl build-essential ninja-build python3-vcstool
vcs import pkgs < deps.repos
```

`deps.repos` pins Core, common, transform, messages, and hardware to Git
commits. VCS checks them out under `pkgs/`, which is intentionally ignored by
the Sensor Kit Git repository. The hardware repository is a monorepo; Bazel
overrides its `build`, `camera`, and `lidar` modules from their respective
subdirectories. Third-party Bazel modules are still fetched from the configured
registries.

Build the Vanjee component and Core tools:

```bash
bazel build --jobs=4 --config=dev //:vanjeelidar //:core_tools
```

Or build the explicit component and tool targets directly:

```bash
bazel build --jobs=4 --config=dev \
  @hardware.lidar//vanjeelidar:libvanjeelidar_component.so \
  //:mainboard //:cyber_recorder //:cyber_monitor
```

`.bazelrc` imports `.bazelrc.dev`; `--config=dev` enables its workspace-relative
overrides into `pkgs/`. No Apollo checkout or absolute local source path is
required. The `wheelos_transform` override is included because the pinned
hardware source depends on it and it is not available from the configured
registries.

After building, source `scripts/env.sh` once in each terminal, then run
`mainboard`, `cyber_monitor`, and `cyber_recorder` directly. The operation guide
contains the exact startup, observation, and recording commands.

### Install mode — TODO

Packaging and installation targets are TODO. The current supported workflow is
local source development with `deps.repos`, `.bazelrc.dev`, and `scripts/env.sh`.
