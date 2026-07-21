"""Binary sensor platform for KVent (Komfovent C4).

Entities:
  - Service Required  (REG_SERVICE 1007, binary: manual bit №14 = 0x2000)
      DeviceClass.PROBLEM → on = problem present
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KVentCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KVentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KVentServiceSensor(coordinator, entry)])


class KVentServiceSensor(CoordinatorEntity[KVentCoordinator], BinarySensorEntity):
    """Binary sensor that turns on when the unit requires servicing."""

    _attr_has_entity_name = True
    _attr_name = "Service Required"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:wrench-clock"

    def __init__(self, coordinator: KVentCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_service"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.service
