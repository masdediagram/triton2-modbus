"""
Triton2 Modbus RTU client with batch reads and speed options.
"""

from __future__ import annotations

from typing import Any

from pymodbus.client import ModbusSerialClient

from .codec import decode_float_cdab, decode_uint32_cdab, decode_floats_cdab, encode_float_cdab
from .constants import (
    BAUD_RATES,
    BAUD_RATE_TO_INDEX,
    BIT_CALIBRATING,
    BIT_CH1,
    BIT_CH2,
    BIT_CH3,
    BIT_CH4,
    BIT_CONFIG_MODE,
    BIT_SENSOR_RUNNING,
    CALIBRATION_COMMANDS,
    CMD_APPLY_CONFIG,
    CMD_CONFIG_MODE,
    CMD_EXIT_CONFIG_MODE,
    CMD_FACTORY_RESET,
    CMD_RESET,
)
from .exceptions import CalibrationTimeoutError, ModbusConnectionError, Triton2Error
from .registers import (
    ADDR_ALL_CAL,
    ADDR_ALL_MEASUREMENTS,
    ADDR_ALL_RAW,
    COUNT_ALL_CAL,
    COUNT_ALL_MEASUREMENTS,
    COUNT_ALL_RAW,
    COUNT_TIMESTAMP_AND_RAW,
    CAL_CHANNEL_REGISTERS,
    RAW_CHANNEL_REGISTERS,
    Register,
    RegisterMap,
)


class ConfigModeContext:
    """Context manager for config mode: enter on __enter__, exit (no save) on __exit__."""

    def __init__(self, client: "Triton2Client") -> None:
        self._client = client

    def __enter__(self) -> "Triton2Client":
        self._client.enter_config_mode()
        return self._client

    def __exit__(self, *args: Any) -> None:
        self._client.exit_config_mode()


class Triton2Client:
    """
    Modbus RTU client for Triton2 capacitive level sensor.
    Optimized for read speed with batch reads; optional serial buffer clearing.
    """

    def __init__(
        self,
        port: str,
        slave: int = 1,
        baudrate: int = 115200,
        clear_serial_before_read: bool = False,
        **serial_kwargs: Any,
    ) -> None:
        self.port = port
        self.slave = slave
        self.baudrate = baudrate
        self.clear_serial_before_read = clear_serial_before_read
        self._client: ModbusSerialClient | None = None
        self._serial_kwargs = serial_kwargs

    def connect(self) -> None:
        if self._client is not None:
            return
        self._client = ModbusSerialClient(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            **self._serial_kwargs,
        )
        if not self._client.connect():
            raise ModbusConnectionError(f"Failed to connect to {self.port}")

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Triton2Client:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _ensure_connected(self) -> ModbusSerialClient:
        if self._client is None:
            raise ModbusConnectionError("Not connected; call connect() first")
        return self._client

    def _clear_serial_rx(self) -> None:
        if not self.clear_serial_before_read:
            return
        client = self._client
        if client is None:
            return
        try:
            conn = getattr(client, "connection", None) or getattr(client, "_connection", None)
            if conn is not None and hasattr(conn, "reset_input_buffer"):
                conn.reset_input_buffer()
        except Exception:
            pass

    def _read_registers(self, address: int, count: int) -> list[int]:
        client = self._ensure_connected()
        self._clear_serial_rx()
        result = client.read_holding_registers(address, count, slave=self.slave)
        if result.isError():
            raise ModbusConnectionError(str(result))
        regs = result.registers
        if regs is None or len(regs) < count:
            raise Triton2Error(f"Expected {count} registers, got {len(regs) if regs else 0}")
        return list(regs[:count])

    def _read_reg(self, reg: Register) -> list[int]:
        return self._read_registers(reg.address, reg.words)

    def _write_register(self, address: int, value: int) -> None:
        client = self._ensure_connected()
        result = client.write_register(address, value, slave=self.slave)
        if result.isError():
            raise ModbusConnectionError(str(result))

    def _write_reg(self, reg: Register, value: int) -> None:
        self._write_register(reg.address, value)

    def _write_registers(self, address: int, values: list[int]) -> None:
        client = self._ensure_connected()
        result = client.write_registers(address, values, slave=self.slave)
        if result.isError():
            raise ModbusConnectionError(str(result))

    def _write_regs(self, reg: Register, values: list[int]) -> None:
        self._write_registers(reg.address, values)

    # --- Read methods ---

    def read_status(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_STATUS)
        return regs[0] & 0xFFFF

    def read_firmware_version(self) -> float:
        regs = self._read_reg(RegisterMap.M_REG_FW_VERSION)
        return (regs[0] & 0xFFFF) / 100.0

    def read_timestamp_ms(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_TIMESTAMP)
        return decode_uint32_cdab(regs)

    def read_raw(self, channel: int) -> float:
        if channel not in (1, 2, 3, 4):
            raise ValueError("channel must be 1, 2, 3, or 4")
        reg = RAW_CHANNEL_REGISTERS[channel - 1]
        regs = self._read_reg(reg)
        return decode_float_cdab(regs)

    def read_calibrated(self, channel: int) -> float:
        if channel not in (1, 2, 3, 4):
            raise ValueError("channel must be 1, 2, 3, or 4")
        reg = CAL_CHANNEL_REGISTERS[channel - 1]
        regs = self._read_reg(reg)
        return decode_float_cdab(regs)

    def read_all_raw(self) -> dict[int, float]:
        regs = self._read_registers(ADDR_ALL_RAW, COUNT_ALL_RAW)
        floats = decode_floats_cdab(regs, 4)
        return {i: floats[i - 1] for i in range(1, 5)}

    def read_all_calibrated(self) -> dict[int, float]:
        regs = self._read_registers(ADDR_ALL_CAL, COUNT_ALL_CAL)
        floats = decode_floats_cdab(regs, 4)
        return {i: floats[i - 1] for i in range(1, 5)}

    def read_all_measurements(self) -> dict[str, Any]:
        regs = self._read_registers(ADDR_ALL_MEASUREMENTS, COUNT_ALL_MEASUREMENTS)
        timestamp_ms = decode_uint32_cdab(regs[0:2])
        raw_floats = decode_floats_cdab(regs[2:10], 4)
        cal_floats = decode_floats_cdab(regs[10:18], 4)
        return {
            "timestamp_ms": timestamp_ms,
            "raw": {i: raw_floats[i - 1] for i in range(1, 5)},
            "calibrated": {i: cal_floats[i - 1] for i in range(1, 5)},
        }

    def read_timestamp_and_raw(self) -> dict[str, Any]:
        """One Modbus request for timestamp + all raw channels (10 words). Use when only raw channels needed."""
        regs = self._read_registers(ADDR_ALL_MEASUREMENTS, COUNT_TIMESTAMP_AND_RAW)
        timestamp_ms = decode_uint32_cdab(regs[0:2])
        raw_floats = decode_floats_cdab(regs[2:10], 4)
        return {"timestamp_ms": timestamp_ms, "raw": {i: raw_floats[i - 1] for i in range(1, 5)}}

    def is_calibrating(self) -> bool:
        return (self.read_status() & BIT_CALIBRATING) != 0

    def is_config_mode(self) -> bool:
        return (self.read_status() & BIT_CONFIG_MODE) != 0

    def is_sensor_running(self) -> bool:
        return (self.read_status() & BIT_SENSOR_RUNNING) != 0

    def channel_active(self, channel: int) -> bool:
        if channel not in (1, 2, 3, 4):
            raise ValueError("channel must be 1, 2, 3, or 4")
        bits = (BIT_CH1, BIT_CH2, BIT_CH3, BIT_CH4)
        return (self.read_status() & bits[channel - 1]) != 0

    # --- Config mode ---

    def enter_config_mode(self) -> None:
        self._write_reg(RegisterMap.M_REG_COMMAND, CMD_CONFIG_MODE)

    def apply_config(self) -> None:
        self._write_reg(RegisterMap.M_REG_COMMAND, CMD_APPLY_CONFIG)

    def exit_config_mode(self) -> None:
        self._write_reg(RegisterMap.M_REG_COMMAND, CMD_EXIT_CONFIG_MODE)

    def config_mode(self) -> ConfigModeContext:
        """Context manager: enter config mode on enter, exit (without saving) on leave."""
        return ConfigModeContext(self)

    def read_config(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_CONFIG)
        return regs[0] & 0xFFFF

    def write_config(self, value: int) -> None:
        self._write_reg(RegisterMap.M_REG_CONFIG, value & 0xFFFF)

    def read_config2(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_CONFIG2)
        return regs[0] & 0xFFFF

    def write_config2(self, value: int) -> None:
        self._write_reg(RegisterMap.M_REG_CONFIG2, value & 0xFFFF)

    def read_baud_rate(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_BAUD_RATE)
        idx = regs[0] & 0xFFFF
        return BAUD_RATES.get(idx, 115200)

    def write_baud_rate_index(self, index: int) -> None:
        self._write_reg(RegisterMap.M_REG_BAUD_RATE, index & 0xFF)

    def set_baud_rate(self, rate: int) -> None:
        if rate not in BAUD_RATE_TO_INDEX:
            raise ValueError(f"Baud rate must be one of {list(BAUD_RATE_TO_INDEX.keys())}")
        self.write_baud_rate_index(BAUD_RATE_TO_INDEX[rate])

    def read_slave_id(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_SLAVEID)
        return regs[0] & 0xFF

    def set_slave_id(self, slave: int) -> None:
        if not 1 <= slave <= 247:
            raise ValueError("slave must be 1-247")
        self._write_reg(RegisterMap.M_REG_SLAVEID, slave)

    def read_calibration_time(self) -> int:
        regs = self._read_reg(RegisterMap.M_REG_CALIBRATION_TIME)
        return regs[0] & 0xFFFF

    def write_calibration_time(self, ms: int) -> None:
        self._write_reg(RegisterMap.M_REG_CALIBRATION_TIME, ms & 0xFFFF)

    # --- Commands ---

    def reset(self) -> None:
        self._write_reg(RegisterMap.M_REG_COMMAND, CMD_RESET)

    def factory_reset(self) -> None:
        self._write_reg(RegisterMap.M_REG_COMMAND, CMD_FACTORY_RESET)

    # --- Calibration ---

    def calibrate_point(self, channel: int, point: int, reference_value: float) -> None:
        if channel not in (1, 2, 3, 4) or point not in (0, 1):
            raise ValueError("channel must be 1-4, point must be 0 or 1")
        cmd = CALIBRATION_COMMANDS[(channel, point)]
        words = encode_float_cdab(reference_value)
        self._write_regs(RegisterMap.M_REG_CAL_REFERENCE, words)
        self._write_reg(RegisterMap.M_REG_COMMAND, cmd)

    def wait_calibration_done(
        self,
        timeout_sec: float = 60.0,
        poll_interval_sec: float = 0.2,
    ) -> None:
        import time
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if not self.is_calibrating():
                return
            time.sleep(poll_interval_sec)
        raise CalibrationTimeoutError(f"Calibration did not complete within {timeout_sec}s")

    # --- Low-level ---

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        return self._read_registers(address, count)

    def write_register(self, address: int, value: int) -> None:
        self._write_register(address, value & 0xFFFF)

    def write_registers(self, address: int, values: list[int]) -> None:
        self._write_registers(address, [v & 0xFFFF for v in values])
