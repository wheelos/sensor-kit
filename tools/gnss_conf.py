#!/usr/bin/env python3

# Copyright 2026 The WheelOS Team. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Created Date: 2026-02-09
# Author: daohu527


import re
import sys
import time

import serial

SERIAL_PORT = "/dev/ttyUSB4"  # Replace with your device name /dev/ttyUSB0
BAUDRATE = 460800
READ_TIMEOUT = 0.1  # seconds

# Command list (modify as needed)
COMMANDS = [
    "unlogall",
    "com COM2 460800",
    "LOG COM2 BESTGNSSPOSB ONTIME 0.2",
    "LOG COM2 BESTGNSSVELB ONTIME 0.2",
    "LOG COM2 BESTXYZB ONTIME 0.2",
    "LOG COM2 RANGEHB ONTIME 1",
    "LOG COM2 RANGECMPB ONTIME 1",
    "LOG COM2 GPSEPHEMB ONCHANGED 60",
    "LOG COM2 BDSEPHEMERISB ONCHANGED 60",
    "LOG COM2 GLOEPHEMERISB ONCHANGED 60",
    "LOG COM2 GALEPHEMERISB ONCHANGED 60",
    "LOG COM2 HEADINGB ONTIME 0.2",
    "LOG COM2 RAWIMUB ONTIME 0.01",
    "LOG COM2 CORRIMUDATAB ONTIME 0.01",
    "LOG COM2 INSPVAB ONTIME 0.01",
    "LOG COM2 INSPVAXB ONTIME 0.1",
    "log COM2 gpgga ontime 1",

    # "insangle 0 0 0 5 5 5",
    # "headingoffset 0 0 19.13 5.00 5.00 5.00",
    # "ant2bodyoffset -0.855 0.14 -0.42 1.0 1.0 1.0",
    # "ins2antoffset 0.56 -3.08 0.28 1.0 1.0 1.0",
    # "ant2outposoffset 2 -0.855 2.465 -0.28",
    # "wheeltread 1.82 4.3",
    # "bodytype 2 0 0",
    "saveconfig",
]


def send_command_and_wait_ack(ser, cmd, timeout=2.0):
    """Send a command and wait for its successful receiver response."""
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode())
    ser.flush()
    print(f">>> Sent: {cmd}")

    deadline = time.monotonic() + timeout
    expected = " ".join(cmd.split()).casefold()
    while time.monotonic() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        text = raw.decode(errors="replace").strip()
        for response in re.finditer(
            r"command,\s*\[(.*?)\],\s*([a-z]+)\b", text, re.IGNORECASE
        ):
            actual = " ".join(response.group(1).split()).casefold()
            if actual != expected:
                continue
            if response.group(2).casefold() != "ok":
                raise RuntimeError(f"Device rejected `{cmd}`: {response.group(0)}")
            return response.group(0)
    raise TimeoutError(f"No successful acknowledgment for `{cmd}` within {timeout}s")


def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=READ_TIMEOUT)
    except serial.SerialException as e:
        print(f"Failed to open serial port: {e}")
        return 1

    try:
        with ser:
            for cmd in COMMANDS:
                try:
                    response = send_command_and_wait_ack(ser, cmd)
                except (serial.SerialException, TimeoutError, RuntimeError) as e:
                    print(f"[ERROR] {e}")
                    return 1
                else:
                    print(f"[ACK] {response}")
                time.sleep(0.05)
    except serial.SerialException as e:
        print(f"Serial communication failed: {e}")
        return 1

    print("Serial port closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
