# Sensor product architecture

## Independent product root

`sensor-infra` packages camera/LiDAR drivers into one sensors runtime.
Camera-only, Hesai-only and combined artifacts are build variants of that
product. Vehicle/CAN/whl-can belong to the independent `vehicle-infra` root;
no sibling checkout, module override or product dependency is required.

| Module | Responsibility |
|---|---|
| `hardware.camera` | Camera component and driver |
| `hardware.lidar` | Selected LiDAR component and vendor dependencies |
| `hardware.build` | Shared build settings and FFmpeg extension |
| `wheelos_core` | Matching Cyber runtime and process tools |

`MODULE.bazel`, its generated lock, build profiles and packaging targets are
owned by this repository. Common packaging infrastructure is local to each
standalone repository; no dependency on vehicle-infra is introduced.

## Layout and responsibilities

- `products/sensors`: selection, explicit device configuration and DAG/launch.
- `build/`: declared component/runfile collection, SDK metadata and archive rules.
- `runtime/`: assembly, selected-DAG combination, integrity/relocation and install.
- `tests/fixtures`: packaging-only data, never operational device configuration.
- `tests/sensors`: private synthetic-image Cyber integration and plugin loading,
  never a shipped sensor driver or performance client.
- `docs/`: build contract, operations and acceptance limits.

Driver sources remain external `bazel_dep` archives. Shared FFmpeg discovery
is implemented only in external `hardware.build`; the product root supplies
one checksummed SDK with explicit runtime files, version and license records.
Local discovery is an opt-in development mode.

## Cyber tool and deployment boundary

Core owns Cyber runtime libraries, public tool targets and generic resource
resolution. Hardware modules own device components and their declared runtime
resources. The sensors product root selects components, reviewed configuration,
tools, DAG/launch templates and an installation/integrity policy. No vehicle
product dependency, sibling source setup script or driver source copy is used.

The runtime explicitly packages mainboard, cyber_launch, cyber_recorder and
cyber_monitor, including each native tool's shared-library runfiles. A
`bazel_dep` does not implicitly deliver every executable in a module.
Shared entries establish artifact roots and library search before executing
native tools, while retaining the original CLI. Recorder/monitor preserve the
calling directory; launch/mainboard resolve declared prepared product files.
Ambient `WHEELOS_CONFIG_ROOT` overrides are explicitly rejected because product
configuration is immutable within an artifact.

The final external product root must select camera/lidar/combined and device
configuration labels explicitly; dependency `.bazelrc` profiles are not
inherited. Installed paths do not depend on Bazel external directory names.
Tools and components are delivered as one versioned closure, rather than relying
on a separately installed system core. Generic packaging code is maintained
locally, following the same paradigm as vehicle without importing its files.

## Validation and remaining gates

Packaging tests cover camera-only, LiDAR-only and combined DAG selection,
relocation, manifest checks, path rejection and non-overwriting installation.
Local-registry package/ELF validation does not initialize devices.
Test-only synthetic images validate both mainboard/launch lifecycle, recorder
payload/descriptor roundtrip and terminal monitoring using the production
packaging rule. Synthetic components/probes never enter the production runtime.
This establishes Cyber tool integration, not actual device message delivery,
frame rate, synchronization, calibration or performance acceptance.

The LiDAR publisher still declares transform and multiple vendor SDKs during
resolution; this root split does not split that external module internally.
Production needs immutable hosted modules/SDK, a reviewed remote lock, ABI
compatibility, valid calibration/configuration and approved device tests.
Frame/drop rate, timing/synchronization, data quality and a live performance
client are independent acceptance items, not consequences of `doctor`.
