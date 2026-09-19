#!/usr/bin/env python3
"""Traegt die Kennzahlen des letzten Laufs in src/report.html ein.

Der Report ist ein datiertes Dokument — aber seine Zahlen standen von Hand
darin, an 25 Stellen und in vier Diagrammen. Beim Gegenlesen am 19.09.2026
waren zwei davon bereits veraltet („Bau & Sanierung 49", tatsaechlich 50;
„Kinder, Schule, Soziales 28", tatsaechlich 29), ohne dass es jemandem
auffallen konnte.

Dieser Schritt macht mit dem Report, was Schritt 13 mit der README macht: Er
ersetzt keinen Fliesstext, sondern genau die Zahl in einer bekannten Umgebung
— und **bricht ab**, wenn eine Stelle nicht genau einmal auffindbar ist. Eine
still uebersprungene Ersetzung waere schlimmer als gar keine.

**Zwei Fallen, beide beim Bauen aufgetreten:**

* `300` steht nicht nur in der Kachel „Sitzungsvorlagen", sondern auch als
  `H=300` in einem Diagramm. Ein Muster ohne Umgebung haette die Zeichenflaeche
  verstellt.
* `248` steht nicht nur bei den Formalia, sondern in den Vorlagennummern
  SV-248/2025 und SV-248/2023.

Deshalb traegt **jedes** Muster seine Umgebung als Gruppen; dazwischen kommen
die Werte. Aufruf:

    uv run python scripts/16_report_pflegen.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent
DATEN = BASIS / "data"
REPORT = BASIS / "src" / "report.html"

MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")

# Die Diagramme nennen die Gremien kuerzer als die Daten. Feste Zuordnung, kein
# Raten: Was hier fehlt, faellt in die Sammelzeile.
DIAGRAMMNAME = {
    "Gemeinderat": "Gemeinderat",
    "Ortschaftsrat Reute-Gaisbeuren": "Ortschaftsrat Reute-Gaisbeuren",
    "Ortschaftsrat Mittelurbach": "Ortschaftsrat Mittelurbach",
    "Ortschaftsrat Michelwinnaden": "Ortschaftsrat Michelwinnaden",
    "Ortschaftsrat Haisterkirch": "Ortschaftsrat Haisterkirch",
    "Ausschuss Umwelt/Technik": "Ausschuss Umwelt/Technik",
    "Verwaltungsausschuss": "Verwaltungsausschuss",
    "Gemeinsamer Ausschuss der Vereinbarten Verwaltungsgemeinschaft "
    "Bad Waldsee-Bergatreute": "Gemeinsamer Ausschuss VVG",
}
SAMMELZEILE = "Kulturbeirat, Baumkommission, AK"


def lies(pfad: Path):
    return json.loads(pfad.read_text(encoding="utf-8"))


def gremienreihen(k: dict) -> str:
    """Die Datenzeilen des Gremiendiagramms: Name, protokolliert, ohne."""
    zeilen, rest_mit, rest_ohne = [], 0, 0
    for name, v in k["gremien"].items():
        ohne = v["sitzungen"] - v["protokolle"]
        if name in DIAGRAMMNAME:
            zeilen.append((DIAGRAMMNAME[name], v["protokolle"], ohne))
        else:
            rest_mit += v["protokolle"]
            rest_ohne += ohne
    zeilen.sort(key=lambda z: -(z[1] + z[2]))
    if rest_mit or rest_ohne:
        zeilen.append((SAMMELZEILE, rest_mit, rest_ohne))
    return ",\n    ".join(f'["{n}",{a},{b}]' for n, a, b in zeilen)


def themenreihen(k: dict) -> str:
    return ",".join(f'["{n}",{a}]' for n, a in k["themen"].items())


def stellen() -> list[tuple[str, tuple]]:
    """Paare aus Suchmuster und Werten. Jedes Muster muss genau einmal passen."""
    k = lies(DATEN / "kennzahlen.json")
    jahr, monat, tag = k["stichtag"].split("-")
    lang = f"{int(tag)}. {MONATE[int(monat) - 1]} {jahr}"
    kurz = f"{tag}.{monat}.{jahr}"

    sitzungen = k["sitzungen"]
    tops = k["tagesordnungspunkte"]
    themen = k["themen"]
    formalia = themen["Formalia ohne Sachinhalt"]
    flaechen = themen["Bauleitplanung"] + themen["Bau & Sanierung"]
    ortschaftsrat = sum(v["sitzungen"] for n, v in k["gremien"].items()
                        if n.startswith("Ortschaftsrat"))
    g = k["gremien"]
    gr_tops = g["Gemeinderat"]["tops"]
    ausschuss_tops = (g["Ausschuss Umwelt/Technik"]["tops"]
                      + g["Verwaltungsausschuss"]["tops"])
    ga_tops = next(v["tops"] for n, v in g.items() if n.startswith("Gemeinsamer"))
    ak_tops = next(v["tops"] for n, v in g.items() if n.startswith("Arbeitskreis"))

    return [
        # --- Kopf
        (r"(bis zum )(?:\d+\. \w+ \d{4})( — )\d+( Sitzungen, )\d+"
         r"( Tagesordnungspunkte, )\d+",
         (lang, sitzungen, tops, k["abstimmungen"]["gesamt"])),
        (r'(<span class="v">)\d+(</span><span class="k">Sitzungen)', (sitzungen,)),
        (r'(<span class="v">)\d+(</span><span class="k">Tagesordnungs-)', (tops,)),
        (r'(<span class="v">)\d+(</span><span class="k">Sitzungs-)', (k["vorlagen"],)),
        (r'(<span class="v">)\d+(</span><span class="k">verlinkte)', (k["dokumente"],)),
        (r'(<span class="v">)\d+(</span><span class="k">öffentliche)', (k["protokolle"],)),
        (r'(<span class="v">)\d+(</span><span class="k">ausgewertete)',
         (k["abstimmungen"]["gesamt"],)),
        # --- Datumsangaben
        (r'(class="figsub">01\.01\.2024 – )[\d.]+( · n = )\d+( Sitzungen)',
         (kurz, sitzungen)),
        # Der Korrekturhinweis traegt ein eigenes Datum — das ist der Tag der
        # Korrektur, nicht der Stichtag. Er wird deshalb **nicht** mitgesetzt.
        (r"(<b>Stichtag:</b> )(?:\d+\. \w+ \d{4})", (lang,)),
        (r"(ohne Gewähr · Stand )[\d.]+", (kurz,)),
        # --- Transparenzkapitel
        (r"(Belege: )\d+( erfasste Sitzungen, davon )\d+( Ortschaftsrats)",
         (sitzungen, ortschaftsrat)),
        (r"(verlinkt )\d+( Dokumente auf dieser Grundlage)", (k["dokumente"],)),
        (r"(var data=\[)\s*\[\"Gemeinderat\".*?(\n  \];)",
         ("\n    " + gremienreihen(k) + "\n  ",)),
        # --- Themenkapitel
        (r"(Die )\d+( Punkte stammen ausschließlich)", (tops,)),
        (r'(class="figsub">n = )\d+( Punkte)', (tops,)),
        (r"(zusammen ergeben <b>)\d+( von )\d+( Punkten</b>)", (flaechen, tops)),
        (r"(Grenzfälle unter den )\d+( als Formalia)", (formalia,)),
        (r"(Grenzfälle unter )\d+( Punkten sind)", (tops,)),
        (r"(Aus )\d+( Punkten ausgewählt)", (tops,)),
        # Die Gruppe ist **nur** der Zeilenanfang: Umfasste sie auch die alten
        # Daten, stuenden die neuen dahinter statt an ihrer Stelle. Genau das
        # ist beim ersten Lauf passiert.
        (r'(var data=\[)\["Formalia ohne Sachinhalt".*?\];',
         (themenreihen(k) + "];",)),
        # Die Teilsummen des Hinweises muessen mitwandern — sonst ergeben sie
        # weiter die alte Gesamtzahl.
        (r"(stammen ausschließlich aus Gemeinderat \()\d+"
         r"(\), den beschließenden Ausschüssen \()\d+"
         r"(\), dem Gemeinsamen Ausschuss \()\d+"
         r"(\) und einem Arbeitskreis \()\d+",
         (gr_tops, ausschuss_tops, ga_tops, ak_tops)),
        # Zwei Prozentrechnungen im Diagrammcode. Verankert an ihrem jeweils
        # eigenen Vorspann — die Muster unterscheiden sich sonst nur im
        # Leerzeichen vor dem Prozentzeichen.
        (r'(" Punkte · "\+\(d\[1\]/)\d+(\*100\))', (tops,)),
        (r'(d\[1\]\+"  \("\+\(d\[1\]/)\d+(\*100\))', (tops,)),
    ]


def main() -> None:
    text = REPORT.read_text(encoding="utf-8")
    geaendert = 0
    paare = stellen()

    for muster, werte in paare:
        treffer = re.findall(muster, text, re.S)
        if len(treffer) != 1:
            sys.exit(f"Report-Pflege abgebrochen: {len(treffer)} Treffer für "
                     f"{muster[:60]!r} — erwartet wurde genau einer. Die Stelle "
                     "wurde umformuliert; das Muster gehört nachgezogen.")

        def einsetzen(m: re.Match, werte: tuple = werte) -> str:
            teile: list[str] = []
            for i, umgebung in enumerate(m.groups()):
                teile.append(umgebung)
                if i < len(werte):
                    teile.append(str(werte[i]))
            return "".join(teile)

        neu = re.sub(muster, einsetzen, text, flags=re.S)
        if neu != text:
            geaendert += 1
        text = neu

    REPORT.write_text(text, encoding="utf-8")
    print(f"  src/report.html  —  {len(paare)} Stellen geprüft, "
          f"{geaendert} aktualisiert")


if __name__ == "__main__":
    main()
