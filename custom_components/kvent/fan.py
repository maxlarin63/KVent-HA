"""Fan platform for KVent (Komfovent C4).

One fan entity per config entry.  Controls:
  - Power on/off  (REG_STATUS 1000)
  - Preset modes  (REG_MODE 1102 + REG_SPEED_MANUAL 1100):
      "Auto"    → mode = 1 (auto ventilation)
      "Speed 1" → mode = 0, speed_manual = 1
      "Speed 2" → mode = 0, speed_manual = 2
      "Speed 3" → mode = 0, speed_manual = 3
      "Boost"   → mode = 0, speed_manual = 4
      "Standby" → mode = 0, speed_manual = 0
"""
from __future__ import annotations

import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MODE_AUTO,
    PRESET_AUTO,
    PRESET_BOOST,
    PRESET_MODES,
    PRESET_SPEED_1,
    PRESET_SPEED_2,
    PRESET_SPEED_3,
    PRESET_STANDBY,
    PRESET_TO_SPEED,
    SPEED_BOOST,
    SPEED_LEVEL_1,
    SPEED_LEVEL_2,
    SPEED_LEVEL_3,
    SPEED_STANDBY,
)
from .coordinator import KVentCoordinator

_LOGGER = logging.getLogger(__name__)

# Reverse map: (mode, speed_manual) → preset label
_STATE_TO_PRESET: dict[tuple[int, int], str] = {
    (MODE_AUTO, -1): PRESET_AUTO,   # auto: speed_manual is don't-care
    (0, SPEED_STANDBY): PRESET_STANDBY,
    (0, SPEED_LEVEL_1): PRESET_SPEED_1,
    (0, SPEED_LEVEL_2): PRESET_SPEED_2,
    (0, SPEED_LEVEL_3): PRESET_SPEED_3,
    (0, SPEED_BOOST): PRESET_BOOST,
}


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
        return _STATE_TO_PRESET.get((0, data.speed_manual))

    # ── Commands ──────────────────────────────────────────────────────────────

    async def async_turn_on(self, **kwargs: object) -> None:
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self, **kwargs: object) -> None:
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
