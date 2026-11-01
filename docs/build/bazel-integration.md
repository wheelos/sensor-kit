# Independent sensors Bzlmod build

## Dependency contract

This repository compiles externally published sources using `bazel_dep`.
It does not manage driver sources or require any Apollo-lite checkout.
Vehicle/CAN/whl-can content is maintained separately in `vehicle-infra`;
this root does not depend on that repository or declare its driver modules.
`scripts/bazel.py` is an optional executable selector; it forwards Bazel
arguments without injecting registries, module overrides or compiler fixes.

The module publisher must provide:

- A reachable registry with immutable module metadata and source archives.
- All transitive dependencies and verified checksums.
- Public component targets and matching Cyber runtime/configuration targets.
- Required target OS, architecture, compiler, system libraries and SDKs.
- Corrected source headers and explicit target SDK discovery; do not retain
  forced compiler includes as a release workaround.

`.bazelrc.registry` configures `https://bcr.wheelos.cn/` followed by
`https://bcr.bazel.build/`, following the remote registry order used upstream.
It excludes the upstream source-tree registry and does not disable locks.

**Release builds are currently blocked.** The configured WheelOS registry
returns HTTP 404 for `hardware.build`, `hardware.camera`, and
`hardware.lidar` version `0.1.0`. A direct Bazel build
now fails resolving `hardware.camera@0.1.0`. No fallback to local driver
sources is configured. Publishing external modules is outside this repository.

The product explicitly selects core's recorder/monitor. Core `1.0.6` has a
standalone recorder compilation error: `subscription_selector.h` uses
`uint32_t` without `<cstdint>`. The reviewed upstream fix is local core commit
`87f4203`. Development tests use the same checksummed registry patch as vehicle;
release requires an immutable published core containing the fix and a newly
resolved release lock. No default source override or forced include is added.

## Product targets

| Product | Configuration | Components |
|---|---|---|
| sensors | `sensors-camera` | camera |
| sensors | `sensors-lidar` | Hesai LiDAR |
| sensors | `sensors-combined` | camera and Hesai LiDAR |

These are variants of one sensors product. Sensor selections are initial supported
variants; adding other external devices requires an explicit component,
configuration and launch integration. The existing external LiDAR module may
resolve multiple vendor SDKs; selecting one component limits build/package
contents, not necessarily registry resolution. Finer dependency isolation
requires the module publisher to split those modules.

A configuration label must expose exactly one reviewed text-protobuf file.
Create a local Bazel package for deployment configuration, or provide one
from an explicitly declared external configuration module. Driver source
must not be copied into this repository. For example:

```starlark
# deployment/BUILD.bazel (deployment-specific, not supplied by default)
exports_files(["camera.pb.txt", "lidar.pb.txt"])
```

Do not commit credentials or private calibration. Relative calibration/device
inputs must be reviewed for the runtime working directory; absolute device
paths remain deployment inputs. Configuration supports explicit
`@RUNTIME_ROOT@` and `@CONFIG_ROOT@` tokens, not arbitrary shell expansion.

Once the actual registry is available:

```bash
bazel build --config=sensors-combined \
  --//products/sensors:camera_config=//deployment:camera.pb.txt \
  --//products/sensors:lidar_config=//deployment:lidar.pb.txt \
  //products/sensors:runtime //products/sensors:package
```

Deployment labels above are placeholders, not executable defaults.
The external build settings/targets must match the published module
versions. No device configuration is supplied by default. All build options
must also be supplied to `bazel run ...:install`.

Resolve and review `MODULE.bazel.lock`, commit it, then repeat with
`--config=release`. The current lock was generated using the local development
registry, not remote release metadata. Product manifests include declared module text, its hash, component
and configuration labels, file hashes and a lock hash when available.

## Packaging and installation

Each product provides `:runtime`, `:package`, and `:install`.
Installation requires an absolute nonexistent destination and never starts
hardware or overwrites customer data:

```bash
# Include the same registry/profile/config options as the build.
bazel run <BUILD_OPTIONS> //products/sensors:install \
  -- --destdir=/opt/sensors-runtime-v1
```

The package is `runtime.tar.gz` in the product output directory. Customers
need target-compatible system dependencies, Bash and Python 3, but do not need
Bazel, Git, source checkouts or a development container.

## Checks available without published modules

```bash
python3 -m unittest discover -s runtime -v
```

These validate packaging logic with synthetic inputs, not driver compilation,
ELF compatibility, device operation or sensor performance. Additional
local-registry compilation and ELF checks are described below;
real-device acceptance remains a release gate.

## Explicit local registry validation

The developer's local registry contains snapshot entries for the three
sensor-root `hardware.*@0.1.0` modules and the transitive
`wheelos_transform@0.1.0`. Each entry has the original module declaration,
checksummed source archive, revision provenance and a development-only marker.
Archives are persisted in that registry's ignored `.local-archives/` directory.
They are not driver source copies in this product repository and do not use
module overrides.

To prepare an equivalent registry on another machine, before entries exist:

```bash
python3 scripts/register_local_modules.py \
  --source /path/to/module-source-checkout \
  --registry /path/to/local-registry \
  --archives /path/to/local-registry/.local-archives
```

The tool refuses modified module sources and existing version entries. These
local snapshot URLs are machine-specific and must not be published as release
entries; production needs immutable hosted archives.

The local camera/build registry entries apply the shared hardware FFmpeg fixes.
These patches are local development metadata until corrected module versions
are published. The original archived snapshots remain unchanged.
Local-registry lockfiles record machine-specific source URLs; do not mistake them for a
remote-registry release lock.

Local validation results:

- Camera-only, Hesai-only and combined runtimes/archives pass with explicitly
  selected local modules and the core recorder patch. The runtime suite has
  12 passing unit tests. Each variant passes the selected-plugin/synthetic
  Cyber integration target: both startup modes, recorded image decoding,
  terminal monitor and clean shutdown, with no device initialization.
- The actual combined installer and archive extraction pass relocation,
  including an installation path containing spaces. All four packaged Cyber
  tool help entries and `doctor` work despite invalid ambient Cyber/library
  roots; camera and Hesai load with `RTLD_NOW` from packaged/system libraries
  without FFmpeg SDK environment variables. Synthetic libraries/probes are
  absent from the production runtime.
- The Hesai-only sensors runtime/archive builds independently of camera.
- Camera and combined sensors runtime/archive builds now pass using an
  independently provisioned Ubuntu FFmpeg SDK. Camera and Hesai shared-library
  dependencies resolve from the package and supported target system libraries.
  A relocated installation passes preparation and `RTLD_NOW` loading of both
  plugins without creating components or initializing devices.
- Camera, video and the upstream product root now use the same
  `@hardware.build//third_party/ffmpeg:extensions.bzl` extension. There is one
  implementation and one repository identity, rather than three copies.
- The default requires a root-selected, checksummed SDK archive. Local SDK
  discovery requires explicit `FFMPEG_MODE=development`; paired
  `FFMPEG_INCLUDE_DIR`/`FFMPEG_LIBRARY_DIR` take precedence over an explicitly
  set legacy sysroot and `pkg-config`. No default `/opt/apollo` path exists.
- Runtime libraries are enumerated, not collected using a `.so` directory
  glob. Development uses comma-separated `FFMPEG_RUNTIME_LIBRARIES` basenames
  from `FFMPEG_RUNTIME_LIBRARY_DIR`; archive mode uses relative `runtime_files`.
  Both must include the required versioned SONAMEs and transitive SDK libraries.
- Archive mode requires version and license files. SDK metadata and licenses
  are packaged under `share/dependencies/ffmpeg`. This preserves supplied
  provenance; it does not constitute a license compliance certification or
  automatic target-architecture validation.

Run packaging tests from the sensor repository:

```bash
# CORE_PATCH_REGISTRY is an absolute private development registry directory.
# Ignore default release registries to ensure the patch registry is first.
LOCAL_OPTIONS=(
  "--registry=file://${CORE_PATCH_REGISTRY}"
  --registry=file:///home/humble/01code/apollo-lite/pkgs/bazel-central-registry
  --registry=https://bcr.bazel.build
)
bazel --ignore_all_rc_files test "${LOCAL_OPTIONS[@]}" \
  //runtime:tests --test_output=all
```

Prepare a separate patch registry containing the original core
`modules/wheelos_core/1.0.6/MODULE.bazel` and original `source.json`, retaining
its archive URL, integrity and strip prefix. Do not overwrite existing
published/local registry entries. Export the reviewed patch into its
`modules/wheelos_core/1.0.6/patches/` directory:

```bash
git -C /home/humble/01code/apollo-lite/pkgs/core show --format= 87f4203 -- \
  cyber/tools/cyber_recorder/record/selector/subscription_selector.h \
  > "${CORE_PATCH_REGISTRY}/modules/wheelos_core/1.0.6/patches/recorder-cstdint.patch"
```

Add `"patches": {"recorder-cstdint.patch": "sha256-ACTUAL_PATCH_SHA256_BASE64"}`
and `"patch_strip": 1` to the original source metadata.
Compute the real integrity with
`openssl dgst -sha256 -binary recorder-cstdint.patch | base64`.
Patch keys are filenames under `patches/`, not paths prefixed with `patches/`.
This is development metadata only; do not commit its machine-specific lock as
a release lock. The upstream source fix is already committed separately.

LiDAR packaging-only command:

```bash
bazel --ignore_all_rc_files build "${LOCAL_OPTIONS[@]}" \
  --//products/sensors:selection=lidar \
  --//products/sensors:lidar_config=//tests/fixtures:sensor-package-only.pb.txt \
  //products/sensors:runtime //products/sensors:package
```

The sensor fixture is deliberately not a valid operational configuration.
Do not launch it. Build/preparation/ELF checks do not prove sensor performance.

Combined sensors packaging (provide target-compatible SDK paths):

```bash
FFMPEG_INCLUDE_DIR=/path/to/sdk/include \
FFMPEG_LIBRARY_DIR=/path/to/sdk/lib \
FFMPEG_RUNTIME_LIBRARY_DIR=/path/to/sdk/runtime-lib \
FFMPEG_RUNTIME_LIBRARIES=libavcodec.so.60,libavutil.so.58,OTHER_REQUIRED_SONAMES \
FFMPEG_MODE=development \
bazel --ignore_all_rc_files build "${LOCAL_OPTIONS[@]}" \
  --//products/sensors:selection=combined \
  --//products/sensors:camera_config=//tests/fixtures:sensor-package-only.pb.txt \
  --//products/sensors:lidar_config=//tests/fixtures:sensor-package-only.pb.txt \
  //products/sensors:runtime //products/sensors:package
```

The SDK used for local validation was downloaded/extracted under the session's
`files/ffmpeg-sdk`, without privileged installation or changing system packages.
The produced product does not need that SDK directory for the tested ELF
dependency closure.

An external root does not inherit dependency `.bazelrc` profiles; the local
commands select variants/config labels explicitly. For camera-only, use
`selection=camera` and omit `lidar_config`. Repeat these same build options for
the actual installer.

The private integration target checks selected production plugins with
`RTLD_NOW` only and runs a separate test-only synthetic image component through
the same product packaging rule:

```bash
bazel --ignore_all_rc_files test "${LOCAL_OPTIONS[@]}" \
  --//products/sensors:selection=lidar \
  --//products/sensors:lidar_config=//tests/fixtures:sensor-package-only.pb.txt \
  //runtime:tests //tests/sensors:integration --test_output=all
```

Use the selected camera/combined SDK and configuration options for those
variants. Tests verify both launcher/mainboard modes, recorder output in the
caller's directory, packaged `info`, decoded image payloads/descriptors,
terminal monitor and clean shutdown on UUID topics. They separately verify
all four tool help entries, `doctor` and selected plugin loading after
relocation. Test components/probes are private and test-only, and never enter
`//products/sensors:runtime` or its archive. No real devices are initialized,
and the packaging fixture is never launched.

## Shared FFmpeg release SDK

The driver modules only import the shared extension; the product root selects
one SDK. The same root-selected SDK is used by all consumers. A dependency
module cannot select its own SDK or override the root.

```starlark
ffmpeg = use_extension("@hardware.build//third_party/ffmpeg:extensions.bzl", "ffmpeg")
ffmpeg.sdk(
    urls = ["https://YOUR-ARTIFACT-HOST/ffmpeg-linux-x86_64.tar.gz"],
    integrity = "sha256-REPLACE_WITH_REAL_ARCHIVE_INTEGRITY",
    version = "FFMPEG_VERSION_AND_BUILD_ID",
    strip_prefix = "sdk",
    include_dir = "include",
    library_dir = "lib",
    runtime_files = [
        "lib/libavcodec.so.60",
        # Enumerate every SONAME and SDK dependency actually required.
    ],
    license_files = ["licenses/ffmpeg-copyright"],
)
```

This is a schema example, not a complete SDK manifest. The archive publisher
must specify platform, compiler/ABI, FFmpeg build options, full runtime closure
and all relevant license records. Integrity pins archive bytes; it does not
establish compatibility with arbitrary targets. No hosted SDK release has been
invented or published here.

Both development and archive SDK modes were validated locally. Archive mode
compiled the combined sensors package without FFmpeg environment variables;
a relocated artifact loaded camera and Hesai plugins using its packaged
libraries. The artifact included the selected SDK integrity/version and 42
supplied license records. No device components were instantiated.

The existing LiDAR module still declares transform and multiple vendor SDKs
at module resolution time. Product selection limits compilation and runtime
contents, not that module's dependency graph. The vehicle/sensors product roots
are now separate repositories with their own
module declarations and locks. Splitting the external LiDAR module's internal
public modules remains a publisher migration; that finer isolation is not
claimed here.
