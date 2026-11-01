import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from assemble import assemble
from entry import command, prepare, runtime_environment
from install import install


ROOT = Path(__file__).absolute().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.base / "cache")})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def create(self, sensors=("camera",)):
        product = "sensors"
        mainboard = self.base / "mainboard"
        mainboard.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n")
        config = self.base / "config.pb.txt"
        config.write_text("reviewed_config: true\n")
        module = self.base / "MODULE.bazel"
        module.write_text('module(name = "test_only")\n')
        entries = [
            [str(mainboard), "libexec/mainboard", "binary"],
            [str(ROOT / "runtime/entry.py"), "libexec/entry.py", "binary"],
        ]
        tool = self.base / "tool.py"
        tool.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "print(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:], "
            "'env': dict(os.environ)}))\n"
        )
        tools = {name: "test_tool" for name in ["cyber_recorder", "cyber_monitor"]}
        entries += [[str(tool), "libexec/" + name, "binary"] for name in tools]
        names = ["sensors.launch", *[sensor + ".dag" for sensor in sensors]]
        entries += [
            [str(ROOT / "products" / product / name), f"share/{product}/{name}", "template"]
            for name in names
        ]
        entries += [
            [str(config), f"share/{product}/{name}.pb.txt", "template"]
            for name in sensors
        ]
        output = self.base / product
        assemble({
            "files": entries, "product": product, "components": ["test_fixture"],
            "configs": ["test_config"], "module_file": str(module),
            "tools": tools,
        }, output)
        return output, entries, module

    def test_relocation_and_stable_launch_stop_paths(self):
        source, _, _ = self.create()
        root = self.base / "installed elsewhere"
        install(source, root)
        work, _ = prepare(root)
        dag = (work / "share/sensors/selected.dag").read_text()
        self.assertIn(str(root / "lib/libcamera_component.so"), dag)
        self.assertIn(str(work / "share/sensors/camera.pb.txt"), dag)
        start = command(root, "cyber_launch", ["start", "share/sensors/sensors.launch"], work)
        stop = command(root, "cyber_launch", ["stop", "share/sensors/sensors.launch"], prepare(root)[0])
        self.assertEqual(start[-1], stop[-1])
        self.assertEqual((work / "bin/mainboard").resolve(), root / "libexec/mainboard")
        completed = subprocess.run(
            [str(root / "bin/mainboard"), "-d", "share/sensors/selected.dag"],
            capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(str(work / "share/sensors/selected.dag"), completed.stdout)

    def test_selected_sensor_dags_only(self):
        for sensors in [("camera",), ("lidar",), ("camera", "lidar")]:
            root, _, _ = self.create(sensors)
            work, _ = prepare(root)
            dag = (work / "share/sensors/selected.dag").read_text()
            self.assertEqual("CameraComponent" in dag, "camera" in sensors)
            self.assertEqual("HesaiComponent" in dag, "lidar" in sensors)
            shutil.rmtree(root)

    def test_conflicting_libraries_and_escaping_paths_rejected(self):
        root, entries, module = self.create()
        other = self.base / "other"
        other.write_text("different")
        spec = {
            "files": entries + [[str(other), "libexec/mainboard", "binary"]],
            "product": "sensors", "components": [], "configs": [], "module_file": str(module),
        }
        with self.assertRaisesRegex(ValueError, "conflicting"):
            assemble(spec, self.base / "conflict")
        spec["files"] = [[str(other), "../escape", "data"]]
        with self.assertRaisesRegex(ValueError, "invalid runtime destination"):
            assemble(spec, self.base / "escape")
        self.assertTrue(root.exists())

    def test_install_preserves_existing_customer_directory(self):
        source, _, _ = self.create()
        destination = self.base / "customer"
        destination.mkdir()
        (destination / "config").write_text("customer data")
        with self.assertRaisesRegex(ValueError, "nonexistent"):
            install(source, destination)
        self.assertEqual((destination / "config").read_text(), "customer data")

    def test_install_restores_bazel_tree_permissions(self):
        source, _, _ = self.create()
        for file in source.rglob("*"):
            file.chmod(0o555)
        source.chmod(0o555)
        destination = self.base / "normalized-install"
        install(source, destination)
        self.assertEqual((destination / "manifest.json").stat().st_mode & 0o777, 0o644)
        self.assertEqual((destination / "bin/mainboard").stat().st_mode & 0o777, 0o755)
        for directory in source.rglob("*"):
            if directory.is_dir():
                directory.chmod(0o755)
        source.chmod(0o755)

    def test_tampering_and_source_tree_paths_fail_explicitly(self):
        root, _, _ = self.create()
        config = root / "share/sensors/camera.pb.txt"
        config.write_text("modified")
        with self.assertRaisesRegex(ValueError, "checksum"):
            prepare(root)
        shutil.rmtree(root)
        root, entries, module = self.create()
        bad = self.base / "bad.conf"
        bad.write_text("--flagfile=/apollo/modules/global.conf\n")
        entries.append([str(bad), "share/sensors/bad.conf", "template"])
        shutil.rmtree(root)
        assemble({
            "files": entries, "product": "sensors", "components": [], "configs": [],
            "module_file": str(module),
        }, root)
        with self.assertRaisesRegex(ValueError, "unmigrated"):
            prepare(root)

    def test_doctor_is_not_a_hardware_or_performance_check(self):
        root, _, _ = self.create()
        completed = subprocess.run([str(root / "bin/doctor")], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["scope"], "file_integrity_and_template_rendering_only")
        self.assertEqual(report["sensor_test_client"], "not_integrated")
        self.assertEqual(
            {path.name for path in (root / "bin").iterdir()},
            {"mainboard", "cyber_launch", "doctor", "cyber_recorder", "cyber_monitor"},
        )
        work, _ = prepare(root)
        with self.assertRaisesRegex(ValueError, "explicit"):
            command(root, "mainboard", [], work)
        with self.assertRaises(ValueError):
            command(root, "mainboard", ["-d", "/outside/test.dag"], work)
        unsafe = self.base / "bad&path"
        shutil.copytree(root, unsafe)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            prepare(unsafe)

    def test_tool_entries_preserve_cwd_arguments_and_shared_environment(self):
        source, _, _ = self.create()
        root = self.base / "installed tools"
        install(source, root)
        environment = dict(
            os.environ, CYBER_DOMAIN_ID="194", CYBER_IP="127.0.0.1",
            LD_LIBRARY_PATH="/unrelated/host/lib", GLOG_logtostderr="0",
            WHEELOS_RUNTIME_LIBRARY_PATH="/explicit/sdk/lib",
        )
        for tool, arguments in [
            ("cyber_recorder", ["record", "-c", "/test/image", "-o", "./output.record"]),
            ("cyber_recorder", ["info", "./input.dag"]),
            ("cyber_monitor", ["-c", "/test/image"]),
        ]:
            with self.subTest(tool=tool, arguments=arguments):
                completed = subprocess.run(
                    [str(root / "bin" / tool), *arguments], cwd=self.base,
                    env=environment, capture_output=True, text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                report = json.loads(completed.stdout)
                self.assertEqual(report["cwd"], str(self.base))
                self.assertEqual(report["args"], arguments)
                env = report["env"]
                self.assertEqual(env["CYBER_DOMAIN_ID"], "194")
                self.assertEqual(env["CYBER_IP"], "127.0.0.1")
                self.assertEqual(env["GLOG_logtostderr"], "0")
                self.assertEqual(env["LD_LIBRARY_PATH"], str(root / "lib") + ":/explicit/sdk/lib")
                work, manifest = prepare(root)
                self.assertEqual(env["CYBER_PATH"], str(work))
                self.assertEqual(env["APOLLO_ROOT_DIR"], str(work))
                self.assertEqual(env["PATH"].split(os.pathsep)[:2],
                                 [str(work / "bin"), str(root / "bin")])
                self.assertEqual(set(manifest["tools"]), {"cyber_recorder", "cyber_monitor"})

    def test_mainboard_dag_option_forms_and_help(self):
        root, _, _ = self.create()
        work, _ = prepare(root)
        relative = "share/sensors/selected.dag"
        rendered = str(work / relative)
        for option in ["-d", "--dag_conf"]:
            self.assertEqual(command(root, "mainboard", [option, relative], work)[1:],
                             [option, rendered])
            with self.assertRaisesRegex(ValueError, "requires"):
                command(root, "mainboard", [option], work)
        for prefix in ["--dag_conf=", "-d"]:
            self.assertEqual(command(root, "mainboard", [prefix + relative], work)[1:],
                             [prefix + rendered])
        self.assertEqual(
            command(root, "mainboard", ["-d", relative, "--dag_conf=" + relative], work)[1:],
            ["-d", rendered, "--dag_conf=" + rendered],
        )
        for tool in ["mainboard", "cyber_launch"]:
            self.assertEqual(command(root, tool, ["--help"], work)[-1], "--help")
        with self.assertRaises(ValueError):
            command(root, "mainboard", ["--dag_conf=/outside/test.dag"], work)

    def test_ambient_configuration_override_is_explicitly_rejected(self):
        root, _, _ = self.create()
        with patch.dict(os.environ, {"WHEELOS_CONFIG_ROOT": str(self.base)}):
            completed = subprocess.run(
                [str(root / "bin/doctor")], capture_output=True, text=True,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("WHEELOS_CONFIG_ROOT", completed.stderr)

    def test_unselected_tools_and_unknown_tools_fail(self):
        root, _, _ = self.create()
        work, _ = prepare(root)
        (root / "libexec/cyber_recorder").unlink()
        with self.assertRaisesRegex(ValueError, "not packaged"):
            command(root, "cyber_recorder", ["--help"], work)
        with self.assertRaisesRegex(ValueError, "unknown runtime tool"):
            command(root, "other", [], work)
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/ambient/lib"}):
            env = runtime_environment(root, work)
        self.assertNotIn("/ambient/lib", env["LD_LIBRARY_PATH"])

    def test_cyber_scheduler_topic_names_are_not_filesystem_paths(self):
        root, entries, module = self.create()
        config = self.base / "scheduler.conf"
        config.write_text('tasks { name: "camera_/apollo/sensor/camera" }\n')
        entries.append([str(config), "conf/scheduler.conf", "data"])
        shutil.rmtree(root)
        assemble({
            "files": entries, "product": "sensors", "components": [], "configs": [],
            "module_file": str(module),
        }, root)
        work, _ = prepare(root)
        self.assertIn("camera_/apollo/sensor/camera", (work / "conf/scheduler.conf").read_text())


if __name__ == "__main__":
    unittest.main()
