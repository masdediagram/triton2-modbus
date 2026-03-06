"""Connect to a Triton2 sensor and read status and channel data."""

import sys
from pathlib import Path

if (Path(__file__).resolve().parent.parent / "src").is_dir():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triton2 import Triton2Client

PORT = "COM3"  # or "/dev/ttyUSB0" on Linux

with Triton2Client(PORT, slave=1) as t2:
    print(f"Firmware: v{t2.read_firmware_version():.2f}")
    print(f"Status:   0x{t2.read_status():03X}")
    print(f"Running:  {t2.is_sensor_running()}")

    cal = t2.read_all_calibrated()
    print("Calibrated:", cal)

    raw = t2.read_all_raw()
    print("Raw (pF):", raw)
