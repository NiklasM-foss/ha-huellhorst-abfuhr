# Abfuhrtermine Hüllhorst – Home Assistant Integration

HACS-kompatible Custom-Integration, die die Müllabfuhrtermine der Gemeinde
Hüllhorst (EMiL AöR) automatisch aus dem offiziellen Service-Portal lädt
und als Sensoren + Kalender in Home Assistant bereitstellt.

**Killer-Feature:** Der ICS-Link im Service-Portal enthält einen Jahres-
spezifischen Token (`id=...`). Diese Integration scrapt 1× pro Tag die
Service-Detail-Seite und erkennt den neuen Link automatisch – beim
Jahreswechsel hat HA also direkt die Termine für das neue Jahr drin,
ohne manuelle Pflege.

## Status

Version 1.0.0 – getestet gegen den 2026er-Kalender.

## Stack

- Home Assistant ≥ 2024.4
- Stdlib + aiohttp (keine externen Python-Dependencies)
- ICS-Parsing inline (sehr simples VCALENDAR-Format)

## Quellen

- Service-Detail-Seite: <https://serviceportal.huellhorst.de/detail/-/vr-bis-detail/dienstleistung/10882/show>
- ICS-Endpoint: `https://webportal.owl-it.de/link?id=…` (Redirect zu
  `serviceportal.huellhorst.de/documents/d/guest/kalenderimport-abfuhrtermine-hullhorst-<JAHR>`)

## Verzeichnisstruktur

```
custom_components/huellhorst_abfuhr/
├── __init__.py          # Setup-Einstiegspunkt
├── api.py               # Scraper + ICS-Parser
├── calendar.py          # Calendar-Entity
├── config_flow.py       # UI-Dialog inkl. Options-Flow
├── const.py             # Konstanten + Müllart-Mapping
├── coordinator.py       # 1×/Tag-Polling, Gruppierung nach Müllart
├── icons.json           # Entity-Icons je Müllart
├── manifest.json
├── sensor.py            # Nächste-Abfuhr-Sensoren (gesamt + pro Müllart)
├── strings.json
└── translations/
    ├── de.json
    └── en.json
hacs.json
README.md
```

## Installation

### Via HACS

1. HACS → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. URL `https://github.com/NiklasM-foss/ha-huellhorst-abfuhr` eintragen,
   Kategorie *Integration*
3. „Abfuhrtermine Hüllhorst" installieren, HA neu starten
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen →
   Abfuhrtermine Hüllhorst*

### Manuell

`custom_components/huellhorst_abfuhr/` ins HA-Configdir kopieren,
HA neu starten.

## Entitäten

- `sensor.naechste_abfuhr` – nächste Abfuhr überhaupt (Timestamp), mit
  Attribut `art` (z. B. „Biotonne").
- `sensor.naechste_abfuhr_<art>` – pro Müllart ein Sensor (Restabfalltonne,
  Biotonne, Papiertonne, Gelbe Tonne, Gelbe Container, Sperrmüll).
- `calendar.abfuhrtermine` – kompletter Jahreskalender als HA-Kalender,
  z. B. für Lovelace-Calendar-Cards.

## Optionen

*Integration → Konfigurieren*:

- **Erinnerungen aus dem ICS übernehmen** – nimmt die Kalender-Variante
  „mit Erinnerungen" (enthält `VALARM`-Einträge). Default aus.

## Beispiel-Automation

```yaml
# Abends vor Abfuhr-Tag erinnern
alias: Müll rausstellen
trigger:
  - platform: template
    value_template: >
      {{ (as_timestamp(states('sensor.naechste_abfuhr')) - now().timestamp())
         < 14*3600
         and as_timestamp(states('sensor.naechste_abfuhr')) - now().timestamp() > 13*3600 }}
action:
  - service: notify.mobile_app_phone
    data:
      title: "Morgen Abfuhr"
      message: >
        Morgen wird {{ state_attr('sensor.naechste_abfuhr', 'art') }}
        abgeholt – heute Abend rausstellen.
```

## Aktualisierungsverhalten

- ICS-Abruf und Page-Scrape: alle 24 h (im Coordinator hartcodiert –
  Abfuhrtermine ändern sich unterm Jahr nicht).
- Beim Jahreswechsel: spätestens 24 h nach Online-Verfügbarkeit des neuen
  Kalenders übernimmt die Integration automatisch.

## Letzte Änderungen

- 1.0.0 – Initiale Release.

## Lizenz

MIT
