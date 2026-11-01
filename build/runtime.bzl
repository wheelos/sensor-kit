"""Assemble explicitly selected external components into standalone products."""

load("@rules_pkg//pkg:providers.bzl", "PackageFilegroupInfo", "PackageFilesInfo")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:defs.bzl", "py_binary")

def _required_impl(ctx):
    fail(ctx.attr.message)

required_input = rule(
    implementation = _required_impl,
    attrs = {"message": attr.string(mandatory = True)},
)

def _runtime_impl(ctx):
    entries = []
    inputs = []
    if len(ctx.files.lockfile) > 1:
        fail("dependency_lock must provide at most one lockfile")
    lockfile = ctx.files.lockfile[0] if ctx.files.lockfile else None
    for file in ctx.files.components:
        entries.append([file.path, "lib/" + file.basename, "binary"])
        inputs.append(file)
    for target in ctx.attr.components + [ctx.attr.mainboard] + ctx.attr.tools.keys():
        info = target[DefaultInfo]
        for file in depset(transitive = [
            info.default_runfiles.files,
            info.data_runfiles.files,
        ]).to_list():
            if file.basename.endswith(".so") or ".so." in file.basename:
                entries.append([file.path, "lib/" + file.basename, "binary"])
                inputs.append(file)
            elif "/sdk.json" in file.short_path or "/licenses/" in file.short_path:
                entries.append([file.path, "share/dependencies/ffmpeg/" + file.basename, "data"])
                inputs.append(file)
    for target, name in ctx.attr.tools.items():
        if name not in ["cyber_recorder", "cyber_monitor"]:
            fail("unsupported runtime tool: " + name)
        executable = target[DefaultInfo].files_to_run.executable
        if not executable:
            fail("runtime tool must be executable: " + str(target.label))
        entries.append([executable.path, "libexec/" + name, "binary"])
        inputs.append(executable)
    for target, destination in ctx.attr.configs.items():
        files = target[DefaultInfo].files.to_list()
        if len(files) != 1:
            fail("config %s must provide exactly one file" % target.label)
        entries.append([files[0].path, destination, "template"])
        inputs.extend(files)
    for file in ctx.files.templates:
        entries.append([file.path, "share/" + ctx.attr.product + "/" + file.basename, "template"])
        inputs.append(file)
    for file in ctx.files.cyber_conf:
        path = file.short_path
        if path.startswith("../"):
            path = path.split("/", 2)[2]
        if not path.startswith("cyber/"):
            fail("unexpected Cyber configuration path: " + path)
        entries.append([file.path, path.removeprefix("cyber/"), "data"])
        inputs.append(file)
    for file, destination in [
        (ctx.executable.mainboard, "libexec/mainboard"),
        (ctx.file.cyber_launch, "libexec/cyber_launch.py"),
        (ctx.file.entry, "libexec/entry.py"),
    ]:
        entries.append([file.path, destination, "binary"])
        inputs.append(file)
    output = ctx.actions.declare_directory(ctx.label.name)
    spec = ctx.actions.declare_file(ctx.label.name + ".json")
    ctx.actions.write(spec, json.encode({
        "product": ctx.attr.product,
        "files": entries,
        "components": [str(t.label) for t in ctx.attr.components],
        "configs": [str(t.label) for t in ctx.attr.configs],
        "tools": {name: str(target.label) for target, name in ctx.attr.tools.items()},
        "module_file": ctx.file.module_file.path,
        "lockfile": lockfile.path if lockfile else None,
    }))
    ctx.actions.run(
        executable = ctx.executable._assembler,
        arguments = [spec.path, output.path],
        inputs = depset(inputs + [spec, ctx.file.module_file] + ctx.files.lockfile),
        outputs = [output],
        mnemonic = "ProductRuntime",
    )
    return [
        DefaultInfo(files = depset([output])),
    ]

product_runtime = rule(
    implementation = _runtime_impl,
    attrs = {
        "product": attr.string(mandatory = True, values = ["sensors"]),
        "components": attr.label_list(allow_files = True),
        "configs": attr.label_keyed_string_dict(allow_files = True),
        "templates": attr.label_list(allow_files = True),
        "tools": attr.label_keyed_string_dict(providers = [DefaultInfo]),
        "mainboard": attr.label(default = "@wheelos_core//cyber/mainboard:mainboard", executable = True, cfg = "target"),
        "cyber_launch": attr.label(default = "@wheelos_core//cyber/tools/cyber_launch:cyber_launch.py", allow_single_file = True),
        "cyber_conf": attr.label(default = "@wheelos_core//cyber:cyber_conf", allow_files = True),
        "entry": attr.label(default = "//runtime:entry.py", allow_single_file = True),
        "module_file": attr.label(default = "//:MODULE.bazel", allow_single_file = True),
        "lockfile": attr.label(default = "//:dependency_lock", allow_files = True),
        "_assembler": attr.label(default = "//runtime:assemble", executable = True, cfg = "exec"),
    },
)

def _package_impl(ctx):
    binaries = ["bin", "lib", "libexec"]
    data = ["conf", "share"]
    outputs = {
        name: ctx.actions.declare_directory(ctx.label.name + "/" + name)
        for name in binaries + data
    }
    manifest = ctx.actions.declare_file(ctx.label.name + "/manifest.json")
    ctx.actions.run(
        executable = ctx.executable._assembler,
        arguments = ["--package", ctx.file.runtime.path, manifest.dirname],
        inputs = [ctx.file.runtime],
        outputs = outputs.values() + [manifest],
        mnemonic = "ProductPackage",
    )
    return [
        DefaultInfo(files = depset(outputs.values() + [manifest])),
        PackageFilegroupInfo(
            pkg_files = [
                (PackageFilesInfo(
                    dest_src_map = {name: outputs[name] for name in names},
                    attributes = {"mode": mode},
                ), ctx.label)
                for names, mode in [(binaries, "0755"), (data, "0644")]
            ] + [
                (PackageFilesInfo(
                    dest_src_map = {"manifest.json": manifest},
                    attributes = {"mode": "0644"},
                ), ctx.label),
            ],
            pkg_dirs = [],
            pkg_symlinks = [],
        ),
    ]

package_files = rule(
    implementation = _package_impl,
    attrs = {
        "runtime": attr.label(mandatory = True, allow_single_file = True),
        "_assembler": attr.label(default = "//runtime:assemble", executable = True, cfg = "exec"),
    },
)

def product_delivery(runtime):
    package_files(name = "package_files", runtime = runtime)
    pkg_tar(
        name = "package",
        srcs = [":package_files"],
        extension = "tar.gz",
        package_file_name = "runtime.tar.gz",
    )
    py_binary(
        name = "install",
        srcs = ["//runtime:install.py"],
        main = "//runtime:install.py",
        data = [runtime],
        args = ["$(rlocationpath " + runtime + ")"],
        deps = ["@rules_python//python/runfiles"],
    )
