#!/usr/bin/env python3
"""Schritt 15 — die Sitzungsvorlagen herunterladen.

Die Vorlage enthaelt den Abschnitt „Zum Sachverhalt": warum die Verwaltung
etwas vorschlaegt. Das ist oft aufschlussreicher als der Beschluss selbst —
„Fuer das Kindergartenjahr 2026/2027 empfehlen die Kirchen und Kommunalen
Landesverbaende eine Erhoehung der Elternbeitraege um 4,5 %" steht in keinem
Protokoll.

Zuerst wurden nur die Vorlagen ohne Beschluss geladen, weil dort sonst gar
nichts stand. Die Pruefung an 64 Dokumenten — 39 ohne Beschluss, 25 als
Stichprobe mit — fand keine Anschriften von Privatpersonen, keine
Bankverbindungen, keine Kontaktdaten; die gefundenen Namen traten samtlich in
amtlicher Funktion auf. Das ist erwartbar: Was im oeffentlichen
Ratsinformationssystem steht, hat die Stadt selbst als veroeffentlichungs-
faehig eingestuft. Schutzbeduerftiges liegt in nichtoeffentlichen Vorlagen,
die dort gar nicht erscheinen.

Seither werden alle geladen. Die laufende Kontrolle uebernimmt
`pruefe_personendaten` in `pruefen.py`: Bei mehreren hundert Dokumenten, die
jede Woche mehr werden, kann niemand mehr von Hand nachsehen.

Ergebnis: data/vorlagen/SV-000-JJJJ.pdf

    uv run --with requests python scripts/15_vorlagen_laden.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

BASIS = Path(__file__).resolve().parent.parent
DATEN = BASIS / "data"
ZIEL = DATEN / "vorlagen"

# Dieselbe Pause wie beim Laden der Protokolle. Die Abfragen sind bewusst
# langsam gehalten, damit der Server der Stadt nicht belastet wird.
PAUSE = 0.2

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def dateiname(vorlage: str) -> str:
    """„SV-132/2026" → „SV-132-2026.pdf"."""
    return re.sub(r"[^A-Za-z0-9-]+", "-", vorlage) + ".pdf"


def alle_vorlagen() -> dict[str, str]:
    """Vorlagennummer → URL der Sitzungsvorlage.

    Nur die Vorlage selbst, nicht die Anlagen: Der Sachverhalt steht dort;
    Planteile, Umweltberichte und Listen bleiben verlinkt, aber ungelesen.
    """
    topmap = json.loads((DATEN / "topmap.json").read_text(encoding="utf-8"))
    gefunden: dict[str, str] = {}
    for p in topmap:
        nr = p.get("vorlage")
        if not nr or nr in gefunden:
            continue
        for d in p.get("dokumente") or []:
            if d.get("titel", "").startswith("Sitzungsvorlage"):
                gefunden[nr] = d["url"]
                break
    return gefunden


def main() -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    offen = alle_vorlagen()

    s = requests.Session()
    s.headers["User-Agent"] = UA

    neu = vorhanden = fehler = 0
    for nr, url in sorted(offen.items()):
        ziel = ZIEL / dateiname(nr)
        if ziel.exists():
            vorhanden += 1
            continue
        try:
            antwort = s.get(url, timeout=60)
            antwort.raise_for_status()
            ziel.write_bytes(antwort.content)
            neu += 1
        except Exception as f:  # noqa: BLE001
            print(f"  Fehler: {ziel.name}: {f}", file=sys.stderr)
            fehler += 1
        time.sleep(PAUSE)

    print(f"Sitzungsvorlagen — neu: {neu}, "
          f"bereits vorhanden: {vorhanden}, fehlgeschlagen: {fehler}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
