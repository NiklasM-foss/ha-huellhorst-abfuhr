"""
Config-Flow.

Es gibt nur eine sinnvolle Konfiguration (gemeindeweite Abfuhrtermine
Hüllhorst), daher nur ein „Bestätigen"-Schritt. Optionen (mit/ohne
Erinnerungen) werden über den Options-Flow nachträglich gepflegt.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AbfuhrPortalClient
from .const import CONF_INCLUDE_REMINDERS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HuellhorstAbfuhrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initiale Einrichtung – testet, ob die Detail-Seite einen ICS-Link liefert."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "HuellhorstAbfuhrOptionsFlow":
        return HuellhorstAbfuhrOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        # Nur eine Instanz: zweite Konfiguration verhindern
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = AbfuhrPortalClient(session)
            try:
                link_ohne, link_mit = await client.async_discover_ics_links()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Detail-Seite nicht erreichbar")
                errors["base"] = "cannot_connect"
            else:
                if not (link_ohne or link_mit):
                    errors["base"] = "no_ics_link"
                else:
                    return self.async_create_entry(
                        title="Abfuhrtermine Hüllhorst",
                        data={},
                        options={
                            CONF_INCLUDE_REMINDERS: user_input.get(
                                CONF_INCLUDE_REMINDERS, False
                            ),
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Optional(CONF_INCLUDE_REMINDERS, default=False): bool}
            ),
            errors=errors,
        )


class HuellhorstAbfuhrOptionsFlow(config_entries.OptionsFlow):
    """Nachträgliche Option: ICS-Variante mit/ohne Erinnerungen."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options.get(CONF_INCLUDE_REMINDERS, False)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Optional(CONF_INCLUDE_REMINDERS, default=current): bool}
            ),
        )
