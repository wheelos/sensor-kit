# Agent Entry Point and Working Rules

Before making changes, read the relevant build targets, source code, and
authoritative documentation. More specific instructions in a subdirectory
take precedence.

## Documentation Layers

- `docs/`: authoritative architecture, build, operation, and validation
  documentation. Update `docs/README.md` when adding or moving documents.
- `.agents/skills/`: reusable workflows.
- `.agents/knowledge/`: verified, stable facts.
- `.agents/notes/`: temporary investigations; not authoritative architecture.
- `.github/`: project governance and automation.

## Project Conventions

- This repository is Sensor Kit. Its scope is sensor drivers, sensor
  configurations, sensor combinations, startup, and validation.
- `wheelos_core` is the middleware. It provides Cyber tools such as
  `mainboard`, `cyber_launch`, `cyber_recorder`, and `cyber_monitor`, along with
  component and configuration loading.
- Middleware and driver source code is maintained in external repositories.
  Pin and import it through `deps.repos` (`vcs import pkgs < deps.repos`), then
  build it with Bazel and `.bazelrc.dev`; do not copy those sources into Sensor
  Kit.
- `scripts/env.sh` configures the generic Core tools and Cyber environment. It
  sets `APOLLO_ROOT_DIR` and `CYBER_PATH` to the Sensor Kit repository root and
  links `conf` to Core's built Cyber configuration. It must not be coupled to
  one sensor, wrap Core commands, or start hardware.
- In sensor DAGs, use paths relative to the repository root for
  `module_library` (for example, `bazel-bin/external/...`) and
  `config_file_path` (for example, `deployment/examples/...`).
- Select SDKs, device configurations, and calibration explicitly. Building or
  activating the environment must not start hardware.
- Do not overwrite existing data or commit build outputs, imported `pkgs/`
  checkouts, runtime logs, credentials, private calibration, or device data.
- Run the smallest relevant validation for each change. Do not claim release,
  lockfile, or hardware acceptance results that were not verified.

## Entry Points

- [Documentation index](docs/README.md)
- [Sensor architecture](docs/architecture/sensor-sdk-plan.md)
- [Bazel build guide](docs/build/bazel-integration.md)
- [Sensor operation guide](docs/operations/sensor-runtime.md)
