"""DataUpdateCoordinator for KVent (Komfovent C4)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_OVR_MINUTES,
    DOMAIN,
    MODE_MANUAL,
    REG_MODE,
    REG_OVR_ENABLE,
    REG_OVR_TIME,
    REG_SEASON,
    REG_SETPOINT,
    REG_SPEED_MANUAL,
    REG_STATUS,
    SPEED_BOOST,
    SPEED_STANDBY,
)
from .modbus import KVentData, KVentModbusClient, encode_setpoint_register

_LOGGER = logging.getLogger(__name__)


class KVentCoordinator(DataUpdateCoordinator[KVentData]):
    """Polls all KVent registers on a fixed interval; exposes write helpers."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._client = KVentModbusClient(host, port)

    # ── Coordinator lifecycle ─────────────────────────────────────────────────

    async def async_disconnect(self) -> None:
        """Cleanly close the Modbus TCP connection."""
        await self._client.disconnect()

    # ── Poll ──────────────────────────────────────────────────────────────────

    async def _async_update_data(self) -> KVentData:
        """Fetch register snapshot; reconnect once on failure."""
        prev = self.data
        try:
            new = await asyncio.wait_for(self._client.async_read_all(), timeout=20.0)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("KVent poll failed (%s), retrying after reconnect", err)
            try:
                await self._client.disconnect()
                new = await asyncio.wait_for(self._client.async_read_all(), timeout=20.0)
            except Exception as retry_err:
                raise UpdateFailed(f"Modbus read failed: {retry_err}") from retry_err
        # C4 firmware briefly reports REG_STATUS=0 while fans keep operating and no
        # stop code is set. Trust REG_FANS_STATUS as the actual run-state in that case.
        if not new.power and new.fans_running and new.alarm_stop_code == 0:
            _LOGGER.debug(
                "KVent: REG_STATUS=0 ignored — fans still operating (snapshot=%s)", new
            )
            new = replace(new, power=True)
        # Diagnostic for off/on cycling: surface full snapshot at every power flip.
        if prev is not None and prev.power != new.power:
            _LOGGER.warning(
                "KVent power transition %s→%s, snapshot=%s",
                prev.power,
                new.power,
                new,
            )
        return new

    # ── Write helpers ─────────────────────────────────────────────────────────

    async def async_set_power(self, on: bool) -> None:
        """Write power on/off then refresh."""
        await self._client.write_register(REG_STATUS, 1 if on else 0)
        await self.async_request_refresh()

    async def async_set_season(self, value: int) -> None:
        """Write season register (0=summer, 1=winter) then refresh."""
        await self._client.write_register(REG_SEASON, value)
        await self.async_request_refresh()

    async def async_set_auto_mode(self) -> None:
        """Switch to Auto ventilation mode then refresh."""
        await self._client.write_register(REG_MODE, 1)
        await self.async_request_refresh()

    async def async_set_manual_speed(self, level: int) -> None:
        """Apply manual ventilation: writes 1–3 to 1100; Standby = power off; Boost = OVR."""
        if level in (1, 2, 3):
            await self._client.write_register(REG_MODE, MODE_MANUAL)
            await self._client.write_register(REG_SPEED_MANUAL, level)
        elif level == SPEED_STANDBY:
            await self._client.write_register(REG_STATUS, 0)
        elif level == SPEED_BOOST:
            await self._client.write_register(REG_MODE, MODE_MANUAL)
            await self._client.write_register(REG_OVR_ENABLE, 1)
            await self._client.write_register(REG_OVR_TIME, DEFAULT_OVR_MINUTES)
        else:
            _LOGGER.warning("KVent: ignored invalid manual level %s", level)
            return
        await self.async_request_refresh()

    async def async_set_setpoint(self, celsius: float) -> None:
        """Write temperature setpoint (register 1201, R/W) then refresh."""
        await self._client.write_register(REG_SETPOINT, encode_setpoint_register(celsius))
        await self.async_request_refresh()

    async def async_write_register(self, addr: int, value: int) -> None:
        """Low-level single-register write (for future expansion)."""
        await self._client.write_register(addr, value)
        await self.async_request_refresh()
