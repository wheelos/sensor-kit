"""Runtime assembly is owned by core, not duplicated in product repositories."""

load(
    "@wheelos_core//runtime:runtime.bzl",
    _required_input = "required_runtime_input",
    _runtime_layout = "runtime_layout",
    _runtime_module = "runtime_module",
    _runtime_package = "runtime_package",
    _runtime_run = "runtime_run",
)

required_input = _required_input
runtime_layout = _runtime_layout
runtime_module = _runtime_module
runtime_package = _runtime_package
runtime_run = _runtime_run
