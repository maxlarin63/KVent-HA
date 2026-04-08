"""Fan platform for KVent (Komfovent C4).

One fan entity per config entry.  Controls:
  - Power on/off  (REG_STATUS 1000)
  - Preset modes: UI reflects actual ventilation level from REG_SPEED (1101).
      "Auto"     → mode = 1
      "Speed 1–3" → manual mode + write 1–3 to REG_SPEED_MANUAL (1100)
      "Boost"    → manual mode + OVR enable/time (1111 / 1112)
      "Standby"  → REG_STATUS 0 (C4 stop)
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FAN_STATE_TO_PRESET,
    MODE_AUTO,
    MODE_MANUAL,
    PRESET_AUTO,
    PRESET_MODES,
    PRESET_TO_SPEED,
    SEASON_OPTION_WINTER,
    SEASON_VALUE_TO_OPTION,
    SPEED_MAP,
)
from .coordinator import KVentCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KVentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KVentFan(coordinator, entry)])


class KVentFan(CoordinatorEntity[KVentCoordinator], FanEntity):
    """KVent ventilation fan entity."""

    _attr_has_entity_name = True
    _attr_name = None  # device name is the entity name
    _attr_preset_modes = PRESET_MODES
    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: KVentCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Komfovent C4",
            manufacturer="Komfovent",
            model="C4",
        )

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.power

    @property
    def preset_mode(self) -> str | None:
        data = self.coordinator.data
        if not data.power:
            return None
        if data.mode == MODE_AUTO:
            return PRESET_AUTO
        return FAN_STATE_TO_PRESET.get((MODE_MANUAL, data.speed))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Mirror key sensor/select/binary state on the primary fan (more-info / dev tools).

        Separate entities stay registered; this only duplicates their values for convenience.
        """
        d = self.coordinator.data
        season = SEASON_VALUE_TO_OPTION.get(d.season, SEASON_OPTION_WINTER)
        current = SPEED_MAP.get(d.speed, str(d.speed))
        out: dict[str, Any] = {
            "supply_air_temperature": d.supply_temp,
            "setpoint_temperature": d.setpoint,
            "ventilation_mode": "auto" if d.mode == MODE_AUTO else "manual",
            "season": season,
            "current_speed": current,
            "service_required": d.service,
        }
        if d.mode != MODE_AUTO:
            out["target_speed"] = SPEED_MAP.get(d.speed_manual, str(d.speed_manual))
        return out

    # ── Commands ──────────────────────────────────────────────────────────────

    async def async_turn_on(self, *args: Any, **kwargs: Any) -> None:
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self, *args: Any, **kwargs: Any) -> None:
        await self.coordinator.async_set_power(False)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_AUTO:
            # Power on if needed, then switch to auto mode
            if not self.coordinator.data.power:
                await self.coordinator.async_set_power(True)
            await self.coordinator.async_set_auto_mode()
        else:
            level = PRESET_TO_SPEED.get(preset_mode)
            if level is None:
                _LOGGER.warning("Unknown preset mode: %s", preset_mode)
                return
            # Power on if needed, then set manual speed
            if not self.coordinator.data.power:
                await self.coordinator.async_set_power(True)
            await self.coordinator.async_set_manual_speed(level)
