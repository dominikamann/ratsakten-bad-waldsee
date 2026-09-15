#!/usr/bin/env python3
"""Traegt die Kennzahlen des letzten Laufs in die README ein.

Die Zahlen in der README standen bisher von Hand da und liefen dem Bestand
hinterher: Nach einem Lauf stimmten Dokumentzahl, Ausgabenzahl und Stichtag
nicht mehr, und auffallen konnte das nur, wo pruefen.py zufaellig hinsah.
Zweimal wurde deshalb eine falsche Zahl veroeffentlicht.

Dieser Schritt setzt jede dieser Stellen aus den Daten. Er ersetzt keinen
Fliesstext, sondern genau die Zahl in einer bekannten Umgebung — und
**bricht ab**, wenn eine Stelle nicht mehr auffindbar ist. Eine still
uebersprungene Ersetzung waere schlimmer als gar keine: Sie sieht aus wie
Pflege und ist keine.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent
DATEN = BASIS / "data"
DOKUMENTE = BASIS / "docs"
README = BASIS / "README.md"

MONATE = ("Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")


def lies(pfad: Path):
    return json.loads(pfad.read_text(encoding="utf-8"))


def stellen() -> list[tuple[str, str]]:
    """Paare aus Suchmuster und Ersatz. Jedes Muster muss genau einmal passen."""
    k = lies(DATEN / "kennzahlen.json")
    register = lies(DATEN / "ausgaben.json")
    suche = lies(DATEN / "suche.json")
    vorgaenge = lies(DATEN / "vorgaenge.json")

    jahr = max(register, key=int)
    woche = max(register[jahr], key=int)
    ausgaben_je_jahr = {j: len(register[j]) for j in register}
    ausgaben = sum(ausgaben_je_jahr.values())

    j, m, t = k["stichtag"].split("-")
    stichtag = f"{t}.{m}.{j}"

    befunde = (DOKUMENTE / "befunde.html").read_text(encoding="utf-8")
    erkenntnisse = befunde.count('class="befundblock"')
    vorhaben = len([p for p in (DOKUMENTE / "themen").glob("*.html")
                    if p.name != "index.html"])
    protokolldateien = len(list((DATEN / "protokolle").glob("*.pdf")))
    ueber_million = sum(1 for v in vorgaenge if (v.get("b") or 0) >= 1_000_000)

    paare = [
        (r"(\| Erfasste Sitzungen \| )\d+( \|)", k["sitzungen"]),
        (r"(\| Tagesordnungspunkte \| )\d+( \|)", k["tagesordnungspunkte"]),
        (r"(\| Sitzungsvorlagen \| )\d+( \|)", k["vorlagen"]),
        (r"(\| Dokumente \| )\d+( \|)", k["dokumente"]),
        (r"(\| Ausgewertete Beschlussprotokolle \| )\d+( \|)", k["protokolle"]),
        (r"(\| Ausgezählte Abstimmungen \| )\d+( \|)", k["abstimmungen"]["gesamt"]),
        (r"(\| Gremien \| )\d+( \|)", len(k["gremien"])),
        (r"(\*\*Zeitraum:\*\* 01\.01\.2024 – )[\d.]+( \(Stichtag\))", stichtag),
        (r"(alle )\d+( Ausgaben der Jahrgänge)", ausgaben),
        (r"(— )\d+( Vorgänge mit ihrem Weg)", suche["sachvorgaenge"]),
        (r"(— )\d+( Vorhaben mit ihrem vollständigen Verlauf)", vorhaben),
        (r"(alle )\d+( Erkenntnisse an einem Ort)", erkenntnisse),
        (r"(nachgeholt \()\d+( Stück\))", ausgaben),
        (r"(Original\. )\d+( Dokumente sind so erreichbar)", k["dokumente"]),
        (r"(und )\d+( Protokolldateien zu )\d+( Sitzungen)",
         (protokolldateien, k["protokolle"])),
        (r"(filtern — )\d+( Vorgänge nennen eine Million)", ueber_million),
        (r"(Themenseiten: )\d+( Vorhaben mit allen Stationen)", vorhaben),
    ]
    for jahrgang, anzahl in sorted(ausgaben_je_jahr.items()):
        paare.append((rf"(── {jahrgang}/\s+)\d+( Ausgaben)", anzahl))


    # Die aktuelle Ausgabe: Ueberschrift und Verweis muessen zusammen wandern.
    paare.append((
        r"(\*\*\[Aktuelle Ausgabe, KW )\d+(/)\d+(\]\(\./docs/ausgaben/)\d+(/kw)\d+(\.html\))",
        (int(woche), jahr, jahr, f"{int(woche):02d}"),
    ))
    return paare


def jahrgaenge_ergaenzen(text: str) -> str:
    """Fehlende Jahrgangszeilen in den Verzeichnisbaum einfuegen.

    Der Baum kennt nur Jahrgaenge, die es beim Schreiben gab. Die erste
    Ausgabe eines neuen Jahres haette den Lauf sonst abgebrochen — jedes Jahr
    einmal, und zwar nachdem alles gebaut und bevor irgendetwas geprueft oder
    veroeffentlicht ist. Ein Jahreswechsel ist keine Umformulierung, gegen die
    der Abbruch schuetzen soll; er ist vorhersehbar.
    """
    register = lies(DATEN / "ausgaben.json")
    zeilen = re.findall(r"^(\s*[│├└─\s]*── )(\d{4})(/\s+)(\d+)( Ausgaben)$",
                        text, re.M)
    if not zeilen:
        return text
    vorhanden = {j for _, j, _, _, _ in zeilen}
    fehlen = sorted(set(register) - vorhanden)
    for jahr in fehlen:
        # An die letzte vorhandene Zeile anhaengen, Einrueckung uebernehmen.
        letzte = re.findall(rf"^.*── {max(vorhanden)}/.*$", text, re.M)[-1]
        neu = re.sub(r"── \d{4}/(\s+)\d+( Ausgaben)",
                     lambda m: f"── {jahr}/{m.group(1)}{len(register[jahr])}{m.group(2)}",
                     letzte)
        # Der vorletzte Jahrgang bekommt den Abzweig, der neue den Abschluss.
        text = text.replace(letzte, letzte.replace("└──", "├──") + "\n" + neu, 1)
        vorhanden.add(jahr)
    return text


def main() -> None:
    text = jahrgaenge_ergaenzen(README.read_text(encoding="utf-8"))
    geaendert = 0

    for muster, wert in stellen():
        treffer = re.findall(muster, text)
        if len(treffer) != 1:
            sys.exit(f"README-Pflege abgebrochen: {len(treffer)} Treffer für {muster!r} "
                     "— erwartet wurde genau einer. Die Stelle wurde umformuliert; "
                     "das Muster gehört nachgezogen.")
        werte = wert if isinstance(wert, tuple) else (wert,)

        def einsetzen(m: re.Match, werte: tuple = werte) -> str:
            # Die Gruppen des Musters sind die Umgebung, die Werte gehoeren
            # dazwischen: Umgebung, Zahl, Umgebung, Zahl, ..., Umgebung.
            teile: list[str] = []
            for i, umgebung in enumerate(m.groups()):
                teile.append(umgebung)
                if i < len(werte):
                    teile.append(str(werte[i]))
            return "".join(teile)

        neu = re.sub(muster, einsetzen, text)
        if neu != text:
            geaendert += 1
        text = neu

    README.write_text(text, encoding="utf-8")
    print(f"  README.md  —  {len(stellen())} Stellen geprüft, {geaendert} aktualisiert")


if __name__ == "__main__":
    main()
