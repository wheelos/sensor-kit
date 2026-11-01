# Sensor product boundaries

- This repository assembles only `products/sensors`. Camera, Hesai and their
  combined selection are variants of one product, not separate products.
- Driver implementations remain external `hardware.camera`/`hardware.lidar`
  Bzlmod modules. No vehicle-infra checkout or product dependency is required.
- `hardware.build` supplies shared FFmpeg rules; the root selects SDK inputs.
  SDK archive mode is the default, local discovery is explicit development mode.
- `build/runtime.bzl` collects declared component/Cyber runfiles and SDK metadata.
- The product explicitly delivers core's mainboard, launcher, recorder and
  monitor. Shared entries establish artifact roots before native execution;
  recorder/monitor retain caller-relative paths (`runtime/entry.py`).
- `runtime/` renders relocatable configuration, combines selected DAGs and
  installs without overwriting customer data. Its cache uses `sensor-infra`.
- Device configuration and selection are mandatory. No live performance client
  or device acceptance is implied by a successful package or `doctor`.
- `tests/sensors` uses private synthetic images for Cyber tool validation and
  loads production plugins without instantiating devices; it is never shipped.
- See [build](../../docs/build/bazel-integration.md) and
  [operation](../../docs/operations/sensor-runtime.md).
