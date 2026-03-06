"""
High-speed channel reading and buffering with export to numpy, pandas, and CSV.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from .client import Triton2Client
from .codec import decode_float_cdab
from .registers import ALL_CHANNELS, Channel, ChannelKind


class ChannelBuffer:
    """
    In-memory buffer for timestamped channel data. Supports append, clear,
    and export to numpy, pandas DataFrame, or CSV.
    """

    def __init__(
        self,
        channels: list[Channel] | None = None,
        maxlen: int | None = None,
    ) -> None:
        if channels is None:
            channels = ALL_CHANNELS.copy()
        self._channels = list(channels)
        self._columns = ["timestamp_ms"] + [c.label for c in self._channels]
        self._maxlen = maxlen
        self._rows: list[tuple[int | float, ...]] = []

    @property
    def column_names(self) -> list[str]:
        return self._columns.copy()

    def append(self, timestamp_ms: int, values: dict[str, float] | list[float]) -> None:
        if isinstance(values, dict):
            row_values: list[int | float] = [timestamp_ms]
            for ch in self._channels:
                row_values.append(values.get(ch.label, float("nan")))
            row = tuple(row_values)
        else:
            row = (timestamp_ms,) + tuple(float(v) for v in values)
        self._rows.append(row)
        if self._maxlen is not None and len(self._rows) > self._maxlen:
            self._rows = self._rows[-self._maxlen :]

    def clear(self) -> None:
        self._rows.clear()

    def __len__(self) -> int:
        return len(self._rows)

    @property
    def is_empty(self) -> bool:
        return len(self._rows) == 0

    def to_numpy(self) -> np.ndarray:
        if not self._rows:
            return np.empty((0, len(self._columns)), dtype=np.float64)
        return np.array(self._rows, dtype=np.float64)

    def to_dataframe(self):  # -> pd.DataFrame (type hint omitted to avoid requiring pandas)
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install triton2-modbus[pandas]"
            ) from e
        arr = self.to_numpy()
        if arr.size == 0:
            return pd.DataFrame(columns=self._columns)
        return pd.DataFrame(arr, columns=self._columns)

    def to_csv(self, path: str | Path, **kwargs: Any) -> None:
        path = Path(path)
        with path.open("w", newline="") as f:
            writer = csv.writer(f, **{k: v for k, v in kwargs.items() if k in ("delimiter", "lineterminator")})
            writer.writerow(self._columns)
            writer.writerows(self._rows)


class ChannelStreamReader:
    """
    High-speed reader that uses Triton2Client to read at maximum rate.
    Only reads the channels given in the constructor (default: all channels).
    Includes an integrated buffer: use read_n/read_for, then to_numpy()/to_csv()/to_dataframe().
    """

    def __init__(
        self,
        client: Triton2Client,
        channels: list[Channel] | None = None,
        clear_serial_before_read: bool = False,
        maxlen: int | None = None,
    ) -> None:
        self._client = client
        if clear_serial_before_read:
            self._client.clear_serial_before_read = True
        if channels is None:
            channels = ALL_CHANNELS.copy()
        self._channels = list(channels)
        self._buffer = ChannelBuffer(channels=self._channels, maxlen=maxlen)

    @property
    def column_names(self) -> list[str]:
        return self._buffer.column_names

    def __len__(self) -> int:
        return len(self._buffer)

    @property
    def is_empty(self) -> bool:
        return self._buffer.is_empty

    def clear(self) -> None:
        """Clear all samples from the internal buffer."""
        self._buffer.clear()

    def to_numpy(self) -> np.ndarray:
        """Export buffered samples to a numpy array (timestamp_ms + channel columns)."""
        return self._buffer.to_numpy()

    def to_dataframe(self):
        """Export buffered samples to a pandas DataFrame. Requires pandas."""
        return self._buffer.to_dataframe()

    def to_csv(self, path: str | Path, **kwargs: Any) -> None:
        """Write buffered samples to a CSV file."""
        self._buffer.to_csv(path, **kwargs)

    def read_one(self, batch: bool = True) -> dict[str, Any]:
        """
        Perform one read, append to buffer, return sample dict.

        If batch is True (default), use a single Modbus request for timestamp and
        all requested channels (or minimal block when only raw or only cal).
        If batch is False, read timestamp and each channel in separate Modbus requests.
        """
        if batch:
            need_cal = any(c.kind == ChannelKind.CAL for c in self._channels)
            need_raw = any(c.kind == ChannelKind.RAW for c in self._channels)
            if need_raw and need_cal:
                data = self._client.read_all_measurements()
            elif need_raw:
                data = self._client.read_timestamp_and_raw()
            else:
                data = self._client.read_all_measurements()
            ts = data["timestamp_ms"]
            row: dict[str, float] = {"timestamp_ms": ts}
            cal_src = data.get("calibrated", {})
            raw_src = data.get("raw", {})
            for ch in self._channels:
                idx = ch.index
                if ch.kind == ChannelKind.CAL:
                    row[ch.label] = cal_src.get(idx, float("nan"))
                else:
                    row[ch.label] = raw_src.get(idx, float("nan"))
        else:
            ts = self._client.read_timestamp_ms()
            row = {"timestamp_ms": ts}
            for ch in self._channels:
                addr = ch.register.address
                size = ch.register.words
                regs = self._client.read_holding_registers(addr, size)
                row[ch.label] = decode_float_cdab(regs)
            data = {"timestamp_ms": ts, "raw": {}, "calibrated": {}}
            for ch in self._channels:
                idx = ch.index
                if ch.kind == ChannelKind.CAL:
                    data["calibrated"][idx] = row[ch.label]
                else:
                    data["raw"][idx] = row[ch.label]
        self._buffer.append(ts, row)
        return data

    def read_n(self, n: int, batch: bool = True) -> ChannelStreamReader:
        """Read n samples at maximum speed. Returns self for chaining."""
        for _ in range(n):
            self.read_one(batch=batch)
        return self

    def read_for(
        self,
        duration_sec: float,
        poll_interval_sec: float | None = None,
        batch: bool = True,
    ) -> ChannelStreamReader:
        """Read for duration_sec (at max speed if poll_interval_sec is None). Returns self."""
        import time
        deadline = time.monotonic() + duration_sec
        while time.monotonic() < deadline:
            self.read_one(batch=batch)
            if poll_interval_sec is not None and poll_interval_sec > 0:
                time.sleep(poll_interval_sec)
        return self
