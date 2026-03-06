"""Tests for Triton2Client using mocked Modbus."""

import pytest
from unittest.mock import MagicMock, patch

from triton2.client import Triton2Client
from triton2.codec import encode_float_cdab
from triton2.exceptions import ModbusConnectionError


def _mock_result(registers: list[int]):
    r = MagicMock()
    r.isError.return_value = False
    r.registers = registers
    return r


@patch("triton2.client.ModbusSerialClient")
def test_connect_and_close(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    MockSerialClient.return_value = mock_client

    t2 = Triton2Client("COM1")
    t2.connect()
    assert t2._client is not None
    t2.close()
    assert t2._client is None
    mock_client.close.assert_called_once()


@patch("triton2.client.ModbusSerialClient")
def test_connect_fails(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = False
    MockSerialClient.return_value = mock_client

    t2 = Triton2Client("COM1")
    with pytest.raises(ModbusConnectionError, match="Failed to connect"):
        t2.connect()


@patch("triton2.client.ModbusSerialClient")
def test_read_status(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    mock_client.read_holding_registers.return_value = _mock_result([0x04])  # BIT_SENSOR_RUNNING
    MockSerialClient.return_value = mock_client

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    assert t2.read_status() == 4


@patch("triton2.client.ModbusSerialClient")
def test_read_firmware_version(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    mock_client.read_holding_registers.return_value = _mock_result([106])  # v1.06
    MockSerialClient.return_value = mock_client

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    assert t2.read_firmware_version() == 1.06


@patch("triton2.client.ModbusSerialClient")
def test_read_all_calibrated_batch(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    # 4 floats: 1.0, 2.0, 3.0, 4.0 -> 8 words
    words = encode_float_cdab(1.0) + encode_float_cdab(2.0) + encode_float_cdab(3.0) + encode_float_cdab(4.0)
    mock_client.read_holding_registers.return_value = _mock_result(words)

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    cal = t2.read_all_calibrated()
    assert cal == {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}
    mock_client.read_holding_registers.assert_called_once()
    call = mock_client.read_holding_registers.call_args
    assert call[0][0] == 26  # ADDR_ALL_CAL
    assert call[0][1] == 8  # COUNT_ALL_CAL


@patch("triton2.client.ModbusSerialClient")
def test_read_holding_registers_error(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    r = MagicMock()
    r.isError.return_value = True
    r.__str__ = lambda _: "Modbus error"
    mock_client.read_holding_registers.return_value = r

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    with pytest.raises(ModbusConnectionError, match="Modbus error"):
        t2.read_all_calibrated()


@patch("triton2.client.ModbusSerialClient")
def test_write_register(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    r = MagicMock()
    r.isError.return_value = False
    mock_client.write_register.return_value = r

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    t2.reset()
    mock_client.write_register.assert_called_once()
    call = mock_client.write_register.call_args
    assert call[0][0] == 10  # M_REG_COMMAND
    assert call[0][1] == 100  # CMD_RESET
    assert call[1]["slave"] == 1


@patch("triton2.client.ModbusSerialClient")
def test_calibrate_point(MockSerialClient):
    mock_client = MagicMock()
    mock_client.connect.return_value = True
    r = MagicMock()
    r.isError.return_value = False
    mock_client.write_register.return_value = r
    mock_client.write_registers.return_value = r

    t2 = Triton2Client("COM1")
    t2._client = mock_client
    t2.calibrate_point(1, 0, 0.0)
    mock_client.write_registers.assert_called_once()
    mock_client.write_register.assert_called()
    # First write_registers(56, words for 0.0), then write_register(10, 410)
