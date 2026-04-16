"""Tests for ChannelBuffer and ChannelStreamReader."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from triton2.stream import ALL_CHANNELS, Channel, ChannelBuffer, ChannelStreamReader
from triton2.client import Triton2Client

# Four calibrated channels only (for tests that expect 4 value columns)
CAL_CHANNELS = [Channel.CH1_CAL, Channel.CH2_CAL, Channel.CH3_CAL, Channel.CH4_CAL]


def test_channel_buffer_default_columns():
    buf = ChannelBuffer()
    assert "timestamp_ms" in buf.column_names
    assert "ch1_cal" in buf.column_names
    assert "ch1_raw" in buf.column_names
    assert len(buf.column_names) == 1 + len(ALL_CHANNELS)


def test_channel_buffer_append_list():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    buf.append(1000, [1.0, 2.0, 3.0, 4.0])
    buf.append(2000, [5.0, 6.0, 7.0, 8.0])
    assert len(buf) == 2
    assert not buf.is_empty


def test_channel_buffer_append_dict():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    buf.append(1000, {"ch1_cal": 1.0, "ch2_cal": 2.0, "ch3_cal": 3.0, "ch4_cal": 4.0})
    assert len(buf) == 1


def test_channel_buffer_clear():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    buf.append(1000, [1.0, 2.0, 3.0, 4.0])
    buf.clear()
    assert len(buf) == 0
    assert buf.is_empty


def test_channel_buffer_to_numpy_empty():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    arr = buf.to_numpy()
    assert arr.shape == (0, 5)


def test_channel_buffer_to_numpy():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    buf.append(100, [1.0, 2.0, 3.0, 4.0])
    buf.append(200, [5.0, 6.0, 7.0, 8.0])
    arr = buf.to_numpy()
    assert arr.shape == (2, 5)
    np.testing.assert_array_almost_equal(arr[0], [100, 1, 2, 3, 4])
    np.testing.assert_array_almost_equal(arr[1], [200, 5, 6, 7, 8])


def test_channel_buffer_to_csv():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    buf.append(100, [1.0, 2.0, 3.0, 4.0])
    buf.append(200, [5.0, 6.0, 7.0, 8.0])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    try:
        buf.to_csv(path)
        text = Path(path).read_text()
        assert "timestamp_ms" in text
        assert "ch1_cal" in text
        assert "100" in text
        assert "200" in text
    finally:
        Path(path).unlink(missing_ok=True)


def test_channel_buffer_to_dataframe_requires_pandas():
    buf = ChannelBuffer(channels=CAL_CHANNELS)
    buf.append(100, [1.0, 2.0, 3.0, 4.0])
    try:
        import pandas as pd
        df = buf.to_dataframe()
        assert len(df) == 1
        assert list(df.columns) == buf.column_names
    except ImportError:
        with pytest.raises(ImportError, match="pandas"):
            buf.to_dataframe()


def test_channel_buffer_maxlen():
    buf = ChannelBuffer(channels=CAL_CHANNELS, maxlen=3)
    for i in range(5):
        buf.append(100 * i, [float(i)] * 4)
    assert len(buf) == 3
    arr = buf.to_numpy()
    assert arr[0, 0] == 200
    assert arr[2, 0] == 400


@patch("triton2.client.ModbusSerialClient")
def test_channel_stream_reader_read_one(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    from triton2.codec import encode_float_cdab
    ts_words = [0, 1000]
    raw_words = []
    for v in [10.0, 20.0, 30.0, 40.0]:
        raw_words.extend(encode_float_cdab(v))
    cal_words = []
    for v in [1.0, 2.0, 3.0, 4.0]:
        cal_words.extend(encode_float_cdab(v))
    all_regs = ts_words + raw_words + cal_words
    mock_client.read_holding_registers.return_value = MagicMock(isError=lambda: False, registers=all_regs)

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    reader = ChannelStreamReader(t2, channels=CAL_CHANNELS)
    data = reader.read_one()
    assert data["timestamp_ms"] == 1000
    assert data["calibrated"][1] == pytest.approx(1.0, rel=1e-5)
    assert len(reader) == 1
    np.testing.assert_array_almost_equal(reader.to_numpy()[0], [1000, 1, 2, 3, 4])


@patch("triton2.client.ModbusSerialClient")
def test_channel_stream_reader_read_n(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    from triton2.codec import encode_float_cdab
    ts_words = [0, 0]
    raw_words = [0] * 8
    cal_words = []
    for v in [1.0, 2.0, 3.0, 4.0]:
        cal_words.extend(encode_float_cdab(v))
    all_regs = ts_words + raw_words + cal_words
    mock_client.read_holding_registers.return_value = MagicMock(isError=lambda: False, registers=all_regs)

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    reader = ChannelStreamReader(t2, channels=CAL_CHANNELS)
    out = reader.read_n(3)
    assert out is reader
    assert len(reader) == 3
    assert mock_client.read_holding_registers.call_count == 3


@patch("triton2.client.ModbusSerialClient")
def test_channel_stream_reader_raw_only_reads_10_words(MockSerialClient):
    """When only raw channels are requested, client should read 10 words (timestamp+raw), not 18."""
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    from triton2.codec import encode_float_cdab
    ts_words = [0, 100]
    raw_words = []
    for v in [1.0, 2.0, 3.0, 4.0]:
        raw_words.extend(encode_float_cdab(v))
    # Only 10 words (timestamp 2 + raw 8)
    regs = ts_words + raw_words
    mock_client.read_holding_registers.return_value = MagicMock(isError=lambda: False, registers=regs)

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    raw_channels = [Channel.CH1_RAW, Channel.CH2_RAW, Channel.CH3_RAW, Channel.CH4_RAW]
    reader = ChannelStreamReader(t2, channels=raw_channels)
    reader.read_one()
    mock_client.read_holding_registers.assert_called_once()
    call = mock_client.read_holding_registers.call_args
    assert call.kwargs["count"] == 10  # timestamp+raw only


@patch("triton2.client.ModbusSerialClient")
def test_channel_stream_reader_read_one_batch_false(MockSerialClient):
    """When batch=False, read_one uses separate Modbus reads for timestamp and each channel."""
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    from triton2.codec import encode_float_cdab
    # read_timestamp_ms uses _read_registers(16,2); then one read per channel
    ts_regs = [0, 500]  # 500 ms
    mock_client.read_holding_registers.side_effect = [
        MagicMock(isError=lambda: False, registers=ts_regs),
        MagicMock(isError=lambda: False, registers=encode_float_cdab(1.5)),
        MagicMock(isError=lambda: False, registers=encode_float_cdab(2.0)),
    ]

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    reader = ChannelStreamReader(t2, channels=[Channel.CH1_CAL, Channel.CH2_CAL])
    data = reader.read_one(batch=False)
    assert data["timestamp_ms"] == 500
    arr = reader.to_numpy()
    assert arr[0, 0] == 500
    assert arr[0, 1] == pytest.approx(1.5, rel=1e-5)
    assert arr[0, 2] == pytest.approx(2.0, rel=1e-5)
    assert mock_client.read_holding_registers.call_count == 3  # timestamp + 2 channels
