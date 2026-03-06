"""
Modbus register map for Triton2 sensor. All addresses are 0-based.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RegisterValueType(str, Enum):
    BITFIELD = "bitfield"  # 16-bit bitfield (status/config)
    UINT16 = "uint16"
    UINT32 = "uint32"
    FLOAT32 = "float32"
    WORDS = "words"  # opaque words (e.g. CHIP_ID)


@dataclass(frozen=True)
class Register:
    address: int
    words: int
    value_type: RegisterValueType


class RegisterMap:
    # --- System / config ---
    M_REG_STATUS = Register(0, 1, RegisterValueType.BITFIELD)
    M_REG_CHIP_ID = Register(1, 4, RegisterValueType.WORDS)
    M_REG_FW_VERSION = Register(5, 1, RegisterValueType.UINT16)  # scaled by /100 in client
    M_REG_CONFIG = Register(6, 1, RegisterValueType.BITFIELD)
    M_REG_CONFIG2 = Register(7, 1, RegisterValueType.UINT16)
    M_REG_BAUD_RATE = Register(8, 1, RegisterValueType.UINT16)
    M_REG_SLAVEID = Register(9, 1, RegisterValueType.UINT16)
    M_REG_COMMAND = Register(10, 1, RegisterValueType.UINT16)
    M_REG_CALIBRATION_TIME = Register(11, 1, RegisterValueType.UINT16)

    # --- Measurements ---
    M_REG_TIMESTAMP = Register(16, 2, RegisterValueType.UINT32)
    M_REG_CH1_RAW = Register(18, 2, RegisterValueType.FLOAT32)
    M_REG_CH2_RAW = Register(20, 2, RegisterValueType.FLOAT32)
    M_REG_CH3_RAW = Register(22, 2, RegisterValueType.FLOAT32)
    M_REG_CH4_RAW = Register(24, 2, RegisterValueType.FLOAT32)
    M_REG_CH1_CAL = Register(26, 2, RegisterValueType.FLOAT32)
    M_REG_CH2_CAL = Register(28, 2, RegisterValueType.FLOAT32)
    M_REG_CH3_CAL = Register(30, 2, RegisterValueType.FLOAT32)
    M_REG_CH4_CAL = Register(32, 2, RegisterValueType.FLOAT32)

    # --- Calibration / tuning ---
    M_REG_CAL_CH1_GAIN = Register(34, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH1_OFFSET = Register(36, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH2_GAIN = Register(38, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH2_OFFSET = Register(40, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH3_GAIN = Register(42, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH3_OFFSET = Register(44, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH4_GAIN = Register(46, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_CH4_OFFSET = Register(48, 2, RegisterValueType.FLOAT32)
    M_REG_KALMAN_Q = Register(50, 2, RegisterValueType.FLOAT32)
    M_REG_KALMAN_R = Register(52, 2, RegisterValueType.FLOAT32)
    M_REG_CAL_REFERENCE = Register(56, 2, RegisterValueType.FLOAT32)


class ChannelKind(str, Enum):
    CAL = "cal"
    RAW = "raw"


@dataclass(frozen=True)
class ChannelDef:
    index: int
    kind: ChannelKind
    register: Register
    label: str


class Channel(Enum):
    """Select which channel data to read. CAL = calibrated, RAW = capacitance (pF)."""

    CH1_CAL = ChannelDef(1, ChannelKind.CAL, RegisterMap.M_REG_CH1_CAL, "ch1_cal")
    CH2_CAL = ChannelDef(2, ChannelKind.CAL, RegisterMap.M_REG_CH2_CAL, "ch2_cal")
    CH3_CAL = ChannelDef(3, ChannelKind.CAL, RegisterMap.M_REG_CH3_CAL, "ch3_cal")
    CH4_CAL = ChannelDef(4, ChannelKind.CAL, RegisterMap.M_REG_CH4_CAL, "ch4_cal")
    CH1_RAW = ChannelDef(1, ChannelKind.RAW, RegisterMap.M_REG_CH1_RAW, "ch1_raw")
    CH2_RAW = ChannelDef(2, ChannelKind.RAW, RegisterMap.M_REG_CH2_RAW, "ch2_raw")
    CH3_RAW = ChannelDef(3, ChannelKind.RAW, RegisterMap.M_REG_CH3_RAW, "ch3_raw")
    CH4_RAW = ChannelDef(4, ChannelKind.RAW, RegisterMap.M_REG_CH4_RAW, "ch4_raw")

    @property
    def index(self) -> int:
        return self.value.index

    @property
    def kind(self) -> ChannelKind:
        return self.value.kind

    @property
    def register(self) -> Register:
        return self.value.register

    @property
    def label(self) -> str:
        return self.value.label


# Default: all channels (calibrated then raw, Ch1–Ch4)
ALL_CHANNELS: list[Channel] = [
    Channel.CH1_CAL,
    Channel.CH2_CAL,
    Channel.CH3_CAL,
    Channel.CH4_CAL,
    Channel.CH1_RAW,
    Channel.CH2_RAW,
    Channel.CH3_RAW,
    Channel.CH4_RAW,
]

# Batch read ranges: (start_address, word_count) for single Modbus request
ADDR_ALL_RAW = 18
COUNT_ALL_RAW = 8  # CH1–CH4 raw (4 floats)
ADDR_ALL_CAL = 26
COUNT_ALL_CAL = 8  # CH1–CH4 calibrated (4 floats)
ADDR_ALL_MEASUREMENTS = 16
COUNT_ALL_MEASUREMENTS = 18  # timestamp(2) + raw(8) + cal(8)
# Timestamp + raw in one contiguous block (one request, 10 words) when only raw channels needed
COUNT_TIMESTAMP_AND_RAW = 10  # addr 16


RAW_CHANNEL_REGISTERS: tuple[Register, ...] = (
    RegisterMap.M_REG_CH1_RAW,
    RegisterMap.M_REG_CH2_RAW,
    RegisterMap.M_REG_CH3_RAW,
    RegisterMap.M_REG_CH4_RAW,
)

CAL_CHANNEL_REGISTERS: tuple[Register, ...] = (
    RegisterMap.M_REG_CH1_CAL,
    RegisterMap.M_REG_CH2_CAL,
    RegisterMap.M_REG_CH3_CAL,
    RegisterMap.M_REG_CH4_CAL,
)
