"""Tests for DeviceScanner."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from triton2.exceptions import ModbusConnectionError
from triton2.scanner import DeviceScanner


@patch("triton2.scanner.ModbusSerialClient")
def test_scanner_default_sets_pymodbus_logging_to_critical(mock_serial):
    mock_inst = MagicMock()
    mock_inst.connect.return_value = True
    mock_serial.return_value = mock_inst

    mock_logger = MagicMock()
    mock_logger.level = 0
    with patch("triton2.scanner.logging.getLogger", return_value=mock_logger):
        with DeviceScanner("COM1"):
            pass
    assert mock_logger.setLevel.call_args_list[0][0][0] == logging.CRITICAL
    assert mock_logger.setLevel.call_args_list[-1][0][0] == 0  # restored


@patch("triton2.scanner.ModbusSerialClient")
def test_scanner_verbose_sets_pymodbus_logging_to_debug(mock_serial):
    mock_inst = MagicMock()
    mock_inst.connect.return_value = True
    mock_serial.return_value = mock_inst

    mock_logger = MagicMock()
    mock_logger.level = 0
    with patch("triton2.scanner.logging.getLogger", return_value=mock_logger):
        with DeviceScanner("COM1", verbose=True):
            pass
    assert mock_logger.setLevel.call_args_list[0][0][0] == logging.DEBUG
    assert mock_logger.setLevel.call_args_list[-1][0][0] == 0


@patch("triton2.scanner.ModbusSerialClient")
def test_scanner_restores_log_level_if_connect_fails(mock_serial):
    mock_inst = MagicMock()
    mock_inst.connect.return_value = False
    mock_serial.return_value = mock_inst

    mock_logger = MagicMock()
    mock_logger.level = 15  # e.g. custom level
    with patch("triton2.scanner.logging.getLogger", return_value=mock_logger):
        with pytest.raises(ModbusConnectionError):
            DeviceScanner("COM1").connect()
    assert mock_logger.setLevel.call_args_list[-1][0][0] == 15
