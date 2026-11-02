# Sensors in a shared Cyber runtime

Activate the final system's commands, not a separate sensor middleware root:

```bash
source /opt/wheelos/system/bin/setup.bash
cyber_launch start modules/sensors/launch/sensors.launch
```

The installed launch references the selected camera, Hesai or combined DAGs.
Startup requires reviewed device configuration and explicit hardware approval.
Build/install never initializes devices.

All modules/tools use one core/configuration root. Coordinate
`CYBER_DOMAIN_ID`, `CYBER_IP`, clock and transport settings across terminals
and services. Modules own business configuration under `modules/sensors/conf`,
not their own `conf/cyber.pb.conf`.

Mainboard/launch wrappers run from the system root; observation tools retain the
caller's cwd and arguments. Core prepares root/library paths before native exec,
ignoring ambient build-cache libraries. Extra SDK libraries require explicit
`WHEELOS_RUNTIME_LIBRARY_PATH`. Monitor needs a TTY/system terminfo.

```bash
cd /absolute/writable/data
cyber_recorder record -c /approved/image/topic -o ./images.record
cyber_recorder info ./images.record
cyber_monitor
```

One recorder/monitor serves sensors, vehicle and algorithms. SIGINT finalizes
the recorder. `play` publishes and requires an isolated approved domain/topic
set; never replay control-containing data into a live vehicle domain.

Paths are software-root-relative; the custom template renderer, `doctor` and
installer have been replaced by core assembly/manifest hashes and official
rules_pkg. Move the complete runtime/archive. Services should use absolute
wrapper paths instead of inherited shell activation. See the
[build/integration contract](../build/bazel-integration.md) for public module
contributions, SDK inputs and release boundaries.
