# Zentrale Konstanten der Hüllhorst-Abfuhrtermine-Integration.

from __future__ import annotations

DOMAIN = "huellhorst_abfuhr"

# Quelle: Service-Detail-Seite mit aktuellen Kalender-Import-Links.
# Wird einmal pro Tag gescraped, um bei Jahreswechsel automatisch den
# neuen ICS-Link zu finden – der `id`-Parameter wechselt jährlich.
SERVICE_DETAIL_URL = (
    "https://serviceportal.huellhorst.de/detail/-/vr-bis-detail/dienstleistung/10882/show"
)

# Plattformen, die diese Integration registriert
PLATFORMS = ["sensor", "calendar"]

# Polling: ICS einmal pro Tag (Termine ändern sich praktisch nie unterm Jahr)
DEFAULT_SCAN_INTERVAL_HOURS = 24

# Option-Keys
CONF_INCLUDE_REMINDERS = "include_reminders"  # ICS-Variante "mit Erinnerungen"

# Mapping interner Slug ←→ ICS-Summary. Wird genutzt, um stabile
# entity_ids zu vergeben, auch wenn die Gemeinde mal Schreibweisen ändert.
WASTE_TYPE_SLUGS: dict[str, str] = {
    "Restabfalltonne": "restmuell",
    "Biotonne": "bio",
    "(Sommer-)Biotonne": "bio",  # Sommer-Variante: gleicher Slug → ein Sensor
    "Papiertonne": "papier",
    "Gelbe Tonne": "gelbe_tonne",
    "Gelbe Container (1.1 cbm)": "gelbe_container",
    "Sperrmüllabfuhr (Anmeldung erforderlich)": "sperrmuell",
    "Sondermüll (Wertstoffhof)": "sondermuell",
}

# Default-Icons je Müllart (Fallback wenn icons.json den Slug nicht kennt)
WASTE_TYPE_ICONS: dict[str, str] = {
    "restmuell": "mdi:trash-can",
    "bio": "mdi:leaf",
    "papier": "mdi:newspaper",
    "gelbe_tonne": "mdi:recycle",
    "gelbe_container": "mdi:recycle-variant",
    "sperrmuell": "mdi:sofa",
    "sondermuell": "mdi:biohazard",
}
