"""Shared pytest fixtures for KVent tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.kvent.modbus import KVentData


@pytest.fixture
def mock_kvent_data() -> KVentData:
    """Return a realistic KVentData snapshot for tests."""
    return KVentData(
        power=True,
        season=1,          # winter
        service=False,
        speed_manual=2,
        speed=2,
        mode=0,            # manual
        supply_temp=18.5,
        setpoint=20.0,
    )


@pytest.fixture
def mock_modbus_client(mock_kvent_data):
    """Patch KVentModbusClient so tests never open a real TCP socket."""
    with patch(
        "custom_components.kvent.modbus.KVentModbusClient",
        autospec=True,
    ) as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.disconnect = AsyncMock()
        instance.async_read_all = AsyncMock(return_value=mock_kvent_data)
        instance.read_registers = AsyncMock(return_value=[1, 1])
        instance.write_register = AsyncMock()
        yield instance
