# Documentation

- [Build and development workflow](build/bazel-integration.md): pinned source
  dependencies, Bazel development build, and current install TODO.
- [Local Vanjee operation](operations/sensor-runtime.md): DAG/config path
  paradigm, start, inspect, and record a physical LiDAR using Core tools.
- [Architecture](architecture/sensor-sdk-plan.md): middleware/product roles,
  repository layout, and DAG/config resolution rules.

The supported workflow in this checkout is source development. The installed
runtime workflow is marked TODO in the build guide.

Vehicle, CAN, and whl-can are maintained in the independent `vehicle-infra`
repository and are not dependencies of this repository.
