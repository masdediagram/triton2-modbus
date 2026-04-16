"""
Triton2 Modbus library: client and high-speed streaming for Triton2 capacitive level sensor.
"""

from .client import Triton2Client
from .scanner import DeviceScanner
from .stream import ALL_CHANNELS, Channel, ChannelBuffer, ChannelStreamReader
from . import bits
from . import constants
from . import registers
from .exceptions import (
    CalibrationTimeoutError,
    ConfigRequiredError,
    ModbusConnectionError,
    Triton2Error,
)

__all__ = [
    "Triton2Client",
    "DeviceScanner",
    "ChannelStreamReader",
    "ChannelBuffer",
    "Channel",
    "ALL_CHANNELS",
    "bits",
    "constants",
    "registers",
    "Triton2Error",
    "ConfigRequiredError",
    "CalibrationTimeoutError",
    "ModbusConnectionError",
]
