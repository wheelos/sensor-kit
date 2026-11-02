# Sensor product boundaries

- This repository assembles only `products/sensors`. Camera, Hesai and their
  combined selection are variants of one product, not separate products.
- Driver implementations remain external `hardware.camera`/`hardware.lidar`
  Bzlmod modules. No vehicle-infra checkout or product dependency is required.
- `hardware.build` supplies shared FFmpeg rules; the root selects SDK inputs.
  SDK archive mode is the default, local discovery is explicit development mode.
- `products/sensors:module` contributes components, business files and declared
  SDK dependencies through core's `RuntimeModuleInfo`; it owns no Cyber tools
  or middleware configuration. `build/runtime.bzl` only re-exports core rules.
- Core's `runtime_layout` assembles one tools/configuration root for one or more
  module contributions. Public `bin/commands` entries establish artifact roots;
  recorder/monitor retain caller-relative paths.
- `products/sensors:runtime`, `:package` and `:install` use the same core layout
  and official rules_pkg packaging. Multi-module systems consume `:module`,
  rather than concatenating separately installed runtime trees.
- Device configuration and selection are mandatory. No live performance client
  or device acceptance is implied by a successful package or tool smoke test.
- `tests/sensors` uses private synthetic images for Cyber tool validation and
  loads production plugins without instantiating devices; it is never shipped.
- See [build](../../docs/build/bazel-integration.md) and
  [operation](../../docs/operations/sensor-runtime.md).
