# Sensor Bzlmod integration

Bazel 8.8.1 builds external camera/Hesai components through `bazel_dep`.
Driver sources are not copied here. This repository does not depend on
vehicle-infra or an Apollo checkout.

`//products/sensors:module` is the public contribution for a final system
using `@wheelos_core//runtime:runtime.bzl`. Core installs tools/configuration
once and deduplicates declared native runfiles. Sensor contributions contain
components, business configuration and root-relative DAG/launch resources.
`runtime_module` also retains declared FFmpeg SDK provenance/license runfiles.

`//products/sensors:runtime`, `:run`, `:package` and `:install` use that same
assembly contract with sensors as its only module. To add vehicle/algorithms,
compose their contributions into one runtime; never concatenate separate
installed core environments.

## Selection, configuration and SDK

```bash
bazel build --config=sensors-combined \
  --//products/sensors:camera_config=//deployment:camera.pb.txt \
  --//products/sensors:lidar_config=//deployment:lidar.pb.txt \
  //products/sensors:runtime //products/sensors:package
```

`sensors-camera`, `sensors-lidar` and `sensors-combined` select one product's
variants. Deployment labels above are examples, not defaults; each must expose
one reviewed configuration file. Missing selection/configuration fails at
analysis. Selecting/building/installing does not start a device.

FFmpeg is the shared `hardware.build` extension. Release requires the root's
checksummed SDK tag and declared runtime/license files; local SDK validation
requires explicit `FFMPEG_MODE=development`, include/library paths and runtime
library list. No ambient host-library scan is performed. GStreamer belongs to
hardware.camera_gst; RTKLIB belongs to hardware.gnss, not these product sources.

Use identical flags for archive and official rules_pkg installation:
`bazel run //products/sensors:install -- --destdir=/absolute/new/versioned/path`.
Choose a new directory outside customer data. Contents are `bin/commands`,
`bin`, `lib`, `bazel-bin/modules`, `modules/sensors`, and common `conf`.
`conf/system-manifest.json` records modules/content hashes, not a release lock.

## Validation and release boundary

The new `@wheelos_core//runtime` API requires an actual corrected module release.
Unchanged older registry snapshots do not provide it. Default registries remain
`.bazelrc.registry`; development uses explicit source overrides for core,
messages, relevant hardware modules and explicit SDK/toolchain configuration.
Local locks/source URLs must not be committed as release locks.

```bash
bazel test <EXPLICIT_LOCAL_SOURCE_OPTIONS> --config=sensors-combined \
  --flaky_test_attempts=1 --test_output=errors \
  //runtime:tests //tests/sensors:integration
```

The integration runtime uses only a private synthetic image component for
startup/pub/sub/recording/monitor checks. Selected real camera/Hesai plugins
are tested with `RTLD_NOW` only, never initialized. Test-only packaging configs
are separate from production configuration labels.

Apollo's final-system regression consumes this repository as an external
Bzlmod module alongside vehicle-infra, using one recorder and configuration,
independent process shutdown, archive extraction and official install relocation.
Local success is not published-module, physical-device or calibration acceptance.
