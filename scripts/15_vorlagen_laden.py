#!/usr/bin/env python3
"""Schritt 15 — Sitzungsvorlagen zu Punkten ohne Beschluss herunterladen.

Zu einem Tagesordnungspunkt ohne Beschluss stand bisher nur der Titel und ein
Verweis. „Information über die Fortschreibung der Elternbeiträge in
Kindertageseinrichtungen" — was darin steht, blieb offen, obwohl es eine
Sitzungsvorlage dazu gibt.

**Geladen wird bewusst nur diese Teilmenge.** Im Bestand hängen 367 Dokumente
an Tagesordnungspunkten; die allermeisten gehören zu Punkten, deren Beschluss
ohnehin im Wortlaut dasteht. Dort fehlt nichts. Die rund vierzig Vorlagen
ohne Beschluss sind die Stellen, an denen die Ausgabe sonst schweigt.

Der zweite Grund ist Vorsicht: Beschlussprotokolle sind knapp und
formalisiert, Sitzungsvorlagen enthalten Sachverhaltsdarstellungen mit
Flurstücken, Beträgen und gelegentlich Namen. Das Projekt sagt zu, keine
Anschriften und keine Klarnamen ohne Funktion wiederzugeben. An vierzig
Dokumenten lässt sich prüfen, ob das trägt; an 367 auf einmal nicht.

Ergebnis: data/vorlagen/SV-000-JJJJ.pdf

    uv run --with requests python scripts/15_vorlagen_laden.py
"""
from __future__ import annotations

import csv
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


def offene_vorlagen() -> dict[str, str]:
    """Vorlagennummer → URL, für Punkte ohne eigenen Beschluss.

    Beschlossen ist, was in `data/csv/beschluesse.csv` steht — der Tabelle,
    die Schritt 07 aus den Protokollen schreibt. Sie ist die einzige Quelle,
    die genau das enthaelt: eine Zeile je protokolliertem Beschluss.

    Zwei falsche Quellen davor, beide beim Gegenlesen aufgefallen:

    * `vorgaenge.json`, Feld `letzte` — das ist das **Datum** der juengsten
      Station und steht bei allen 519 Vorgaengen. Daran gemessen galt jeder
      Punkt als beschlossen.
    * `vorgaenge.json` ueberhaupt — es fuehrt nur einen Teil der Vorlagen.
      SV-101/2026 hat einen einstimmigen Beschluss und fehlt dort trotzdem.
    """
    topmap = json.loads((DATEN / "topmap.json").read_text(encoding="utf-8"))

    beschlossen: set[str] = set()
    with (DATEN / "csv" / "beschluesse.csv").open(encoding="utf-8-sig") as f:
        for zeile in csv.DictReader(f, delimiter=";"):
            if zeile.get("vorlage"):
                beschlossen.add(zeile["vorlage"])

    offen: dict[str, str] = {}
    for p in topmap:
        nr = p.get("vorlage")
        if not nr or nr in beschlossen or nr in offen:
            continue
        for d in p.get("dokumente") or []:
            # Nur die Sitzungsvorlage selbst, nicht Anlagen und Planteile:
            # Der Sachverhalt steht dort, die Anlagen sind Karten und Listen.
            if d.get("titel", "").startswith("Sitzungsvorlage"):
                offen[nr] = d["url"]
                break
    return offen


def main() -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    offen = offene_vorlagen()

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

    print(f"Sitzungsvorlagen ohne Beschluss — neu: {neu}, "
          f"bereits vorhanden: {vorhanden}, fehlgeschlagen: {fehler}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
