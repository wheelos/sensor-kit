# Sensor product architecture

## Layering and responsibilities

1. **`wheelos_core` (Middleware)**: Provides the Cyber RT pub/sub runtime,
   component class loader (`mainboard`), launch manager (`cyber_launch`), and
   observation/recording tools (`cyber_monitor`, `cyber_recorder`).
2. **`deps.repos` + `pkgs/` (Source management)**: Pins exact Git commits for
   `core`, `common`, `transform`, `wheelos_msgs`, and `hardware`. `vcs` imports
   them into `pkgs/` (ignored by this repository's Git tracking).
3. **Bazel + `.bazelrc.dev` (Build system)**: Maps Bzlmod dependencies to the
   local `pkgs/` checkouts and compiles both Core tools and selected sensor
   driver components.
4. **This repository (`sensor-kit`)**: Exposes top-level build targets in
   `BUILD.bazel`, provides `scripts/env.sh` to activate the Core runtime
   environment, and stores reference sensor configurations and DAGs under
   `deployment/examples/`.

Vehicle, CAN, and whl-can are maintained in the independent `vehicle-infra`
repository.

## Repository layout

| Path | Responsibility |
|---|---|
| `MODULE.bazel`, `.bazelrc*`, `.bazelversion` | Bazel module dependencies, registries, and `dev` overrides |
| `deps.repos` | Pinned VCS source manifest for development checkouts |
| `pkgs/` | VCS-imported source repositories (gitignored) |
| `BUILD.bazel` | Top-level aliases for Core tools (`//:core_tools`) and sensor drivers (`//:vanjeelidar`, `//:hesai`, `//:camera`) |
| `scripts/env.sh` | Generic Core runtime environment setup (`PATH`, `APOLLO_ROOT_DIR`, `CYBER_PATH`, `CYBER_IP`, `CYBER_DOMAIN_ID`, `TERMINFO`) |
| `deployment/examples/` | Versioned reference DAGs and device configurations |
| `docs/` | Architecture, build, and operating documentation |

## DAG and configuration path resolution paradigm

In `wheelos_core`, `mainboard` resolves paths using two environment roots:

- `CYBER_PATH` (`common::WorkRoot()`): used by `GlobalData` to read
  `conf/cyber.pb.conf`, by `ModuleController::LoadModule` to resolve relative
  `module_library` paths, and by `ComponentBase` as the base for non-`modules/`
  relative config paths.
- `APOLLO_ROOT_DIR` (`ResourceManager::SoftwareRoot()`): used by
  `ResourceManager::ResolveConfigPath` to validate and resolve DAG files and
  `config_file_path` entries within the software root.

`scripts/env.sh` unifies both roots to the repository root
(`APOLLO_ROOT_DIR = CYBER_PATH = <repo_root>`) and links `<repo_root>/conf` to
Core's built `cyber/conf` directory. This establishes a single, uniform
root-relative paradigm for every sensor DAG:

- **`module_library`**: write the repository-root-relative path under
  `bazel-bin/`, for example:
  `bazel-bin/external/hardware.lidar+/vanjeelidar/libvanjeelidar_component.so`
- **`config_file_path`**: write the repository-root-relative path, for example:
  `deployment/examples/vanjee/conf/vanjee.pb.txt`
- **`mainboard -d`**: pass either a repository-root-relative path
  (`deployment/examples/vanjee/dag/vanjee.dag`) or an `$APOLLO_ROOT_DIR`-prefixed
  path (`"$APOLLO_ROOT_DIR/deployment/examples/vanjee/dag/vanjee.dag"`).

Because both `WorkRoot()` and `SoftwareRoot()` resolve to `<repo_root>`, these
paths work regardless of where the repository is cloned or which directory the
shell is currently in.
