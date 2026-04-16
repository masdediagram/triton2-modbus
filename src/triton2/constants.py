"""
Triton2 Modbus constants: commands, status/config bits, baud rates.

Bit masks are aliases of :class:`bits.StatusBit` / :class:`bits.ConfigBit` (single source of truth).
"""

from .bits import ConfigBit, StatusBit

# --- Commands (M_REG_COMMAND) ---
CMD_NONE = 0
CMD_RESET = 100
CMD_RESET_CALIBRATION = 101
CMD_FACTORY_RESET = 102
CMD_CONFIG_MODE = 201
CMD_APPLY_CONFIG = 202
CMD_EXIT_CONFIG_MODE = 203
CMD_CALIBRATE_CH1_PT0 = 410
CMD_CALIBRATE_CH1_PT1 = 411
CMD_CALIBRATE_CH2_PT0 = 420
CMD_CALIBRATE_CH2_PT1 = 421
CMD_CALIBRATE_CH3_PT0 = 430
CMD_CALIBRATE_CH3_PT1 = 431
CMD_CALIBRATE_CH4_PT0 = 440
CMD_CALIBRATE_CH4_PT1 = 441

# --- Status bits (M_REG_STATUS, register 0) ---
BIT_SYSTEM_ERROR = StatusBit.BIT_SYSTEM_ERROR.mask
BIT_SENSOR_ERROR = StatusBit.BIT_SENSOR_ERROR.mask
BIT_SENSOR_RUNNING = StatusBit.BIT_SENSOR_RUNNING.mask
BIT_CALIBRATING = StatusBit.BIT_CALIBRATING.mask
BIT_CH1 = StatusBit.BIT_CH1.mask
BIT_CH2 = StatusBit.BIT_CH2.mask
BIT_CH3 = StatusBit.BIT_CH3.mask
BIT_CH4 = StatusBit.BIT_CH4.mask
BIT_CONFIG_MODE = StatusBit.BIT_CONFIG_MODE.mask
BIT_DUMMY = StatusBit.BIT_DUMMY.mask

# --- Config bits (M_REG_CONFIG, register 6) ---
BIT_RESET = ConfigBit.BIT_RESET.mask
BIT_ENABLE_CH1 = ConfigBit.BIT_ENABLE_CH1.mask
BIT_ENABLE_CH2 = ConfigBit.BIT_ENABLE_CH2.mask
BIT_ENABLE_CH3 = ConfigBit.BIT_ENABLE_CH3.mask
BIT_ENABLE_CH4 = ConfigBit.BIT_ENABLE_CH4.mask
BIT_ENABLE_ACTIVE_GUARD = ConfigBit.BIT_ENABLE_ACTIVE_GUARD.mask
BIT_DISABLE_DIGITAL = ConfigBit.BIT_DISABLE_DIGITAL.mask
BIT_DISABLE_ANALOG = ConfigBit.BIT_DISABLE_ANALOG.mask
BIT_EMPTY = ConfigBit.BIT_EMPTY.mask

# --- Baud rate index -> bps (M_REG_BAUD_RATE) ---
BAUD_RATES: dict[int, int] = {
    0: 9600,
    1: 19200,
    2: 38400,
    3: 57600,
    4: 115200,
    5: 230400,
    6: 460800,
    7: 921600,
}

BAUD_RATE_TO_INDEX: dict[int, int] = {bps: idx for idx, bps in BAUD_RATES.items()}

# Calibration command lookup: (channel 1–4, point 0|1) -> command value
CALIBRATION_COMMANDS: dict[tuple[int, int], int] = {
    (1, 0): CMD_CALIBRATE_CH1_PT0,
    (1, 1): CMD_CALIBRATE_CH1_PT1,
    (2, 0): CMD_CALIBRATE_CH2_PT0,
    (2, 1): CMD_CALIBRATE_CH2_PT1,
    (3, 0): CMD_CALIBRATE_CH3_PT0,
    (3, 1): CMD_CALIBRATE_CH3_PT1,
    (4, 0): CMD_CALIBRATE_CH4_PT0,
    (4, 1): CMD_CALIBRATE_CH4_PT1,
}
