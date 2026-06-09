"""Tests for the KVent coordinator sanity-check logic.

Covers the two device-firmware-quirk workarounds:
  - REG_STATUS=0 ignored while REG_FANS_STATUS=1 (cycling fix, v0.0.22)
  - REG 1200 glitches suppressed by range + sudden-jump check (v0.0.24)

Mocks the modbus client and runs ``_async_update_data`` directly. No real I/O.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kvent.const import POLL_FAILURE_GRACE
from custom_components.kvent.coordinator import KVentCoordinator
from custom_components.kvent.modbus import KVentData


def _data(**overrides) -> KVentData:
    """Realistic-default KVentData; override individual fields per test."""
    base = {
        "power": True,
        "season": 0,
        "service": False,
        "speed_manual": 2,
        "speed": 2,
        "mode": 0,
        "supply_temp": 24.5,
        "setpoint": 22.0,
        "alarm_stop_flags": 0,
        "alarm_stop_code": 0,
        "fans_running": True,
    }
    base.update(overrides)
    return KVentData(**base)


def _coordinator(prev: KVentData | None, new: KVentData) -> KVentCoordinator:
    """Build a KVentCoordinator with mocked hass and modbus client."""
    hass = MagicMock()
    coord = KVentCoordinator(hass, host="1.2.3.4", port=502, scan_interval=5)
    coord._client = MagicMock()
    coord._client.async_read_all = AsyncMock(return_value=new)
    coord._client.disconnect = AsyncMock()
    # DataUpdateCoordinator stores last data on `self.data`; seed it directly.
    coord.data = prev
    return coord


@pytest.mark.asyncio
async def test_reg_status_zero_with_running_fans_is_overridden():
    """C4 firmware quirk: REG_STATUS briefly reads 0 while fans keep operating."""
    prev = _data(power=True)
    new = _data(power=False, fans_running=True, alarm_stop_code=0)
    coord = _coordinator(prev, new)

    out = await coord._async_update_data()

    assert out.power is True  # overridden


@pytest.mark.asyncio
async def test_reg_status_zero_with_alarm_is_not_overridden():
    """Legitimate stop with an alarm code must surface as power=False."""
    prev = _data(power=True)
    new = _data(power=False, fans_running=False, alarm_stop_code=4)  # heater overheat
    coord = _coordinator(prev, new)

    out = await coord._async_update_data()

    assert out.power is False


@pytest.mark.asyncio
async def test_supply_temp_out_of_range_carries_forward():
    """REG 1200 glitch (e.g. -256.0 °C from byte-swap) → use prev value."""
    prev = _data(supply_temp=24.8)
    new = _data(supply_temp=-256.0)  # raw 0xF600 byte-swap case
    coord = _coordinator(prev, new)

    out = await coord._async_update_data()

    assert out.supply_temp == 24.8


@pytest.mark.asyncio
async def test_supply_temp_sudden_jump_carries_forward():
    """In-range but physically implausible 1-poll jump → use prev value."""
    prev = _data(supply_temp=25.5)
    new = _data(supply_temp=0.0)  # the May 15 0xC4 anomaly: 0x0000 in range
    coord = _coordinator(prev, new)

    out = await coord._async_update_data()

    assert out.supply_temp == 25.5


@pytest.mark.asyncio
async def test_supply_temp_normal_drift_is_preserved():
    """Routine ±0.5 °C drift must pass through untouched."""
    prev = _data(supply_temp=24.5)
    new = _data(supply_temp=25.0)
    coord = _coordinator(prev, new)

    out = await coord._async_update_data()

    assert out.supply_temp == 25.0


@pytest.mark.asyncio
async def test_first_poll_with_no_prev_accepts_value_as_is():
    """When self.data is None, no carry-forward is possible — accept the read."""
    new = _data(supply_temp=24.0)
    coord = _coordinator(prev=None, new=new)

    out = await coord._async_update_data()

    assert out.supply_temp == 24.0


# ── Transient poll-failure grace (v0.0.25) ────────────────────────────────────


@pytest.mark.asyncio
async def test_transient_failure_within_grace_carries_forward():
    """A single failed poll keeps entities available by reusing the last snapshot."""
    prev = _data(power=True, supply_temp=25.2)
    coord = _coordinator(prev, new=prev)
    coord._client.async_read_all = AsyncMock(side_effect=TimeoutError())

    out = await coord._async_update_data()

    assert out is prev  # carried forward, no UpdateFailed → entity stays `on`


@pytest.mark.asyncio
async def test_sustained_failure_beyond_grace_raises():
    """Once consecutive failures exceed the grace window, surface UpdateFailed."""
    prev = _data(power=True)
    coord = _coordinator(prev, new=prev)
    coord._client.async_read_all = AsyncMock(side_effect=TimeoutError())

    for _ in range(POLL_FAILURE_GRACE):
        assert await coord._async_update_data() is prev  # absorbed
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()  # grace exhausted


@pytest.mark.asyncio
async def test_failure_with_no_prev_raises_immediately():
    """No prior snapshot to fall back on → fail on the first error."""
    coord = _coordinator(prev=None, new=_data())
    coord._client.async_read_all = AsyncMock(side_effect=TimeoutError())

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


@pytest.mark.asyncio
async def test_success_resets_grace_counter():
    """A good poll between blips re-arms the full grace window."""
    prev = _data(power=True)
    good = _data(power=True, supply_temp=24.9)
    coord = _coordinator(prev, new=prev)

    # Burn grace − 1 failures, then a success must reset the counter.
    coord._client.async_read_all = AsyncMock(side_effect=TimeoutError())
    for _ in range(POLL_FAILURE_GRACE - 1):
        await coord._async_update_data()
    coord._client.async_read_all = AsyncMock(return_value=good)
    await coord._async_update_data()
    assert coord._consecutive_failures == 0

    # Counter reset means a fresh full grace window is available again.
    coord._client.async_read_all = AsyncMock(side_effect=TimeoutError())
    for _ in range(POLL_FAILURE_GRACE):
        assert await coord._async_update_data() is not None
