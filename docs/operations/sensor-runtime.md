# Local Vanjee operation

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

Use separate terminals on the same host. Source the environment once in each
terminal; this exposes only the built Core commands and sets the Cyber
environment. `env.sh` also selects a system terminfo directory when
`TERMINFO` is not already set, which is needed by the curses-based monitor.

**Terminal 1 — start the driver:**

```bash
source scripts/env.sh
mainboard -d "$APOLLO_ROOT_DIR/deployment/examples/vanjee/dag/vanjee.dag"
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
