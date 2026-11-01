# Independent sensors runtime

The repository assembles external camera/LiDAR components with matching Cyber
tools, reviewed device configuration and declared shared-library runfiles.
Customers do not need vehicle-infra, Apollo-lite, source, Git or Bazel to run
a successfully built compatible artifact.

```text
sensors-runtime/
├── bin/                 # mainboard, cyber_launch, cyber_recorder, cyber_monitor, doctor
├── lib/                 # selected plugins and shared-library runfiles
├── libexec/             # matching mainboard, launcher and entry
├── conf/                # Cyber configuration
├── share/sensors/       # reviewed device configuration and DAG/launch
├── share/dependencies/  # selected FFmpeg metadata/licenses, when applicable
└── manifest.json
```

The entry verifies checksums and renders `@RUNTIME_ROOT@`/`@CONFIG_ROOT@` into
`${XDG_CACHE_HOME:-~/.cache}/sensor-infra/<identity>`. Identity includes the
installation path and manifest, so relocated artifacts regenerate paths
without rewriting the installation. Start/stop share the same rendered launch.

`APOLLO_ROOT_DIR` and `CYBER_PATH` point at prepared configuration, not a
source repository. Prepared `bin` leads `PATH`; the launcher uses its packaged
mainboard. Library search uses packaged `lib` and explicitly requested
`WHEELOS_RUNTIME_LIBRARY_PATH`, not ambient `LD_LIBRARY_PATH`.
Known source-tree paths in templates are rejected; message topic names do not
imply a source-repository dependency.

All four Cyber entries share the same artifact/environment bootstrap.
Installed `bin` follows prepared `bin` in `PATH`, making the same artifact's
recorder/monitor available to explicitly declared binary launch entries.
No shell setup script or global environment modification is required.
`CYBER_DOMAIN_ID`, `CYBER_IP` and explicit logging settings are inherited;
online tools must share the sensors' reviewed domain and network settings.
`WHEELOS_CONFIG_ROOT` is rejected explicitly, including an empty value, to
prevent ambient file overrides bypassing immutable product configuration.

Launch XML `<environment>` only affects the launcher and its children.
It is applied after initial launch resolution/mainboard selection and does
not configure tools in another terminal or direct mainboard startup.
It cannot replace the bootstrap. ELF library search must be established before
starting native programs, not inside mainboard's `main()`. Reviewed launch
files must not redirect bootstrap roots or libraries to another installation.

## Start and stop

After building/installing with actual reviewed device configuration:

```bash
/opt/sensors-runtime-v1/bin/doctor
/opt/sensors-runtime-v1/bin/cyber_launch start share/sensors/sensors.launch
/opt/sensors-runtime-v1/bin/cyber_launch stop share/sensors/sensors.launch

# Alternative single-component debug entry, not a second simultaneous instance:
/opt/sensors-runtime-v1/bin/mainboard -d share/sensors/camera.dag
```

Select `lidar.dag` for a LiDAR-only artifact, or `selected.dag` for all selected
components. Direct mainboard is stopped with SIGINT/Ctrl-C. Absolute packaged
DAG/launch paths are accepted. Do not launch the source-tree templates with a
generic system launcher; use the package entry and its `share/sensors` paths.
Mainboard accepts `-d FILE`, `-dFILE`, `--dag_conf FILE` and `--dag_conf=FILE`,
including repeated explicit options. Tool help remains available through
`mainboard -h` and `cyber_launch --help`.

The combined launch contains only build-selected components. Camera-only
artifacts have no LiDAR DAG and vice versa. Calibration/resource paths,
vendor SDK/system ABI, USB/network/device permissions and time synchronization
remain explicit deployment requirements.

## Recorder and monitor

Cyber does not need a central daemon before these tools start. Recorder and
monitor run independently of device components. Core provides the tools;
this product explicitly packages them and their declared shared-library
dependencies. Select a topic actually published by the reviewed configuration:

```bash
# In each terminal, use the same deployment communication settings.
/opt/sensors-runtime-v1/bin/cyber_monitor -c /YOUR_REVIEWED_SENSOR_TOPIC

# Run from a writable data directory, not the installation or config cache:
/opt/sensors-runtime-v1/bin/cyber_recorder record \
  -c /YOUR_REVIEWED_SENSOR_TOPIC -o ./sensor.record
# Ctrl-C finalizes the record; use the actual output filename:
/opt/sensors-runtime-v1/bin/cyber_recorder info ./ACTUAL_RECORD_FILE
```

Recorder/monitor keep the invoking working directory and forward their native
arguments unchanged. Relative recording input/output and recorder YAML paths
therefore refer to the caller's directory, not the prepared configuration cache.
Starting/stopping a recorder does not start/stop sensors.

Do not add the interactive monitor to device launch: the launcher captures
subprocess output, while monitor needs a terminal UI. No automatic recorder
or recorder-dependent sensor lifecycle is configured.

**`cyber_recorder play` publishes messages and is not read-only diagnosis.**
Use an isolated, approved playback environment and an explicit topic allowlist;
do not publish recorded device data into a live domain or replay control topics.

## Verification boundary

`doctor` reports only file integrity and template rendering. It does not
initialize devices, check semantic protobuf validity, load plugins or prove
message flow, data quality or performance.

The packaging-only fixture is not operational configuration: never launch
its artifact against devices. Build/installation/ELF checks are not a sensor
acceptance test. No live performance client is currently packaged. Validate
frame rate, drops, timestamps, synchronization and calibration separately.
The private `//tests/sensors:integration` uses a synthetic image timer component,
unique test topics and a loopback test domain. It verifies real packaged
mainboard/launcher, recorder payloads/descriptors and terminal monitor shutdown;
it does not initialize hardware. Production artifacts are separately checked
with `RTLD_NOW` loading only, never component instantiation.
See [build and SDK contract](../build/bazel-integration.md).
