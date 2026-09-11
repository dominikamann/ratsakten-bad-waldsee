"""Die Navigation der Website — an einer Stelle.

Sechs Bauskripte und der Report erzeugen jeweils eigene Seiten, brauchen aber
dieselbe Navigationsleiste. Bis hierher stand sie siebenmal im Quelltext; fuer
zwei neue Eintraege mussten sechs Dateien angefasst werden. Eine Seite, die
dabei vergessen wird, faellt niemandem auf — sie verliert nur still einen
Verweis.

Die Eintraege stehen deshalb in `navigation.json`. Diese Datei liest sowohl
dieses Modul als auch `04_vorrendern.js`, das die Leiste im Report ersetzt.
"""

from __future__ import annotations

import json
from pathlib import Path

EINTRAEGE = json.loads(
    (Path(__file__).resolve().parent / "navigation.json").read_text(encoding="utf-8"))


def navigation(hoch: str = "", hier: str = "") -> str:
    """Die Verweise der Markenleiste.

    `hoch` ist der relative Weg zum docs-Verzeichnis, `hier` markiert die
    aktuelle Seite.
    """
    teile = []
    for e in EINTRAEGE:
        aktuell = ' aria-current="page"' if e["name"] == hier else ""
        teile.append(f'<a href="{hoch}{e["ziel"]}"{aktuell}>{e["text"]}</a>')
    return "\n    <span aria-hidden=\"true\">/</span>\n    ".join(teile)
