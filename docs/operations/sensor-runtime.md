# Local sensor operation

This guide covers the supported source-development workflow only. First
complete the dependency import and Bazel build in the
[build guide](../build/bazel-integration.md). The checked-in example is a
reference configuration; verify its network and model settings against the
device before starting it.

## Configuration and DAG paradigm

The example lives under [`deployment/examples/vanjee/`](../../deployment/examples/vanjee/):

- `conf/vanjee.pb.txt` selects model `vanjee_720_16`, host address
  `192.168.10.3`, and LiDAR address `192.168.10.6`.
- `dag/vanjee.dag` uses repository-root-relative paths for both
  `module_library` and `config_file_path`:

  ```protobuf
  module_config {
    module_library: "bazel-bin/external/hardware.lidar+/vanjeelidar/libvanjeelidar_component.so"
    components {
      class_name: "VanjeelidarComponent"
      config {
        name: "vanjeelidar_local"
        config_file_path: "deployment/examples/vanjee/conf/vanjee.pb.txt"
      }
    }
  }
  ```

  Because `scripts/env.sh` sets both `APOLLO_ROOT_DIR` and `CYBER_PATH` to the
  repository root and links `conf` to Core's `cyber/conf`, `mainboard` resolves
  both fields directly from the repository root regardless of the current
  working directory. Other sensors or multi-sensor DAGs follow the same rule
  (for example, `bazel-bin/external/hardware.lidar+/hesai/libhesai_component.so`
  or `bazel-bin/external/hardware.camera+/libcamera_component.so`).
- The published channels are
  `/apollo/sensor/vanjeelidar/up/PointCloud2` and
  `/apollo/sensor/vanjeelidar/up/Imu`.

Edit the example configuration if the host/device addresses or model differ.

## Start and observe

### NovAtel GNSS

The reference configuration in
[`deployment/examples/novatel/`](../../deployment/examples/novatel/) reads the
NovAtel binary stream from `/dev/ttyUSB4` at 460800 baud. Confirm that this
device node is connected to the receiver output and that no other process has
the serial port open before starting the component. The GNSS configuration
uses the `NOVATEL_BINARY` parser already provided by `hardware.gnss`; it does
not send receiver commands at startup.

The example currently selects UTM zone 50, but it is still provisional:
replace it with the confirmed deployment projection before relying on
odometry. The live receiver currently reports empty GPGGA coordinates, so the
zone cannot be inferred from this stream.

The receiver's legacy `RAWIMUB` log does not include an IMU model ID, so the
example explicitly selects the confirmed Murata `SCHA634_D03`. The supplied
receiver protocol defines acceleration scale as `frq / 655360` m/s^2/count
and angular-rate scale as `frq / 160849.543863` deg/s/count. Set
`rawimu_rate_hz` to the actual receiver output frequency; the example uses
100 Hz. The driver converts angular rate to rad/s and undoes the wire's
negative Y before applying the configured frame mapping.
In a subsequent live capture, the payload timestamps showed a
median 0.01 s interval, and 796 recorded published IMU messages had a median
acceleration norm of 9.781 m/s^2 (range 9.763-9.797 m/s^2). This supports the
100 Hz scale for that capture but does not validate all orientations or gyro
scale.
In a 1.5-second live sample, all 497 binary frames passed CRC validation.
The observed IDs and parser outcomes were:

| ID / log | Frames | Parser result and current data state |
|---|---:|---|
| 268 `RAWIMU` | 148 | Decoded and published to `/apollo/sensor/gnss/imu`; z counts 63,968-64,165. With the supplied receiver scale at 100 Hz this is approximately 9.76-9.79 m/s^2 on z; orientation, rate and physical calibration still require verification. |
| 507 `INSPVA` | 149 | Decoded and published to odometry/INS status. Latitude, longitude, height, and velocity are zero; INS status is `ALIGNING`. |
| 812 `CORRIMUDATA` | 149 | Decoded and published to `/apollo/sensor/gnss/corrected_imu`; all six delta fields were zero in this sample. |
| 99 `BESTVEL` | 8 | Frame recognized, but the invalid `INSUFFICIENT_OBS` solution is rejected; no valid velocity result is emitted. |
| 1429 `BESTGNSSPOS` | 8 | Decoded and published to best-pose/GNSS status; status is `INSUFFICIENT_OBS` and coordinates are zero. |
| 971 `HEADING` | 8 | Decoded and published; status is `INSUFFICIENT_OBS`, heading/baseline are zero. |
| 1465 `INSPVAX` | 15 | Decoded and published to INS status; `ins_status=ALIGNING`, position type is unavailable. |
| 140 `RANGECMP` | 2 | Not dispatched by this parser; raw bytes only. |
| 241 `BESTXYZ` | 8 | Not dispatched by this parser; raw bytes only. |
| 6005 | 2 | Not dispatched by this parser; raw bytes only. Meaning not identified from the current log definition. |

Among the other logs in the requested binary list, the parser implements
`BESTGNSSVELB`, GPS/BDS/GLO ephemerides, `HEADINGB`, `INSPVAB`, and
`INSPVAXB`; they were not observed in this capture. It does not implement
`BESTXYZB` (ID 241), `RANGEHB`, `RANGECMPB` (ID 140), or `GALEPHEMERISB`.
It also implements BESTPOS/PSRPOS, BESTVEL/PSRVEL, alternate RAWIMU and CORRIMU
formats, INS covariance, uncompressed RANGE observations, and INSPVAS; these
were not observed in this capture. `GPGGA`, `MARK1PVA`, and modern `CORRIMUS`
are not decoded by the current NovAtel parser; no such logs were identified
in this sample. The raw byte channel retains even unparsed frames for later
decoding.

The Cyber recorder independently confirmed live publication: over 2.37
seconds it recorded 237 messages each on `/apollo/sensor/gnss/imu` and
`/apollo/sensor/gnss/corrected_imu`, plus INS/GNSS status, best-pose, and
heading messages. The receiver reports `INSUFFICIENT_OBS` for position,
velocity, and heading; `INSPVA` coordinates and velocity are zero, and INS
status is `ALIGNING`. Although `/apollo/sensor/gnss/odometry` is also
published, its zero/invalid navigation solution must not be used.

For this receiver, the supplied `CORRIMUDATAB` protocol states that all six
increments are zero before the device enters integrated navigation and are
output normally after it enters that mode. Thus the observed zero fields are
consistent with the reported `ALIGNING` state, but neither a zero vector nor
`ALIGNING` alone proves the receiver's exact integration stage. The parser
does not suppress zero-valued messages or infer validity from them; consumers
must use the receiver's INS status, rather than the presence of the
`corrected_imu` topic, when deciding whether to use its values.

The supplied payload lists GPS week and seconds followed by six doubles:
pitch, roll and yaw angle increments around vehicle x/y/z, then lateral,
longitudinal and vertical velocity increments along x/y/z. The parser
multiplies these by `corrimu_rate_hz` to produce rad/s and m/s^2. The
published legacy `corrected_imu` vector retains the receiver's vehicle
right/forward/up axes; the raw IMU topic uses forward/left/up instead. The
receiver's exact correction semantics and the configured relationship
between vehicle and sensor axes still require device verification.

This confirms binary frame and payload decoding despite invalid header time;
it does not independently validate the receiver/RT1176 conversion, actual
output rate, axis orientation or physical IMU calibration. Treat
`/apollo/sensor/gnss/imu` values as uncalibrated until verified against the
device. The payload GPS week is 2243 (2023), so decoded
measurement timestamps are stale. Raw binary frames remain available on
`/apollo/sensor/gnss/raw_data`. The separate `corrimu_rate_hz: 100` matches
`CORRIMUDATAB ONTIME 0.01`.

The parser now validates each binary frame's sync, length, and CRC and decodes
payload-timed PVA/IMU messages using the time carried in their payload, even
when the frame header time is unavailable. Header-timed status logs are also
decoded without inventing measurement timestamps. The current receiver still
has no satellite fix: its coordinates are zero/empty and INS is aligning.
Decoded IMU/PVA values can be inspected, but GPS event timestamps may be stale
and position/odometry are not valid navigation results until receiver time
and solution status recover.

Build the component with the commands in the
[build guide](../build/bazel-integration.md), then start it:

```bash
bazel build --config=dev @@proj+//:proj_runtime_data
source scripts/env.sh
export PROJ_DATA="$APOLLO_ROOT_DIR/bazel-bin/external/proj+/data"
cyber_launch start "$APOLLO_ROOT_DIR/deployment/examples/novatel/launch/novatel.launch"
```

The GNSS component publishes channels including
`/apollo/sensor/gnss/raw_data`, `/apollo/sensor/gnss/gnss_status`,
`/apollo/sensor/gnss/ins_status`, `/apollo/sensor/gnss/odometry`,
`/apollo/sensor/gnss/corrected_imu`, and `/apollo/sensor/gnss/imu`.
`cyber_monitor` can inspect these channels while the component is running.
Press Ctrl+C in the launch terminal to stop it; Core's launch manager stops
the managed mainboard process.

Use separate terminals on the same host. Source the environment once in each
terminal; this exposes only the built Core commands and sets the Cyber
environment. `env.sh` also selects a system terminfo directory when
`TERMINFO` is not already set, which is needed by the curses-based monitor.

**Terminal 1 — start the driver:**

```bash
source scripts/env.sh
cyber_launch start "$APOLLO_ROOT_DIR/deployment/examples/vanjee/launch/vanjee.launch"
```

**Terminal 2 — inspect channels:**

```bash
source scripts/env.sh
cyber_monitor
```

`cyber_monitor` is interactive and requires a TTY. Keep `CYBER_IP` and
`CYBER_DOMAIN_ID` consistent across terminals. `env.sh` defaults to
`127.0.0.1` and domain `80`; set `CYBER_IP` to the reachable host address
before sourcing when observing from another host.

## Record and inspect

**Terminal 3 — record point cloud and IMU:**

```bash
source scripts/env.sh
mkdir -p "$HOME/data"
record_dir="$(mktemp -d "$HOME/data/vanjee.XXXXXX")"
record_base="$record_dir/vanjee.record"
cyber_recorder record \
  -c /apollo/sensor/vanjeelidar/up/PointCloud2 \
  -c /apollo/sensor/vanjeelidar/up/Imu \
  -o "$record_base"
```

Press Ctrl+C to finalize the recording. In the same terminal, inspect the first
completed segment:

```bash
cyber_recorder info "${record_base}.00000"
```

Core writes numbered segments, for example `vanjee.record.00000`. The recorder
stores Cyber channel messages, not raw UDP packets. The unique temporary
directory keeps this example from overwriting an existing recording.

## Verified hardware scope

The configured device at `192.168.10.6` was started with `mainboard`; the
monitor displayed the PointCloud2 channel. An approximately 10-second
recording contained both expected channels: 101
`apollo.drivers.PointCloud` messages and 1008
`apollo.drivers.vanjee.VanjeeImu` messages in one verification run. This
confirms acquisition for that device, network, and configuration only; it is
not a reliability, calibration, or other-hardware certification.
