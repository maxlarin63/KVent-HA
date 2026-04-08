"""Number platform for KVent (Komfovent C4).

Temperature setpoint — register 1201 (R/W, signed int16 = tenths of °C).
"""
from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KVentCoordinator

SETPOINT_DESCRIPTION = NumberEntityDescription(
    key="setpoint",
    name="Temperature setpoint",
    device_class=NumberDeviceClass.TEMPERATURE,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    native_min_value=0.0,
    native_max_value=30.0,
    native_step=0.5,
    mode=NumberMode.BOX,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KVentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KVentSetpointNumber(coordinator, entry)])


class KVentSetpointNumber(CoordinatorEntity[KVentCoordinator], NumberEntity):
    """Writable supply-air setpoint (Komfovent register 1201)."""

    entity_description = SETPOINT_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: KVentCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_setpoint_number"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.setpoint

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_setpoint(value)
