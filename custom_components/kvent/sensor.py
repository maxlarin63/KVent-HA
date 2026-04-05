"""Sensor platform for KVent (Komfovent C4).

Entities:
  - Supply Air Temperature  (REG_SUPPLY_TEMP 1200, signed/10 °C)
  - Setpoint Temperature    (REG_SETPOINT   1201, signed/10 °C)
  - Current Speed           (REG_SPEED      1101, 0–4, mapped to label)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SPEED_MAP
from .coordinator import KVentCoordinator
from .modbus import KVentData


@dataclass(frozen=True)
class KVentSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a value accessor."""

    value_fn: Callable[[KVentData], float | str | None] = lambda _: None


SENSOR_DESCRIPTIONS: tuple[KVentSensorDescription, ...] = (
    KVentSensorDescription(
        key="supply_temp",
        name="Supply Air Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        icon="mdi:thermometer-chevron-up",
        value_fn=lambda d: d.supply_temp,
    ),
    KVentSensorDescription(
        key="setpoint",
        name="Setpoint Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        icon="mdi:thermometer-auto",
        value_fn=lambda d: d.setpoint,
    ),
    KVentSensorDescription(
        key="speed",
        name="Current Speed",
        icon="mdi:fan",
        value_fn=lambda d: SPEED_MAP.get(d.speed, f"Unknown ({d.speed})"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KVentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KVentSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class KVentSensor(CoordinatorEntity[KVentCoordinator], SensorEntity):
    """A sensor entity backed by a single KVentData field."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KVentCoordinator,
        entry: ConfigEntry,
        description: KVentSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )

    @property
    def native_value(self) -> float | str | None:
        return self.entity_description.value_fn(self.coordinator.data)
