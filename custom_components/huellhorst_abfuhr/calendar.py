"""
Calendar-Plattform: macht den Abfuhrkalender als HA-Kalender verfügbar.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AbfuhrCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AbfuhrCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AbfuhrCalendar(coordinator, entry)])


class AbfuhrCalendar(CoordinatorEntity[AbfuhrCoordinator], CalendarEntity):
    """Ein einziger Kalender mit allen Abfuhrterminen des Jahres."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:trash-can-outline"

    def __init__(
        self, coordinator: AbfuhrCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "Abfuhrtermine"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Abfuhrtermine Hüllhorst",
            "manufacturer": "EMiL AöR / Gemeinde Hüllhorst",
            "model": "ICS-Kalender",
        }

    @property
    def event(self) -> CalendarEvent | None:
        ev = self.coordinator.next_event_any()
        return _to_event(ev) if ev else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        events: list[Any] = (self.coordinator.data or {}).get("events", [])
        return [
            _to_event(e)
            for e in events
            if e.end >= start_date and e.start <= end_date
        ]


def _to_event(ev: Any) -> CalendarEvent:
    return CalendarEvent(
        start=ev.start,
        end=ev.end,
        summary=ev.summary,
    )
