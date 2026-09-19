"""Der Weg eines Vorhabens durch das Verfahren — als Kurzfassung.

Eine Chronik mit 19 Stationen beantwortet die Frage „wie ist der Stand?" erst
nach vollstaendigem Lesen. Dieser Baustein stellt die Kurzfassung voran.

**Was hier ausdruecklich nicht geschieht: auswaehlen, was wichtig ist.** Eine
Kurzfassung, die eine Vergabe nennt und eine Abwaegung weglaesst, haette eine
Wertung getroffen, die in keinem Protokoll steht — genau die Fehlerklasse,
die dieses Projekt gefaehrdet.

Stattdessen wird gelesen, was die Verwaltung selbst in den amtlichen Titel
schreibt. Er endet in aller Regel mit der Bezeichnung des Verfahrensschritts:

    Bebauungsplan Teilbereich B „Drei Eichen VI" … – Abwägung und Entwurfsbeschluss
    20. Änderung des Flächennutzungsplans … - Abwägung und Feststellungsbeschluss

Diese Bezeichnung wird uebernommen, nicht gedeutet und nicht umformuliert.
Wo der Titel keinen Verfahrensschritt nennt, entsteht keine Zeile; die Station
steht weiterhin in der Chronik darunter. Der Baustein ist eine Uebersicht ueber
das Verfahren, kein Ersatz fuer sie.

Drei Fallen, alle beim Auszaehlen ueber den ganzen Bestand gefunden:

1. **Der Gedankenstrich steht oft ohne Leerzeichen davor** („Gaisbeuren-
   Abwägung und Entwurfsbeschluss"). Verlangt man Leerzeichen auf beiden
   Seiten, fehlen fuenf der elf Schritte von „Drei Eichen VI". Verlangt wird
   deshalb nur das Leerzeichen *danach* — sonst zerrisse „Drei-Eichen".
2. **„Aufstellungs- und Ueberleitungsbeschluss" enthaelt selbst einen solchen
   Strich.** Ungeschuetzt bliebe als Schritt „und Ueberleitungsbeschluss".
3. **Zusammengefasst wird nach Vorlagennummer, nicht nach Wortlaut.** Dieselbe
   Vorlage durchlaeuft mehrere Gremien — das ist ein Schritt. Zwei Vorlagen mit
   gleicher Bezeichnung sind dagegen zwei Schritte: „Drei Eichen VI" hatte am
   17.06. und am 16.09.2024 je einen Entwurfsbeschluss, aus zwei Vorlagen.
   Nach Wortlaut gebuendelt waere daraus faelschlich einer geworden.

Parallel laufende Verfahren bekommen ihren Strang genannt (Bebauungsplan,
Flaechennutzungsplan, Teilbereich A oder B). Ohne das liest sich die Liste bei
„Drei Eichen VI" so, als sei der Satzungsbeschluss vom 25.11.2024 spaeter
wieder aufgeschnuert worden — tatsaechlich betraf er Teilbereich A, waehrend
Teilbereich B erst begann.
"""

from __future__ import annotations

import re

# Woran ein Verfahrensschritt zu erkennen ist. Bewusst kurz gehalten: jedes
# Wort hier stammt aus dem amtlichen Sprachgebrauch der Bauleitplanung und des
# Sanierungsrechts und ist im Bestand ausgezaehlt.
VERFAHREN = re.compile(
    r"(beschluss|abwägung|beteiligung|vergabe|erschließungsträger|"
    r"änderungssatzung|aufhebung)", re.I)

# Ab wann die Kurzfassung ueberhaupt etwas leistet: Sie braucht mindestens zwei
# Schritte, und sie muss kuerzer sein als die Chronik, ueber der sie steht.
# Sonst gibt sie dieselbe Auskunft ein zweites Mal.
MINDEST_SCHRITTE = 2

_SCHUTZ = chr(1)


def schrittname(titel: str) -> str | None:
    """Die Bezeichnung des Verfahrensschritts aus dem amtlichen Titel."""
    t = re.sub(r"\s+", " ", titel or "").strip()
    # „Aufstellungs- und Ueberleitungsbeschluss": dieser Strich trennt keine
    # Titelteile, sondern haelt ein Wort zusammen.
    t = re.sub(r"-\s+(und|bzw|oder)\s+",
               lambda m: f"{_SCHUTZ} {m.group(1)} ", t)
    teile = re.split(r"\s*[–—-]\s+|,\s*hier:\s*", t)
    if len(teile) < 2:
        return None
    letzter = teile[-1].replace(_SCHUTZ, "-").strip(" .,")
    return letzter if VERFAHREN.search(letzter) else None


def strang(titel: str) -> str:
    """Welches parallel laufende Verfahren die Station betrifft."""
    t = titel or ""
    if re.search(r"Flächennutzungsplan", t, re.I):
        art = "Flächennutzungsplan"
    elif re.search(r"Bebauungsplan", t, re.I):
        art = "Bebauungsplan"
    elif re.search(r"Baugebiet|Erschließung", t, re.I):
        art = "Erschließung"
    else:
        art = ""
    teil = re.search(r"Teilbereich(?:es)?\s+([A-Z])\b", t)
    if teil:
        art = f"{art}, Teilbereich {teil.group(1)}" if art else \
              f"Teilbereich {teil.group(1)}"
    return art


def schritte(stationen: list[dict]) -> list[dict]:
    """Die Verfahrensschritte eines Vorhabens in zeitlicher Folge.

    `stationen` muss nach Datum sortiert sein; jede Station braucht den
    Schluessel `_nr` mit ihrer Nummer in der Chronik, damit die Kurzfassung
    dorthin verweisen kann.

    `gremien` zaehlt jedes Gremium einmal, `stationen` dagegen jede Behandlung:
    SV-95/2024 stand dreimal auf einer Tagesordnung, aber in zwei Gremien — der
    Gemeinderat behandelte sie am 23.09.2024 und erneut am 28.04.2025.
    """
    weg: list[dict] = []
    for st in stationen:
        name = schrittname(st.get("t", ""))
        if not name:
            continue
        # Dieselbe Vorlage in mehreren Gremien ist ein Schritt. Stationen ohne
        # Vorlagennummer koennen nur ueber ihre Bezeichnung gebuendelt werden.
        schluessel = st.get("v") or f"ohne-nummer:{name.lower()}"
        vorher = next((s for s in weg if s["schluessel"] == schluessel), None)
        if vorher is not None:
            if st["gl"] not in vorher["gremien"]:
                vorher["gremien"].append(st["gl"])
            vorher["bis"] = st["d"]
            vorher["stationen"] += 1
            continue
        weg.append({
            "schluessel": schluessel,
            "name": name,
            "strang": strang(st.get("t", "")),
            "von": st["d"],
            "bis": st["d"],
            "gremien": [st["gl"]],
            "stationen": 1,
            "vorlage": st.get("v") or "",
            "nr": st["_nr"],
        })
    return weg


def lohnt(weg: list[dict], stationen: list[dict]) -> bool:
    """Ob die Kurzfassung mehr leistet als die Chronik selbst."""
    return len(weg) >= MINDEST_SCHRITTE and len(weg) < len(stationen)
