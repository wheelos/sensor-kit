# Sensor Kit

Sensor Kit combines external sensor drivers with
[wheelos_core](https://github.com/wheelos/core), which provides the Cyber
middleware, component loader, recorder, and monitor. Driver and middleware
sources are imported with VCS; Bazel builds the selected tools and drivers.

This quick start builds and runs the Vanjee LiDAR example. It assumes a Linux
host, a connected Vanjee LiDAR, and network access to the device.

## 1. Clone and prepare dependencies

Install Git, curl, a C++ toolchain, Ninja, vcstool, and
[Bazelisk](https://github.com/bazelbuild/bazelisk#installation). The repository
selects Bazel 8.8.1 through `.bazelversion`.

```bash
git clone https://github.com/wheelos/sensor-kit.git
cd sensor-kit

sudo apt update
sudo apt install git curl build-essential ninja-build python3-vcstool
vcs import pkgs < deps.repos
```

`deps.repos` pins the external source revisions. `pkgs/` is managed by VCS and
ignored by this repository's Git tracking. Third-party Bazel modules are
fetched from the registries configured in `.bazelrc.registry`.

## 2. Build the driver and Core tools

```bash
bazel build --jobs=4 --config=dev //:vanjeelidar //:core_tools
```

The `dev` profile in `.bazelrc.dev` maps Bazel modules to the VCS checkouts in
`pkgs/`. The build does not start the sensor.

## 3. Check the device configuration

The example at
[`deployment/examples/vanjee/conf/vanjee.pb.txt`](deployment/examples/vanjee/conf/vanjee.pb.txt)
uses model `vanjee_720_16`, host address `192.168.10.3`, and LiDAR address
`192.168.10.6`. Confirm or edit these values for your device and host before
starting it.

## 4. Start the driver

In **Terminal 1**, from the repository directory:

```bash
source scripts/env.sh
mainboard -d "$APOLLO_ROOT_DIR/deployment/examples/vanjee/dag/vanjee.dag"
```

## 5. View channels

In **Terminal 2**, from the repository directory:

```bash
source scripts/env.sh
cyber_monitor
```

Look for:

- `/apollo/sensor/vanjeelidar/up/PointCloud2`
- `/apollo/sensor/vanjeelidar/up/Imu`

`cyber_monitor` is interactive and requires a terminal.

## 6. Record point cloud and IMU

In **Terminal 3**, from the repository directory:

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

Press Ctrl+C to finalize the recording, then inspect the first record segment
in the same terminal:

```bash
cyber_recorder info "${record_base}.00000"
```

Core writes numbered record files such as `vanjee.record.00000`. The unique
directory created by `mktemp` avoids overwriting existing recordings. Stop
`mainboard` with Ctrl+C in Terminal 1 when finished.

## More information

- [Build and development workflow](docs/build/bazel-integration.md)
- [Vanjee configuration, startup, and recording details](docs/operations/sensor-runtime.md)
- [Architecture and path resolution](docs/architecture/sensor-sdk-plan.md)

The supported workflow currently uses source checkouts and Core tools. The
installed runtime workflow is not yet available.
