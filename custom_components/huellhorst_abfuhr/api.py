"""
Client für das Hüllhorster Service-Portal.

Zwei Aufgaben:

1. Den aktuellen ICS-Link von der Service-Detail-Seite scrapen. Der
   `id`-Parameter im `webportal.owl-it.de/link?id=...` wechselt jedes Jahr,
   daher kann er nicht hardcoded werden. Die Detail-Seite verlinkt aber
   immer auf die aktuelle Variante – Scraping ist deshalb der robusteste
   Weg, um auch über Jahreswechsel hinweg „automatisch" aktuell zu bleiben.

2. Den gefundenen ICS-Inhalt herunterladen und die VEVENTs parsen. Statt
   einer Extra-Dependency (`icalendar`) parsen wir das simple VEVENT-Format
   selbst – BEGIN/END-Token, DTSTART, SUMMARY reichen aus.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .const import SERVICE_DETAIL_URL

_LOGGER = logging.getLogger(__name__)

# Pattern für die ICS-Import-URLs auf der Detail-Seite. Akzeptiert alles
# was nach `id=` an Base64URL-Zeichen kommt.
_LINK_RE = re.compile(
    r"https://webportal\.owl-it\.de/link\?id=[A-Za-z0-9_\-]+"
)

# User-Agent: Das Portal antwortet auf Default-Python-UA mit 403
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)


@dataclass
class AbfuhrEvent:
    """Ein einzelner Abfuhr-Termin aus dem ICS-Feed."""

    summary: str
    start: datetime
    end: datetime


class AbfuhrPortalClient:
    """Asynchroner Client – wird vom Coordinator pro Refresh genutzt."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_discover_ics_links(self) -> tuple[str | None, str | None]:
        """
        Holt die Detail-Seite und extrahiert beide ICS-Links (ohne/mit
        Erinnerungen). Reihenfolge auf der Seite: ohne, dann mit.

        Liefert (link_ohne, link_mit). Einer oder beide können None sein,
        wenn die Seite mal kaputt ist – der Coordinator entscheidet dann,
        ob er einen alten gecachten Link weiterverwendet.
        """
        async with self._session.get(
            SERVICE_DETAIL_URL,
            headers={"User-Agent": _UA},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            resp.raise_for_status()
            html = await resp.text()

        matches = _LINK_RE.findall(html)
        # Eindeutige Reihenfolge bewahren (set würde shufflen)
        seen: list[str] = []
        for m in matches:
            if m not in seen:
                seen.append(m)

        link_ohne = seen[0] if len(seen) >= 1 else None
        link_mit = seen[1] if len(seen) >= 2 else None
        _LOGGER.debug(
            "ICS-Links gefunden: ohne=%s mit=%s", bool(link_ohne), bool(link_mit)
        )
        return link_ohne, link_mit

    async def async_fetch_ics(self, url: str) -> str:
        """Lädt den ICS-Inhalt als Text. Folgt dem 302 vom owl-it-Link."""
        async with self._session.get(
            url,
            headers={"User-Agent": _UA},
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            return await resp.text()


def parse_ics(text: str) -> list[AbfuhrEvent]:
    """
    Parser für das simple VCALENDAR/VEVENT-Format, das das Portal liefert.

    Erwartet pro Event mindestens DTSTART, DTEND und SUMMARY. Zeiten kommen
    als Local-Time ohne TZ (z. B. `20260105T063000`). Wir nehmen Europe/Berlin
    als Annahme – passt, weil die Gemeinde dort liegt.
    """
    events: list[AbfuhrEvent] = []
    current: dict[str, str] = {}
    in_event = False

    for raw in text.splitlines():
        line = raw.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
            continue
        if line == "END:VEVENT":
            in_event = False
            try:
                summary = current.get("SUMMARY", "").strip()
                start = _parse_ics_datetime(current["DTSTART"])
                end = _parse_ics_datetime(
                    current.get("DTEND", current["DTSTART"])
                )
                if summary:
                    events.append(AbfuhrEvent(summary=summary, start=start, end=end))
            except (KeyError, ValueError) as err:
                _LOGGER.debug("Event übersprungen: %s", err)
            continue
        if not in_event or ":" not in line:
            continue
        # Property-Zeile: KEY[;PARAMS]:VALUE  – Params vor `:` ignorieren wir
        key_part, _, value = line.partition(":")
        key = key_part.split(";", 1)[0]
        current[key] = value

    events.sort(key=lambda e: e.start)
    return events


def _parse_ics_datetime(value: str) -> datetime:
    """
    Parst `20260105T063000` oder `20260105` (DATE-only).

    Lokale Zeit wird als Europe/Berlin-Naiv interpretiert und zu UTC-aware
    konvertiert; HA stellt sie korrekt dar.
    """
    value = value.strip()
    # DATE-only
    if "T" not in value:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
    # DATETIME mit lokaler Zeit
    naive = datetime.strptime(value, "%Y%m%dT%H%M%S")
    # Hüllhorst liegt in Europe/Berlin → grob als UTC+1 / UTC+2 behandeln.
    # Wir lassen es aware in UTC enden, indem wir es als „local Berlin" markieren.
    try:
        from zoneinfo import ZoneInfo

        return naive.replace(tzinfo=ZoneInfo("Europe/Berlin"))
    except Exception:  # noqa: BLE001
        # Fallback: einfach UTC – beim Anzeigen 1–2 h verschoben, aber
        # für Tagesgenauigkeit der Abfuhrtermine völlig ausreichend.
        return naive.replace(tzinfo=timezone.utc)
