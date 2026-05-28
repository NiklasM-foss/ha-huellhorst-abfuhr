"""
Setup-Einstiegspunkt der Hüllhorst-Abfuhrtermine-Integration.

Pro ConfigEntry wird ein Coordinator angelegt, der den ICS-Link von der
Service-Detail-Seite scrapt, das ICS lädt, parst und an Sensoren + Kalender
weiterreicht.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AbfuhrPortalClient
from .const import DOMAIN, PLATFORMS
from .coordinator import AbfuhrCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Wird beim Laden des Entries aufgerufen."""
    session = async_get_clientsession(hass)
    client = AbfuhrPortalClient(session)
    coordinator = AbfuhrCoordinator(hass, entry, client)

    # Erster Refresh synchron – scheitert er, scheitert das Setup
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Reload, wenn der User Options ändert (z.B. „mit Erinnerungen")
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Triggert einen Reload bei Options-Änderung."""
    await hass.config_entries.async_reload(entry.entry_id)
