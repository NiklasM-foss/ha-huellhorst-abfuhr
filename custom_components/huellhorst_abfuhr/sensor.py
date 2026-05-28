"""
Sensor-Plattform.

Erzeugt pro entdeckter Müllart einen Sensor mit dem nächsten Abfuhrtermin
als `device_class=timestamp`, plus einen aggregierten „Nächste Abfuhr"-Sensor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WASTE_TYPE_ICONS
from .coordinator import AbfuhrCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AbfuhrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [NextAbfuhrAnySensor(coordinator, entry)]

    # Pro Müllart-Slug, der im aktuellen ICS auftaucht, einen Sensor anlegen.
    # Spätere Müllarten (z.B. ein neuer Typ Mitte Jahres) brauchen einen Reload –
    # ist aber selten genug, dass das ok ist.
    slugs = list((coordinator.data or {}).get("by_slug", {}).keys())
    for slug in sorted(slugs):
        entities.append(NextAbfuhrSlugSensor(coordinator, entry, slug))

    async_add_entities(entities)


class _Base(CoordinatorEntity[AbfuhrCoordinator], SensorEntity):
    """Basis: gemeinsame Device-Info."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: AbfuhrCoordinator, entry: ConfigEntry, key: str):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Abfuhrtermine Hüllhorst",
            "manufacturer": "EMiL AöR / Gemeinde Hüllhorst",
            "model": "ICS-Kalender",
        }


class NextAbfuhrAnySensor(_Base):
    """Nächste Abfuhr überhaupt – egal welcher Typ."""

    _attr_translation_key = "next_any"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: AbfuhrCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_any")
        self._attr_name = "Nächste Abfuhr"

    @property
    def native_value(self) -> datetime | None:
        ev = self.coordinator.next_event_any()
        return ev.start if ev else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        ev = self.coordinator.next_event_any()
        if not ev:
            return None
        return {
            "art": ev.summary,
            "end": ev.end.isoformat(),
        }


class NextAbfuhrSlugSensor(_Base):
    """Nächste Abfuhr einer bestimmten Müllart (Restmüll, Bio, …)."""

    def __init__(
        self, coordinator: AbfuhrCoordinator, entry: ConfigEntry, slug: str
    ) -> None:
        super().__init__(coordinator, entry, f"next_{slug}")
        self._slug = slug
        # Lesbarer Name: nimm den Original-SUMMARY-String des ersten Events
        events = (coordinator.data or {}).get("by_slug", {}).get(slug, [])
        readable = events[0].summary if events else slug.replace("_", " ").title()
        self._attr_name = f"Nächste Abfuhr {readable}"
        self._attr_translation_key = f"next_{slug}"
        self._attr_icon = WASTE_TYPE_ICONS.get(slug, "mdi:trash-can-outline")

    @property
    def native_value(self) -> datetime | None:
        ev = self.coordinator.next_event_for_slug(self._slug)
        return ev.start if ev else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        ev = self.coordinator.next_event_for_slug(self._slug)
        if not ev:
            return None
        return {
            "summary": ev.summary,
            "end": ev.end.isoformat(),
        }
