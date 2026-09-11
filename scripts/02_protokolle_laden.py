#!/usr/bin/env python3
"""Schritt 2 — die öffentlichen Beschlussprotokolle herunterladen.

Protokolle hängen nicht an den Vorlagen, sondern an den Sitzungsseiten. Sie
erscheinen üblicherweise wenige Tage nach der Sitzung.

Ergebnis: data/protokolle/JJJJ-MM-TT_<gremium>.pdf

    uv run --with requests python scripts/02_protokolle_laden.py
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
ZIEL = DATEN / "protokolle"
PAUSE = 0.2

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def kurzname(titel: str) -> str:
    """Gremiumsname auf etwas kürzen, das als Dateiname taugt."""
    # Achtung: Hier wird bewusst am ersten Komma geschnitten, obwohl das
    # den Gremiumsnamen verkuerzt. Die bereits geladenen Protokolle auf
    # der Platte tragen genau diese Namen; eine Aenderung wuerde sie
    # unauffindbar machen. Fuer die Anzeige gibt es gremium().
    name = re.sub(r",.*", "", titel)
    name = re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", "-", name).strip("-")
    return name[:48]


def main() -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    sitzungen = json.loads((DATEN / "sitzungen.json").read_text(encoding="utf-8"))

    s = requests.Session()
    s.headers["User-Agent"] = UA

    neu = vorhanden = fehler = 0
    for sitzung in sitzungen:
        for nr, url in enumerate(sitzung["protokolle"], 1):
            suffix = "" if nr == 1 else f"_{nr}"
            ziel = ZIEL / f"{sitzung['start'][:10]}_{kurzname(sitzung['titel'])}{suffix}.pdf"
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

    print(f"Protokolle — neu: {neu}, bereits vorhanden: {vorhanden}, "
          f"fehlgeschlagen: {fehler}", file=sys.stderr)


if __name__ == "__main__":
    main()
