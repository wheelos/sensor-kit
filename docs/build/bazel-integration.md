# Build and development workflow

## Development mode

The supported clean-checkout workflow imports the latest `main` branches with
VCS, builds with the `dev` profile, and then starts sensors with Core's
`cyber_launch` entry point as described in the
[operation guide](../operations/sensor-runtime.md). Building does not start
hardware.

### Requirements

- Linux development host with Git, curl, a C++ build toolchain, and Ninja.
- `python3-vcstool` (`vcs` command).
- [Bazelisk](https://github.com/bazelbuild/bazelisk#installation), or Bazel
  8.8.1. The repository pins 8.8.1 in `.bazelversion`.
- Network access to the Git repositories and the Bazel registries in
  `.bazelrc.registry`.

Install the system packages and import source dependencies once from the
repository root:

```bash
sudo apt update
sudo apt install git curl build-essential ninja-build python3-vcstool
vcs import pkgs < deps.repos
```

`deps.repos` tracks `main` for Core, common, transform, messages, and hardware.
VCS checks them out under `pkgs/`, which is intentionally ignored by the
Sensor Kit Git repository. Existing clean checkouts can be updated with
`vcs pull pkgs`; inspect and preserve any local changes before updating. The
hardware repository is a monorepo; Bazel overrides its `build`, `camera`,
`gnss`, `hal`, and `lidar` modules from their respective subdirectories.
Third-party Bazel modules are still fetched from the configured registries.

Build the Vanjee component and Core tools:

```bash
bazel build --jobs=4 --config=dev //:vanjeelidar //:gnss //:core_tools
```

The GNSS parser also requires PROJ's runtime database. Build it once before
starting the component:

```bash
bazel build --config=dev @@proj+//:proj_runtime_data
```

Or build the explicit component and tool targets directly:

```bash
bazel build --jobs=4 --config=dev \
  @hardware.lidar//vanjeelidar:libvanjeelidar_component.so \
  @hardware.gnss//:libgnss_component.so \
  //:cyber_launch //:mainboard //:cyber_recorder //:cyber_monitor
```

`.bazelrc` imports `.bazelrc.dev`; `--config=dev` enables its workspace-relative
overrides into `pkgs/`. No Apollo checkout or absolute local source path is
required. The `wheelos_transform` override is included because the hardware
source depends on it and it is not available from the configured
registries.

After building, source `scripts/env.sh` once in each terminal. Start a sensor
with `cyber_launch start <sensor.launch>`; use `cyber_monitor` and
`cyber_recorder` to inspect and record channels. `mainboard -d <sensor.dag>`
remains available as the lower-level direct entry point. The operation guide
contains the exact commands.

### Install mode — TODO

Packaging and installation targets are TODO. The current supported workflow is
local source development with `deps.repos`, `.bazelrc.dev`, and `scripts/env.sh`.
