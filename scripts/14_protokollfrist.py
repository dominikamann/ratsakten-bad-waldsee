#!/usr/bin/env python3
"""Misst, wie lange ein Beschlussprotokoll nach der Sitzung auf sich warten laesst.

Der Anlass: Eine Sitzung ohne abrufbares Protokoll stand bisher ab der ersten
Minute unter „Blinder Fleck". Bei einem Wochenlauf war sie dann immer schon
einige Tage alt; bei einem taeglichen Lauf trifft es jede Sitzung am Abend
ihres Stattfindens — und wirft ihr ein Versaeumnis vor, das noch gar nicht
eingetreten sein kann.

Gebraucht wurde also eine belegte Frist statt einer gegriffenen. Gemessen
wird der Abstand zwischen dem Sitzungsdatum und dem **Aenderungsdatum des
PDF** (`/ModDate`).

Was diese Groesse ist und was nicht — das gehoert dazu:

* Sie ist **nicht** der Zeitpunkt, zu dem das Protokoll im
  Ratsinformationssystem eingestellt wurde. Den gibt das System nicht her.
* Sie ist ein **Proxy**: Vor der Erzeugung des PDF kann es nicht online
  gewesen sein, also ist sie eine Untergrenze.
* Sie wird **ueberschrieben, wenn das PDF neu erzeugt wird**. Drei der vier
  grossen Ausreisser tragen Daten vom 28./29.10.2025 — ein Buendel, das nach
  einer Umstellung im System aussieht und nicht nach vier Protokollen, die
  ein Jahr lang fehlten.
* `/CreationDate` ist unbrauchbar: In allen Dateien steht dort derselbe Wert
  aus dem Jahr 2019, ein Artefakt der erzeugenden Software.

Gezaehlt werden nur Dateien, deren Titel mit „Beschlussprotokoll" beginnt.
Zwei der 74 Dateien unter data/protokolle/ sind keine Protokolle, sondern
Tagesordnungsanlagen („TOP 8 — Unterzeichnen der Protokollniederschriften").
Sie tragen ein PDF-Datum **vor** der Sitzung und haetten die Messung verzerrt.

Aufruf:  uv run --with pypdf python scripts/14_protokollfrist.py
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import statistics
import sys
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.CRITICAL)

BASIS = Path(__file__).resolve().parent.parent
PROTOKOLLE = BASIS / "data" / "protokolle"

# Stufen, an denen die Verteilung abgelesen wird.
STUFEN = (2, 3, 5, 7, 10, 14, 21, 28, 42)


def abstaende() -> list[tuple[int, str, dt.date, dt.date]]:
    """Abstand in Tagen je echtem Beschlussprotokoll."""
    werte = []
    for pfad in sorted(PROTOKOLLE.glob("*.pdf")):
        m = PdfReader(pfad).metadata or {}
        if not str(m.get("/Title", "")).startswith("Beschlussprotokoll"):
            continue                      # Tagesordnungsanlage, kein Protokoll
        g = re.match(r"D:(\d{4})(\d{2})(\d{2})", str(m.get("/ModDate", "")))
        if not g:
            continue
        sitzung = dt.date.fromisoformat(pfad.name[:10])
        erzeugt = dt.date(int(g[1]), int(g[2]), int(g[3]))
        werte.append(((erzeugt - sitzung).days, pfad.name, sitzung, erzeugt))
    return werte


def main() -> None:
    werte = abstaende()
    if not werte:
        sys.exit("Keine auswertbaren Protokolle unter data/protokolle/.")
    tage = sorted(x[0] for x in werte)

    print(f"  {len(werte)} Beschlussprotokolle ausgewertet")
    print(f"  Median {statistics.median(tage):.0f} Tage · "
          f"frühestens {min(tage)} · spätestens {max(tage)}")
    print()
    for stufe in STUFEN:
        n = sum(1 for t in tage if t <= stufe)
        print(f"    innerhalb {stufe:>2} Tagen   {n:>3}/{len(tage)}   {n / len(tage) * 100:5.1f} %")

    # Der interessante Teil ist nicht der Median, sondern die Stelle, ab der
    # der Zulauf versiegt: Was bis dahin nicht da ist, kommt erst sehr viel
    # spaeter — und ist dann eine Nachreichung, keine normale Bearbeitung.
    # Gesucht wird die kleinste Stufe, nach der zwei weitere Stufen keinen
    # einzigen Zuwachs mehr bringen. Eine Stufe allein genuegt nicht: Das
    # traefe auch eine zufaellige Luecke in der Verteilung.
    zaehlung = {s: sum(1 for t in tage if t <= s) for s in STUFEN}
    schnitt = None
    for i, stufe in enumerate(STUFEN[:-2]):
        folgende = STUFEN[i + 1:i + 3]
        if all(zaehlung[f] == zaehlung[stufe] for f in folgende) and zaehlung[stufe] < len(tage):
            schnitt = stufe
            break

    if schnitt:
        n = zaehlung[schnitt]
        letzte = STUFEN[STUFEN.index(schnitt) + 2]
        print()
        print(f"  Schnitt bei {schnitt} Tagen: Bis {letzte} Tage kommt danach kein einziges")
        print(f"  Protokoll mehr nach. {n} von {len(tage)} ({n / len(tage) * 100:.1f} %) liegen dann vor;")
        print(f"  die übrigen {len(tage) - n} sind Nachreichungen mit "
              f"{min(t for t in tage if t > schnitt)} bis {max(tage)} Tagen Abstand.")
        print()
        print(f"  → Als Karenzfrist verwendet: KARENZ_TAGE = {schnitt} "
              "in scripts/05_ausgaben_bauen.py")


if __name__ == "__main__":
    main()
