"""
DataUpdateCoordinator – scrapt 1× pro Tag die Detail-Seite, lädt das ICS und
hält die geparsten Events im Cache. Bei Jahreswechsel findet der Scrape den
neuen Link automatisch.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AbfuhrEvent, AbfuhrPortalClient, parse_ics
from .const import (
    CONF_INCLUDE_REMINDERS,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    WASTE_TYPE_SLUGS,
)

_LOGGER = logging.getLogger(__name__)


class AbfuhrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Lädt die Abfuhrtermine und gruppiert sie nach Müllart."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AbfuhrPortalClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS),
        )
        self._client = client
        self._entry = entry
        # Letzter erfolgreich genutzter ICS-Link – als Fallback, wenn der
        # Scrape mal scheitert (Server-Hickup, HTML-Änderung etc.)
        self._last_ics_url: str | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            link_ohne, link_mit = await self._client.async_discover_ics_links()

            # User-Option: nimmt er den Kalender „mit Erinnerungen" oder ohne
            want_reminders = self._entry.options.get(CONF_INCLUDE_REMINDERS, False)
            preferred = link_mit if want_reminders else link_ohne
            fallback = link_ohne if want_reminders else link_mit

            ics_url = preferred or fallback or self._last_ics_url
            if not ics_url:
                raise UpdateFailed(
                    "Konnte keinen ICS-Link auf der Detail-Seite finden."
                )
            self._last_ics_url = ics_url

            ics_text = await self._client.async_fetch_ics(ics_url)
            events = parse_ics(ics_text)
            if not events:
                raise UpdateFailed("ICS lieferte keine Events.")

            # Pro bekanntem Müllart-Slug die Liste der Events sammeln
            by_slug: dict[str, list[AbfuhrEvent]] = {}
            for ev in events:
                slug = _slug_for_summary(ev.summary)
                by_slug.setdefault(slug, []).append(ev)

            return {
                "events": events,
                "by_slug": by_slug,
                "ics_url": ics_url,
            }
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Abruf fehlgeschlagen: {err}") from err

    def next_event_for_slug(self, slug: str) -> AbfuhrEvent | None:
        """Hilfsmethode: nächster anstehender Termin einer Müllart."""
        now = datetime.now(timezone.utc)
        events = (self.data or {}).get("by_slug", {}).get(slug, [])
        return next(
            (
                e
                for e in events
                if e.start.astimezone(timezone.utc) >= now
                or e.end.astimezone(timezone.utc) >= now
            ),
            None,
        )

    def next_event_any(self) -> AbfuhrEvent | None:
        """Nächster anstehender Termin – unabhängig von der Müllart."""
        now = datetime.now(timezone.utc)
        events: list[AbfuhrEvent] = (self.data or {}).get("events", [])
        return next(
            (e for e in events if e.start.astimezone(timezone.utc) >= now),
            None,
        )


def _slug_for_summary(summary: str) -> str:
    """
    Mappt eine ICS-SUMMARY („Restabfalltonne") auf einen stabilen Slug.
    Unbekannte Summaries werden grob normalisiert.
    """
    if summary in WASTE_TYPE_SLUGS:
        return WASTE_TYPE_SLUGS[summary]
    # Fallback: lowercase, Sonderzeichen weg
    slug = "".join(c.lower() if c.isalnum() else "_" for c in summary).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "unbekannt"
