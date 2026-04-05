"""Config flow for KVent (Komfovent C4)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import (
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .modbus import KVentModbusClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=3600)
        ),
    }
)


async def _test_connection(host: str, port: int) -> str | None:
    """Try to connect and read one register block.  Returns error key or None."""
    client = KVentModbusClient(host, port)
    try:
        await asyncio.wait_for(client.connect(), timeout=10)
        await asyncio.wait_for(client.read_registers(1000, 2), timeout=5)
        return None
    except TimeoutError:
        return "cannot_connect"
    except OSError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        return "unknown"
    finally:
        await client.disconnect()


class KVentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the KVent config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST].strip()
            port: int = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Prevent duplicate entries for the same host:port
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            error_key = await _test_connection(host, port)
            if error_key:
                errors["base"] = error_key
            else:
                return self.async_create_entry(
                    title=f"Komfovent C4 ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
