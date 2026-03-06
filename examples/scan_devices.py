"""Scan the Modbus RTU bus for responding Triton2 (or other) devices."""

import sys
from pathlib import Path

if (Path(__file__).resolve().parent.parent / "src").is_dir():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triton2 import DeviceScanner

PORT = "COM3"  # or "/dev/ttyUSB0" on Linux

# Scan default range 1–247
with DeviceScanner(PORT) as scanner:
    found = scanner.scan()
    print(f"Devices found: {found}")

# Or scan a limited range, e.g. 1–10
# with DeviceScanner(PORT) as scanner:
#     found = scanner.scan(slave_ids=range(1, 11))
#     print(f"Devices found: {found}")
