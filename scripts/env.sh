#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Source this file: source scripts/env.sh" >&2
  exit 2
fi

_sensor_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || return 1
_core_bin="$_sensor_root/bazel-bin/external/wheelos_core+/cyber"
_mainboard_dir="$_core_bin/mainboard"
_launch_dir="$_core_bin/tools/cyber_launch"
_recorder_dir="$_core_bin/tools/cyber_recorder"
_monitor_dir="$_core_bin/tools/cyber_monitor"
_cyber_conf_dir="$_mainboard_dir/mainboard.runfiles/wheelos_core+/cyber/conf"

if [[ ! -f "$_cyber_conf_dir/cyber.pb.conf" ]]; then
  echo "wheelos_core Bazel runfiles are not built; run the documented bazel build first." >&2
  return 1
fi
for _tool in \
  "$_mainboard_dir/mainboard" \
  "$_launch_dir/cyber_launch" \
  "$_recorder_dir/cyber_recorder" \
  "$_monitor_dir/cyber_monitor"; do
  if [[ ! -x "$_tool" ]]; then
    echo "wheelos_core tool is missing: $_tool" >&2
    return 1
  fi
done

ln -sfn "$_cyber_conf_dir" "$_sensor_root/conf"

export APOLLO_ROOT_DIR="$_sensor_root"
export CYBER_PATH="$_sensor_root"
export CYBER_IP="${CYBER_IP:-127.0.0.1}"
export CYBER_DOMAIN_ID="${CYBER_DOMAIN_ID:-80}"

if [[ -z "${TERMINFO:-}" ]]; then
  for _terminfo_dir in \
    /lib/terminfo \
    /usr/lib/terminfo \
    /usr/share/terminfo \
    /etc/terminfo; do
    if [[ -d "$_terminfo_dir" ]]; then
      export TERMINFO="$_terminfo_dir"
      break
    fi
  done
fi

for _tool_dir in "$_mainboard_dir" "$_launch_dir" "$_recorder_dir" "$_monitor_dir"; do
  case ":$PATH:" in
    *":$_tool_dir:"*) ;;
    *) PATH="$_tool_dir:$PATH" ;;
  esac
done
export PATH

echo "wheelos_core local runtime environment configured."
echo "APOLLO_ROOT_DIR=$APOLLO_ROOT_DIR"
echo "CYBER_PATH=$CYBER_PATH"
echo "CYBER_IP=$CYBER_IP CYBER_DOMAIN_ID=$CYBER_DOMAIN_ID"

unset _sensor_root _core_bin _mainboard_dir _launch_dir _recorder_dir _monitor_dir
unset _cyber_conf_dir _tool _tool_dir _terminfo_dir
