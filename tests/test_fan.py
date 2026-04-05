"""Tests for the KVent fan entity."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kvent.const import (
    MODE_AUTO,
    MODE_MANUAL,
    PRESET_AUTO,
    PRESET_BOOST,
    PRESET_SPEED_1,
    PRESET_SPEED_2,
    PRESET_SPEED_3,
    PRESET_STANDBY,
    SPEED_BOOST,
    SPEED_LEVEL_1,
    SPEED_LEVEL_2,
    SPEED_LEVEL_3,
    SPEED_STANDBY,
)
from custom_components.kvent.modbus import KVentData


def _make_data(**overrides) -> KVentData:
    base = KVentData(
        power=True,
        season=1,
        service=False,
        speed_manual=2,
        speed=2,
        mode=MODE_MANUAL,
        supply_temp=18.5,
        setpoint=20.0,
    )
    return KVentData(**{**base.__dict__, **overrides})


def _make_fan(data: KVentData):
    """Return a KVentFan with a mocked coordinator (no HA hass needed)."""
    from custom_components.kvent.fan import KVentFan

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.async_set_power = AsyncMock()
    coordinator.async_set_auto_mode = AsyncMock()
    coordinator.async_set_manual_speed = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"

    fan = KVentFan.__new__(KVentFan)
    fan.coordinator = coordinator
    fan._attr_unique_id = "test_fan"
    return fan, coordinator


# ──────────────────────────────────────────────────────────────────────────────
# is_on
# ──────────────────────────────────────────────────────────────────────────────

def test_is_on_when_power_true():
    fan, _ = _make_fan(_make_data(power=True))
    assert fan.is_on is True


def test_is_off_when_power_false():
    fan, _ = _make_fan(_make_data(power=False))
    assert fan.is_on is False


# ──────────────────────────────────────────────────────────────────────────────
# preset_mode resolution
# ──────────────────────────────────────────────────────────────────────────────

def test_preset_none_when_off():
    fan, _ = _make_fan(_make_data(power=False))
    assert fan.preset_mode is None


def test_preset_auto():
    fan, _ = _make_fan(_make_data(power=True, mode=MODE_AUTO))
    assert fan.preset_mode == PRESET_AUTO


@pytest.mark.parametrize("speed,expected", [
    (SPEED_STANDBY, PRESET_STANDBY),
    (SPEED_LEVEL_1, PRESET_SPEED_1),
    (SPEED_LEVEL_2, PRESET_SPEED_2),
    (SPEED_LEVEL_3, PRESET_SPEED_3),
    (SPEED_BOOST, PRESET_BOOST),
])
def test_preset_manual_speeds(speed, expected):
    fan, _ = _make_fan(_make_data(power=True, mode=MODE_MANUAL, speed_manual=speed))
    assert fan.preset_mode == expected


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_turn_on_calls_set_power():
    fan, coord = _make_fan(_make_data(power=False))
    await fan.async_turn_on()
    coord.async_set_power.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_turn_off_calls_set_power():
    fan, coord = _make_fan(_make_data(power=True))
    await fan.async_turn_off()
    coord.async_set_power.assert_awaited_once_with(False)


@pytest.mark.asyncio
async def test_set_preset_auto_calls_set_auto_mode():
    fan, coord = _make_fan(_make_data(power=True, mode=MODE_MANUAL))
    await fan.async_set_preset_mode(PRESET_AUTO)
    coord.async_set_auto_mode.assert_awaited_once()
    coord.async_set_manual_speed.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_preset_speed1():
    fan, coord = _make_fan(_make_data(power=True))
    await fan.async_set_preset_mode(PRESET_SPEED_1)
    coord.async_set_manual_speed.assert_awaited_once_with(SPEED_LEVEL_1)


@pytest.mark.asyncio
async def test_set_preset_boost():
    fan, coord = _make_fan(_make_data(power=True))
    await fan.async_set_preset_mode(PRESET_BOOST)
    coord.async_set_manual_speed.assert_awaited_once_with(SPEED_BOOST)


@pytest.mark.asyncio
async def test_set_preset_powers_on_if_off():
    """Setting a preset while unit is off should power it on first."""
    fan, coord = _make_fan(_make_data(power=False))
    await fan.async_set_preset_mode(PRESET_SPEED_2)
    coord.async_set_power.assert_awaited_once_with(True)
    coord.async_set_manual_speed.assert_awaited_once_with(SPEED_LEVEL_2)


@pytest.mark.asyncio
async def test_set_preset_auto_powers_on_if_off():
    fan, coord = _make_fan(_make_data(power=False))
    await fan.async_set_preset_mode(PRESET_AUTO)
    coord.async_set_power.assert_awaited_once_with(True)
    coord.async_set_auto_mode.assert_awaited_once()
