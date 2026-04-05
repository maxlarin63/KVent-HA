"""Select platform for KVent (Komfovent C4).

Entities:
  - Season  (REG_SEASON 1001)  options: Summer / Winter
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SEASON_OPTION_TO_VALUE,
    SEASON_OPTION_WINTER,
    SEASON_OPTIONS,
    SEASON_VALUE_TO_OPTION,
)
from .coordinator import KVentCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KVentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KVentSeasonSelect(coordinator, entry)])


class KVentSeasonSelect(CoordinatorEntity[KVentCoordinator], SelectEntity):
    """Select entity for Summer / Winter season mode."""

    _attr_has_entity_name = True
    _attr_name = "Season"
    _attr_options = SEASON_OPTIONS
    _attr_icon = "mdi:weather-partly-cloudy"

    def __init__(self, coordinator: KVentCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_season"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )

    @property
    def current_option(self) -> str:
        return SEASON_VALUE_TO_OPTION.get(self.coordinator.data.season, SEASON_OPTION_WINTER)

    async def async_select_option(self, option: str) -> None:
        value = SEASON_OPTION_TO_VALUE.get(option)
        if value is None:
            _LOGGER.warning("Unknown season option: %s", option)
            return
        await self.coordinator.async_set_season(value)
