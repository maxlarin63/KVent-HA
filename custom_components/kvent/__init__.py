"""KVent – Home Assistant integration for Komfovent C4 ventilation units."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INTEGRATION_VERSION,
)
from .coordinator import KVentCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    "fan",
    "climate",
    "sensor",
    "binary_sensor",
    "select",
    "number",
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KVent from a config entry."""
    host: str = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    port: int = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT))
    scan_interval: int = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    desired_title = f"KVent C4 v{INTEGRATION_VERSION} ({host})"
    if entry.title != desired_title:
        hass.config_entries.async_update_entry(entry, title=desired_title)

    coordinator = KVentCoordinator(hass, host, port, scan_interval)

    # Initial refresh — raises ConfigEntryNotReady on failure (HA handles retry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a KVent config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: KVentCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_disconnect()
    return unload_ok
