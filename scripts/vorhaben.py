"""Welche Vorgaenge ein Vorhaben bilden — und wie dessen Seite heisst.

Zwei Schritte brauchen dieselbe Antwort: Schritt 11 baut die Themenseiten,
Schritt 08 verlinkt aus der Suche darauf. Waere die Zuordnung zweimal
geschrieben, liefe sie frueher oder spaeter auseinander und die Suche zeigte
Verweise auf Seiten, die es nicht gibt.
"""

from __future__ import annotations

import re
import unicodedata

# Ab wie vielen Stationen lohnt eine eigene Seite. Bei einer einzigen stuende
# dort nichts, was nicht schon in der Wochenausgabe steht.
MINDEST_STATIONEN = 2


def slug(name: str) -> str:
    roh = unicodedata.normalize("NFKD", name)
    roh = (roh.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
              .replace("Ä", "ae").replace("Ö", "oe").replace("Ü", "ue")
              .replace("ß", "ss"))
    roh = "".join(c for c in roh if not unicodedata.combining(c))
    roh = re.sub(r"[^A-Za-z0-9]+", "-", roh).strip("-").lower()
    return roh[:60] or "vorhaben"


def vergleichsname(name: str) -> str:
    """Schluessel, unter dem zwei Schreibweisen dasselbe Vorhaben meinen.

    Die Verwaltung schreibt denselben Vorgang nicht immer gleich: „der
    Vereinbarten Verwaltungsgemeinschaft" und „der vereinbarten
    Verwaltungsgemeinschaft", „Sport- und Gesundheitspark" und „Sport- und
    Gesundheitsparks". Ohne diesen Abgleich entstuenden zwei Seiten fuer ein
    Vorhaben.
    """
    worte = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", name.lower())
    return " ".join(w[:-1] if len(w) > 4 and w.endswith("s") else w for w in worte)


def zusammenfuehren(vorgaenge: list[dict]) -> list[dict]:
    """Mehrstufige Vorgaenge zu Vorhaben buendeln, je mit Namenskuerzel.

    Nur mehrstufige Vorgaenge sind Vorhaben im hier gemeinten Sinn. Einzelne
    Tagesordnungspunkte tragen oft denselben Routinetitel („Verschiedenes",
    „Bekanntgaben"); wuerde man auch sie zusammenfassen, entstuenden
    Sammelseiten, die kein Vorhaben beschreiben.
    """
    kandidaten = [v for v in vorgaenge if len(v.get("s", [])) >= MINDEST_STATIONEN]

    zusammen: dict[str, dict] = {}
    for v in kandidaten:
        k = vergleichsname(v["t"])
        if k in zusammen:
            ziel = zusammen[k]
            bekannt = {(st["d"], st.get("v"), st["t"]) for st in ziel["s"]}
            ziel["s"] += [st for st in v["s"]
                          if (st["d"], st.get("v"), st["t"]) not in bekannt]
            if len(v["t"]) > len(ziel["t"]):
                ziel["t"] = v["t"]
            ziel["v"] = " · ".join(sorted(
                {n for n in (ziel["v"] + " · " + v["v"]).split(" · ") if n}))
        else:
            zusammen[k] = dict(v, s=list(v["s"]), _schluessel=k)

    auswahl = [v for v in zusammen.values() if len(v["s"]) >= MINDEST_STATIONEN]
    auswahl.sort(key=lambda v: (-len(v["s"]), v["t"]))

    vergeben: set[str] = set()
    for v in auswahl:
        name = slug(v["t"])
        if name in vergeben:                 # zwei Vorhaben gleichen Namens
            name = f"{name}-{len(vergeben)}"
        vergeben.add(name)
        v["_slug"] = name
    return auswahl


def seiten_je_vorgang(vorgaenge: list[dict]) -> dict[str, str]:
    """Zu jedem Vorgangstitel die Themenseite, sofern es eine gibt."""
    return {v["_schluessel"]: v["_slug"] for v in zusammenfuehren(vorgaenge)}
