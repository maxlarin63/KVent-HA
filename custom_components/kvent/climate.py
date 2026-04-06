"""Climate platform for KVent (Komfovent C4).

One climate entity per config — same semantics as the fan + setpoint number, exposed
as a standard HVAC UI (no YAML templates).  Fan, number, and sensor entities stay
registered unchanged.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
    PRESET_SERVICE_ALERT,
    PRESET_TO_SPEED,
    SEASON_OPTION_TO_VALUE,
    SEASON_OPTION_WINTER,
    SEASON_OPTIONS,
    SEASON_VALUE_TO_OPTION,
    SPEED_MAP,
)
from .coordinator import KVentCoordinator

_LOGGER = logging.getLogger(__name__)

CLIMATE_ENTITY_DESCRIPTION = ClimateEntityDescription(
    key="climate",
    translation_key="komfovent_climate",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KVentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KVentClimate(coordinator, entry)])


class KVentClimate(CoordinatorEntity[KVentCoordinator], ClimateEntity):
    """Komfovent C4 as a ClimateEntity (ventilation / fan-only semantics)."""

    entity_description = CLIMATE_ENTITY_DESCRIPTION

    _attr_has_entity_name = True
    _attr_name = "Climate"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
    _attr_swing_modes = list(SEASON_OPTIONS)
    _attr_min_temp = 5.0
    _attr_max_temp = 35.0
    _attr_target_temperature_step = 0.5
    _attr_precision = PRECISION_HALVES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: KVentCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Komfovent C4",
            manufacturer="Komfovent",
            model="C4",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Ensure entity registry has translation_key so the UI uses integration strings
        # for attribute names (e.g. "Season" instead of core "Swing mode").
        if self.registry_entry and self.registry_entry.translation_key != "komfovent_climate":
            er.async_get(self.hass).async_update_entity(
                self.entity_id,
                translation_key="komfovent_climate",
            )

    @property
    def icon(self) -> str | None:
        """Highlight service required on dashboards / widgets (extra_state_attributes are often hidden)."""
        if self.coordinator.data.service:
            return "mdi:wrench-clock"
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data.power:
            return HVACMode.OFF
        return HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> HVACAction | None:
        if not self.coordinator.data.power:
            return HVACAction.OFF
        return HVACAction.FAN

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data.supply_temp

    @property
    def target_temperature(self) -> float | None:
        return self.coordinator.data.setpoint

    @property
    def preset_modes(self) -> list[str]:
        if self.coordinator.data.service:
            return [PRESET_SERVICE_ALERT, *PRESET_MODES]
        return list(PRESET_MODES)

    @property
    def preset_mode(self) -> str | None:
        data = self.coordinator.data
        if data.service:
            return PRESET_SERVICE_ALERT
        if not data.power:
            return None
        if data.mode == MODE_AUTO:
            return PRESET_AUTO
        return FAN_STATE_TO_PRESET.get((MODE_MANUAL, data.speed_manual))

    @property
    def swing_mode(self) -> str | None:
        """Season (Summer/Winter), surfaced as swing_mode for standard climate UIs."""
        return SEASON_VALUE_TO_OPTION.get(self.coordinator.data.season, SEASON_OPTION_WINTER)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Service status and speed snapshot (details panel / templates)."""
        d = self.coordinator.data
        current = SPEED_MAP.get(d.speed, str(d.speed))
        return {
            "service_required": d.service,
            "service_status": "🛠 Service required" if d.service else "✅ OK",
            "ventilation_mode": "auto" if d.mode == MODE_AUTO else "manual",
            "current_speed": current,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_set_power(False)
            return
        if hvac_mode == HVACMode.FAN_ONLY:
            await self.coordinator.async_set_power(True)
            return
        _LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_set_power(False)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp: float | None = kwargs.get("temperature")
        if temp is None:
            return
        await self.coordinator.async_set_setpoint(temp)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_SERVICE_ALERT:
            return
        if preset_mode == PRESET_AUTO:
            if not self.coordinator.data.power:
                await self.coordinator.async_set_power(True)
            await self.coordinator.async_set_auto_mode()
            return
        level = PRESET_TO_SPEED.get(preset_mode)
        if level is None:
            _LOGGER.warning("Unknown preset mode: %s", preset_mode)
            return
        if not self.coordinator.data.power:
            await self.coordinator.async_set_power(True)
        await self.coordinator.async_set_manual_speed(level)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Map swing_mode to Komfovent season register (REG_SEASON)."""
        value = SEASON_OPTION_TO_VALUE.get(swing_mode)
        if value is None:
            _LOGGER.warning("Unknown season (swing) option: %s", swing_mode)
            return
        await self.coordinator.async_set_season(value)
