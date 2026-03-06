"""Triton2 library exceptions."""


class Triton2Error(Exception):
    """Base exception for Triton2 library."""

    pass


class ConfigRequiredError(Triton2Error):
    """Raised when writing to a config-only register outside configuration mode."""

    pass


class CalibrationTimeoutError(Triton2Error):
    """Raised when calibration does not complete within the timeout."""

    pass


class ModbusConnectionError(Triton2Error):
    """Raised on Modbus/serial communication errors."""

    pass
