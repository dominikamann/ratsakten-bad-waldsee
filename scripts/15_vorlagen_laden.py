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

    uv run --with requests --with pypdf python scripts/15_vorlagen_laden.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textwerk import paket_abschnitt, pdf_text

BASIS = Path(__file__).resolve().parent.parent
DATEN = BASIS / "data"
ZIEL = DATEN / "vorlagen"
PAKETE = DATEN / "pakete"

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


def paketname(url: str) -> str:
    """Ein eindeutiger Dateiname fuer ein Gesamtpaket.

    Im Ratsinformationssystem heisst *jedes* Paket „Gesamtes_Sitzungspaket.pdf";
    unterschieden werden sie allein durch die Kennung davor. Der letzte
    Pfadteil taugt deshalb nicht als Dateiname — beim ersten Versuch
    ueberschrieben sich alle Pakete gegenseitig, und der Sachverhalt wurde aus
    dem Paket einer fremden Sitzung geschnitten.
    """
    teile = [x for x in url.split("/") if x]
    kennung = teile[-2] if len(teile) >= 2 else "paket"
    return re.sub(r"[^A-Za-z0-9_-]+", "", kennung)[:40] + ".pdf"


def vorlagen_ohne_pdf() -> dict[str, str]:
    """Vorlagennummer → URL des Gesamtpakets, fuer Vorlagen ohne eigene PDF.

    Sechs von 283 Vorlagen sind im Ratsinformationssystem nicht einzeln
    veroeffentlicht — darunter die Bewerbung um die Landesgartenschau und der
    Erwerb einer Skulptur fuer das Verwaltungsgebaeude. Ihr Sachverhalt steht
    trotzdem im Netz, nur eben im Gesamtpaket der Sitzung. Ohne diesen Weg
    zeigt die Ausgabe bei ihnen die blosse Vorlagennummer und sonst nichts,
    obwohl die Auskunft oeffentlich abrufbar ist.
    """
    topmap = json.loads((DATEN / "topmap.json").read_text(encoding="utf-8"))
    sitzungen = json.loads((DATEN / "sitzungen.json").read_text(encoding="utf-8"))

    eigene = {p["vorlage"] for p in topmap if p.get("vorlage")
              and any(d.get("titel", "").startswith("Sitzungsvorlage")
                      for d in (p.get("dokumente") or []))}
    pakete = {x["url"]: u for x in sitzungen for u in x["pdfs"]
              if "Gesamtes_Sitzungspaket" in u}

    offen: dict[str, str] = {}
    for p in topmap:
        nr = p.get("vorlage")
        if nr and nr not in eigene and nr not in offen and p["url"] in pakete:
            offen[nr] = pakete[p["url"]]
    return offen


def aus_paketen_nachtragen(s: requests.Session) -> tuple[int, int]:
    """Fehlende Vorlagen aus dem Gesamtpaket der Sitzung nachtragen.

    Abgelegt wird der herausgeschnittene Abschnitt als Textdatei neben den
    Vorlagen. So bleibt der Ausgabenbauer unveraendert: Er liest die PDF,
    wenn es sie gibt, und sonst diese Datei.
    """
    offen = vorlagen_ohne_pdf()
    if not offen:
        return 0, 0
    PAKETE.mkdir(parents=True, exist_ok=True)

    nachgetragen = leer = 0
    for nr, url in sorted(offen.items()):
        ziel = ZIEL / (dateiname(nr)[:-4] + ".txt")
        if ziel.exists():
            continue

        paket = PAKETE / paketname(url)
        if not paket.exists():
            try:
                antwort = s.get(url, timeout=120)
                antwort.raise_for_status()
                paket.write_bytes(antwort.content)
            except Exception as f:
                print(f"  Paket nicht ladbar fuer {nr}: {f}", file=sys.stderr)
                continue
            time.sleep(PAUSE)

        abschnitt = paket_abschnitt(pdf_text(paket), nr)
        if not abschnitt:
            # Kein Abbruch: Eine Vorlage ohne auffindbaren Abschnitt bleibt
            # eben ohne Sachverhalt — so wie bisher alle sechs.
            print(f"  {nr}: im Paket kein Abschnitt gefunden", file=sys.stderr)
            leer += 1
            continue
        ziel.write_text(abschnitt, encoding="utf-8")
        nachgetragen += 1
    return nachgetragen, leer


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
        except Exception as f:
            print(f"  Fehler: {ziel.name}: {f}", file=sys.stderr)
            fehler += 1
        time.sleep(PAUSE)

    nachgetragen, leer = aus_paketen_nachtragen(s)

    print(f"Sitzungsvorlagen — neu: {neu}, "
          f"bereits vorhanden: {vorhanden}, fehlgeschlagen: {fehler}, "
          f"aus Gesamtpaket nachgetragen: {nachgetragen}"
          + (f", im Paket nicht gefunden: {leer}" if leer else ""),
          file=sys.stderr)


if __name__ == "__main__":
    main()
