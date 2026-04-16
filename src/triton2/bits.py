"""
Bitfield definitions for Triton2 holding registers (16-bit words, bits 0–15).

Status bits: ``M_REG_STATUS`` (address 0), read-only.
Configuration bits: ``M_REG_CONFIG`` (address 6), read/write in config mode per device rules.

Names follow ``references/registers-definitions.md``; indices match the technical guide bitfields.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .registers import Register, RegisterMap


@dataclass(frozen=True)
class BitDef:
    """Single bit within a 16-bit Modbus register."""

    index: int
    label: str


class StatusBit(Enum):
    """Bits of ``M_REG_STATUS`` (read-only)."""

    BIT_SYSTEM_ERROR = BitDef(0, "bit_system_error")
    BIT_SENSOR_ERROR = BitDef(1, "bit_sensor_error")
    BIT_SENSOR_RUNNING = BitDef(2, "bit_sensor_running")
    BIT_CALIBRATING = BitDef(3, "bit_calibrating")
    BIT_CH1 = BitDef(4, "bit_ch1")
    BIT_CH2 = BitDef(5, "bit_ch2")
    BIT_CH3 = BitDef(6, "bit_ch3")
    BIT_CH4 = BitDef(7, "bit_ch4")
    BIT_CONFIG_MODE = BitDef(8, "bit_config_mode")
    BIT_DUMMY = BitDef(9, "bit_dummy")

    @property
    def index(self) -> int:
        return self.value.index

    @property
    def label(self) -> str:
        return self.value.label

    @property
    def mask(self) -> int:
        return 1 << self.value.index

    @property
    def register(self) -> Register:
        return RegisterMap.M_REG_STATUS


class ConfigBit(Enum):
    """Bits of ``M_REG_CONFIG`` (read/write; CONF registers require config mode to persist)."""

    BIT_RESET = BitDef(0, "bit_reset")
    BIT_ENABLE_CH1 = BitDef(1, "bit_enable_ch1")
    BIT_ENABLE_CH2 = BitDef(2, "bit_enable_ch2")
    BIT_ENABLE_CH3 = BitDef(3, "bit_enable_ch3")
    BIT_ENABLE_CH4 = BitDef(4, "bit_enable_ch4")
    BIT_ENABLE_ACTIVE_GUARD = BitDef(5, "bit_enable_active_guard")
    BIT_DISABLE_DIGITAL = BitDef(6, "bit_disable_digital")
    BIT_DISABLE_ANALOG = BitDef(7, "bit_disable_analog")
    BIT_EMPTY = BitDef(8, "bit_empty")

    @property
    def index(self) -> int:
        return self.value.index

    @property
    def label(self) -> str:
        return self.value.label

    @property
    def mask(self) -> int:
        return 1 << self.value.index

    @property
    def register(self) -> Register:
        return RegisterMap.M_REG_CONFIG
