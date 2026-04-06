"""Tests for the KVent climate entity."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACAction, HVACMode

from custom_components.kvent.const import (
    MODE_AUTO,
    MODE_MANUAL,
    PRESET_AUTO,
    PRESET_BOOST,
    PRESET_MODES,
    PRESET_SERVICE_ALERT,
    PRESET_SPEED_1,
    PRESET_SPEED_2,
    PRESET_STANDBY,
    SEASON_OPTION_SUMMER,
    SEASON_OPTION_WINTER,
    SPEED_BOOST,
    SPEED_LEVEL_1,
    SPEED_LEVEL_2,
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


def _make_climate(data: KVentData):
    from custom_components.kvent.climate import KVentClimate

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.async_set_power = AsyncMock()
    coordinator.async_set_auto_mode = AsyncMock()
    coordinator.async_set_manual_speed = AsyncMock()
    coordinator.async_set_setpoint = AsyncMock()
    coordinator.async_set_season = AsyncMock()

    entry = MagicMock()
    entry.entry_id = "test_entry"

    climate = KVentClimate.__new__(KVentClimate)
    climate.coordinator = coordinator
    climate._attr_unique_id = "test_climate"
    return climate, coordinator


def test_hvac_off_when_power_false():
    climate, _ = _make_climate(_make_data(power=False))
    assert climate.hvac_mode == HVACMode.OFF
    assert climate.hvac_action == HVACAction.OFF


def test_hvac_fan_only_when_power_true():
    climate, _ = _make_climate(_make_data(power=True))
    assert climate.hvac_mode == HVACMode.FAN_ONLY
    assert climate.hvac_action == HVACAction.FAN


def test_preset_none_when_off():
    climate, _ = _make_climate(_make_data(power=False))
    assert climate.preset_mode is None


def test_current_and_target_temperature():
    climate, _ = _make_climate(_make_data())
    assert climate.current_temperature == 18.5
    assert climate.target_temperature == 20.0


@pytest.mark.parametrize("speed,expected", [
    (SPEED_STANDBY, PRESET_STANDBY),
    (SPEED_LEVEL_1, PRESET_SPEED_1),
    (SPEED_LEVEL_2, PRESET_SPEED_2),
    (SPEED_BOOST, PRESET_BOOST),
])
def test_preset_manual_speeds(speed, expected):
    climate, _ = _make_climate(_make_data(power=True, mode=MODE_MANUAL, speed_manual=speed))
    assert climate.preset_mode == expected


def test_preset_auto():
    climate, _ = _make_climate(_make_data(power=True, mode=MODE_AUTO))
    assert climate.preset_mode == PRESET_AUTO


def test_swing_mode_season():
    climate, _ = _make_climate(_make_data(season=1))
    assert climate.swing_mode == SEASON_OPTION_WINTER
    climate2, _ = _make_climate(_make_data(season=0))
    assert climate2.swing_mode == SEASON_OPTION_SUMMER


def test_extra_state_attributes_service_and_speed():
    climate, _ = _make_climate(_make_data(service=True, speed=2, mode=MODE_MANUAL))
    attrs = climate.extra_state_attributes
    assert attrs["service_required"] is True
    assert attrs["service_status"] == "Service required"
    assert attrs["ventilation_mode"] == "manual"
    assert attrs["current_speed"] == "Level 2"
    assert climate.preset_mode == PRESET_SERVICE_ALERT
    assert climate.preset_modes[0] == PRESET_SERVICE_ALERT
    assert len(climate.preset_modes) == len(PRESET_MODES) + 1


def test_preset_modes_normal_when_no_service():
    climate, _ = _make_climate(_make_data(service=False))
    assert climate.preset_modes == list(PRESET_MODES)


def test_icon_when_service():
    climate, _ = _make_climate(_make_data(service=True))
    assert climate.icon == "mdi:wrench-clock"


def test_icon_none_when_no_service():
    climate, _ = _make_climate(_make_data(service=False))
    assert climate.icon is None


def test_extra_state_attributes_auto_ventilation_mode():
    climate, _ = _make_climate(_make_data(mode=MODE_AUTO))
    assert climate.extra_state_attributes["ventilation_mode"] == "auto"


@pytest.mark.asyncio
async def test_set_swing_season():
    climate, coord = _make_climate(_make_data())
    await climate.async_set_swing_mode(SEASON_OPTION_SUMMER)
    coord.async_set_season.assert_awaited_once_with(0)


@pytest.mark.asyncio
async def test_set_hvac_off():
    climate, coord = _make_climate(_make_data(power=True))
    await climate.async_set_hvac_mode(HVACMode.OFF)
    coord.async_set_power.assert_awaited_once_with(False)


@pytest.mark.asyncio
async def test_set_hvac_fan_only():
    climate, coord = _make_climate(_make_data(power=False))
    await climate.async_set_hvac_mode(HVACMode.FAN_ONLY)
    coord.async_set_power.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_set_temperature():
    climate, coord = _make_climate(_make_data())
    await climate.async_set_temperature(temperature=22.5)
    coord.async_set_setpoint.assert_awaited_once_with(22.5)


@pytest.mark.asyncio
async def test_set_preset_auto_powers_on():
    climate, coord = _make_climate(_make_data(power=False))
    await climate.async_set_preset_mode(PRESET_AUTO)
    coord.async_set_power.assert_awaited_once_with(True)
    coord.async_set_auto_mode.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_preset_service_alert_noop():
    climate, coord = _make_climate(_make_data(service=True))
    await climate.async_set_preset_mode(PRESET_SERVICE_ALERT)
    coord.async_set_power.assert_not_awaited()
    coord.async_set_auto_mode.assert_not_awaited()
    coord.async_set_manual_speed.assert_not_awaited()
