"""
Simple Modbus RTU device scanner: find which slave IDs respond on the bus.
"""

from __future__ import annotations

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

from .exceptions import ModbusConnectionError


# Default probe: one holding register at address 0 (Triton2 status register).
# Any device with a holding register at 0 will respond.
DEFAULT_PROBE_ADDRESS = 0
DEFAULT_PROBE_COUNT = 1


class DeviceScanner:
    """
    Scan a Modbus RTU bus for responding slave (unit) IDs.
    Uses a minimal read of holding registers to detect devices.

    ``timeout`` and ``retries`` are passed to pymodbus (per-request wait and retry count);
    lower values speed up scans over empty IDs.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        probe_address: int = DEFAULT_PROBE_ADDRESS,
        probe_count: int = DEFAULT_PROBE_COUNT,
        *,
        timeout: float = 3.0,
        retries: int = 3,
        **serial_kwargs: object,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.probe_address = probe_address
        self.probe_count = probe_count
        self.timeout = timeout
        self.retries = retries
        self._serial_kwargs = serial_kwargs
        self._client: ModbusSerialClient | None = None

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
            timeout=self.timeout,
            retries=self.retries,
        )
        if not self._client.connect():
            raise ModbusConnectionError(f"Failed to connect to {self.port}")

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> DeviceScanner:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def probe(self, slave_id: int) -> bool:
        if self._client is None:
            raise ModbusConnectionError("Not connected; call connect() first")
        try:
            result = self._client.read_holding_registers(
                self.probe_address,
                count=self.probe_count,
                device_id=slave_id,
            )
        except ModbusIOException:
            # No reply (wrong ID, timeout, bus idle) — not a responding device.
            return False
        return not result.isError()

    def scan(
        self,
        slave_ids: range | list[int] | None = None,
    ) -> list[int]:
        """
        Probe each slave ID and return those that respond.

        Args:
            slave_ids: IDs to try. Defaults to range(1, 248) (Modbus 1–247).

        Returns:
            List of slave IDs that responded successfully.
        """
        if slave_ids is None:
            slave_ids = range(1, 248)
        if isinstance(slave_ids, range):
            slave_ids = list(slave_ids)
        found: list[int] = []
        for sid in slave_ids:
            if 1 <= sid <= 247 and self.probe(sid):
                found.append(sid)
        return found
