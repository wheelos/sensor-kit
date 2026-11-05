# Sensor architecture and path-resolution facts

- **Four-layer boundary**:
  1. `wheelos_core` is the Cyber RT middleware providing `mainboard`,
     `cyber_launch`, `cyber_recorder`, `cyber_monitor`, `ModuleController`, and
     `ResourceManager`.
  2. `deps.repos` pins exact Git commits for `core`, `common`, `transform`,
     `wheelos_msgs`, and `hardware`, imported into gitignored `pkgs/` via
     `vcs import pkgs < deps.repos`.
  3. `.bazelrc.dev` maps Bzlmod modules to `%workspace%/pkgs/...` for local
     Bazel builds (`--config=dev`).
  4. `sensor-kit` exposes top-level targets in `BUILD.bazel` (`//:core_tools`,
     `//:vanjeelidar`, `//:hesai`, `//:camera`), sets up the runtime
     environment via `scripts/env.sh`, and maintains reference sensor DAG/conf
     files under `deployment/examples/`.
- **Unified root-relative DAG paradigm**:
  - In `wheelos_core`, `ModuleController::LoadModule` resolves relative
     `module_library` paths against `common::WorkRoot()` (`CYBER_PATH`), while
     `ComponentBase::ResolveComponentConfigPath` resolves non-`modules/`
     relative `config_file_path` entries against `common::WorkRoot()` and then
     validates through `ResourceManager::ResolveConfigPath` that the canonical
     file resides inside `SoftwareRoot()` (`APOLLO_ROOT_DIR`).
  - `scripts/env.sh` sets both `APOLLO_ROOT_DIR` and `CYBER_PATH` to the
     repository root and symlinks `<repo_root>/conf` to Core's built
     `cyber/conf` directory.
  - Consequently, every DAG file uses repository-root-relative paths without
    `../` traversal or `/apollo/` prefixes:
    - `module_library`: `bazel-bin/external/<module>/<pkg>/lib<component>.so`
    - `config_file_path`: `deployment/examples/<sensor>/conf/<sensor>.pb.txt`
- See [architecture](../../docs/architecture/sensor-sdk-plan.md),
  [build](../../docs/build/bazel-integration.md), and
  [operation](../../docs/operations/sensor-runtime.md).
