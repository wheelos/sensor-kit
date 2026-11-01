"""Validate packaged Cyber tools with synthetic images; never start devices."""

import fcntl
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
import uuid

from python.runfiles import runfiles


class SensorIntegration(unittest.TestCase):
    def stop_process(self, process):
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)

    def check_monitor(self, root, env, topic):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 160, 0, 0))
        process = None
        output = b""
        try:
            process = subprocess.Popen(
                [str(root / "bin/cyber_monitor"), "-c", topic],
                env=dict(env, TERM="xterm"), stdin=slave, stdout=slave, stderr=slave,
                start_new_session=True,
            )
            deadline = time.monotonic() + 10
            while topic.encode() not in output and time.monotonic() < deadline:
                self.assertIsNone(process.poll(), output.decode(errors="replace"))
                if select.select([master], [], [], 0.2)[0]:
                    output += os.read(master, 65536)
            self.assertIn(topic.encode(), output, output.decode(errors="replace"))
            process.send_signal(signal.SIGINT)
            process.wait(timeout=10)
            self.assertEqual(process.returncode, 0, output.decode(errors="replace"))
        finally:
            if process is not None:
                self.stop_process(process)
            os.close(master)
            os.close(slave)

    def test_synthetic_message_recording_and_shutdown(self):
        resolver = runfiles.Create()
        source = Path(resolver.Rlocation(sys.argv[1]))
        probe = Path(resolver.Rlocation(sys.argv[2]))
        for tool in ["mainboard", "cyber_launch"]:
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "relocated runtime"
                shutil.copytree(source, root)
                topic = f"/sensor_infra/test/{uuid.uuid4().hex}/image"
                env = dict(os.environ, CYBER_DOMAIN_ID="194", CYBER_IP="127.0.0.1",
                           GLOG_logtostderr="1", SENSOR_INFRA_TEST_TOPIC=topic,
                           XDG_CACHE_HOME=str(Path(temporary) / "cache"))
                env.pop("WHEELOS_CONFIG_ROOT", None)
                log = Path(temporary) / "sensor.log"
                recorder_log = Path(temporary) / "recorder.log"
                recorder = None
                with log.open("w") as output:
                    arguments = (
                        ["start", "share/sensors/sensors.launch"]
                        if tool == "cyber_launch" else ["--dag_conf=share/sensors/selected.dag"]
                    )
                    process = subprocess.Popen(
                        [str(root / "bin" / tool), *arguments], env=env,
                        stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                    )
                    try:
                        with recorder_log.open("w") as recorder_output:
                            recorder = subprocess.Popen(
                                [str(root / "bin/cyber_recorder"), "record", "-c", topic,
                                 "-o", "./images.record", "-i", "0", "-m", "0"],
                                cwd=temporary, env=env, stdout=recorder_output,
                                stderr=subprocess.STDOUT, start_new_session=True,
                            )
                        self.check_monitor(root, env, topic)
                        time.sleep(0.5)
                        self.assertIsNone(process.poll(), log.read_text()[-6000:])
                        self.assertIsNone(recorder.poll(), recorder_log.read_text()[-6000:])
                        recorder.send_signal(signal.SIGINT)
                        recorder.wait(timeout=15)
                        self.assertEqual(recorder.returncode, 0, recorder_log.read_text()[-6000:])
                        records = list(Path(temporary).glob("images.record*"))
                        self.assertEqual(len(records), 1, recorder_log.read_text()[-6000:])
                        info = subprocess.run(
                            [str(root / "bin/cyber_recorder"), "info", records[0].name],
                            cwd=temporary, env=env, capture_output=True, text=True, timeout=10,
                        )
                        self.assertEqual(info.returncode, 0, info.stdout + info.stderr)
                        self.assertIn(topic, info.stdout)
                        verified = subprocess.run(
                            [str(probe), str(records[0]), topic],
                            env=dict(env, LD_LIBRARY_PATH=str(root / "lib")),
                            capture_output=True, text=True, timeout=10,
                        )
                        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
                        if tool == "cyber_launch":
                            stopped = subprocess.run(
                                [str(root / "bin/cyber_launch"), "stop", "share/sensors/sensors.launch"],
                                env=env, capture_output=True, text=True, timeout=15,
                            )
                            self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
                        else:
                            process.send_signal(signal.SIGINT)
                        process.wait(timeout=15)
                        self.assertEqual(process.returncode, 0, log.read_text()[-6000:])
                    finally:
                        if recorder is not None:
                            self.stop_process(recorder)
                        self.stop_process(process)
                self.assertIn("Cleanup synthetic sensor", log.read_text())
                print(f"Synthetic/{tool}: {verified.stdout.strip()}; terminal observed image; clean shutdown.")

    def test_selected_product_plugins_load_without_device_initialization(self):
        source = Path(runfiles.Create().Rlocation(sys.argv[3]))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "relocated product"
            shutil.copytree(source, root)
            env = dict(os.environ, XDG_CACHE_HOME=str(Path(temporary) / "cache"),
                       LD_LIBRARY_PATH=str(root / "lib"))
            env.pop("WHEELOS_CONFIG_ROOT", None)
            for tool, arguments in [
                ("doctor", []), ("mainboard", ["-h"]), ("cyber_launch", ["--help"]),
                ("cyber_recorder", ["--help"]), ("cyber_monitor", ["-h"]),
            ]:
                result = subprocess.run(
                    [str(root / "bin" / tool), *arguments], env=env,
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            plugins = [
                str(root / "lib" / name)
                for name in ["libcamera_component.so", "libhesai_component.so"]
                if (root / "lib" / name).exists()
            ]
            self.assertTrue(plugins)
            self.assertFalse((root / "lib/libsynthetic_sensor.so").exists())
            result = subprocess.run(
                [sys.executable, "-c",
                 "import ctypes, os, sys; "
                 "handles = [ctypes.CDLL(p, mode=os.RTLD_NOW) for p in sys.argv[1:]]",
                 *plugins],
                env=env, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(f"Selected product: {', '.join(Path(p).name for p in plugins)}; RTLD_NOW only, no devices.")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
