"""Shared pytest fixtures for KVent tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_socket

from custom_components.kvent.modbus import KVentData


@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest) -> None:
    """Allow ProactorEventLoop self-pipe before pytest-asyncio builds the loop.

    pytest-homeassistant-custom-component disables all sockets in pytest_runtest_setup,
    which runs after fixture setup has started. The default event_loop fixture then
    hits SocketBlockedError on Windows. Modbus I/O remains mocked in our tests.
    """
    if fixturedef.argname == "event_loop":
        pytest_socket.enable_socket()


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
