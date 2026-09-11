"""Der gemeinsame Rahmen aller Seiten — Kopf, Navigation, Fuß, Datumsformate.

Sieben Bauskripte und der Report erzeugen jeweils eigene Seiten, brauchen aber
denselben Rahmen. Bis hierher stand er in jedem Skript noch einmal: derselbe
Dokumentkopf, dieselbe Markenleiste, ein etwas anderer Fuß. Acht Kopien
derselben Sache laufen zuverlässig auseinander — zuletzt trug der Fuß auf vier
Seiten eine Verweisliste und auf vier anderen eine Markenzeile, und das Datum
erschien in drei Schreibweisen nebeneinander.

Hier steht es einmal. Eine neue Seite ist ein Aufruf von `kopf()` und `fuss()`;
ein neuer Menüeintrag eine Zeile in `navigation.json`, die auch
`04_vorrendern.js` liest.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

SKRIPTE = Path(__file__).resolve().parent
WURZEL = SKRIPTE.parent

EINTRAEGE = json.loads((SKRIPTE / "navigation.json").read_text(encoding="utf-8"))

TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "M&auml;rz", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


def e(s) -> str:
    """Zeichen maskieren, die im HTML eine Bedeutung haben."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- Datum ----------
# Zwei Schreibweisen, und nur diese zwei: die lange im Fließtext, die kurze in
# den einzeiligen Kennzahlen- und Fußzeilen. Das ISO-Datum aus den Daten
# erscheint nirgends auf einer Seite — es ist ein Speicherformat, kein Lesetext.

def datum(wert) -> dt.date:
    return wert if isinstance(wert, dt.date) else dt.date.fromisoformat(str(wert)[:10])


def lang(wert) -> str:
    d = datum(wert)
    return f"{TAGE[d.weekday()]}, {d.day}. {MONATE[d.month - 1]} {d.year}"


def kurz(wert) -> str:
    d = datum(wert)
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


# ---------- Navigation ----------

def navigation(hoch: str = "", hier: str = "") -> str:
    """Die Verweise der Markenleiste.

    `hoch` ist der relative Weg zum docs-Verzeichnis, `hier` markiert die
    aktuelle Seite.
    """
    teile = []
    for x in EINTRAEGE:
        aktuell = ' aria-current="page"' if x["name"] == hier else ""
        teile.append(f'<a href="{hoch}{x["ziel"]}"{aktuell}>{x["text"]}</a>')
    return "\n    <span aria-hidden=\"true\">/</span>\n    ".join(teile)


# ---------- Stilvorlagen ----------

def stil(*namen: str, pfad: str = "") -> str:
    """Die genannten Stildateien aneinanderhängen.

    `basis.css` steht immer zuerst; was danach kommt, darf es überschreiben.
    Die Schriften tragen einen Platzhalter für den Weg zum docs-Verzeichnis.
    """
    teile = []
    for n in ("schriften.css", "basis.css", *namen):
        text = (SKRIPTE / n).read_text(encoding="utf-8")
        teile.append(text.replace("{PFAD}", pfad))
    return "\n".join(teile)


# ---------- Seitenrahmen ----------

def kopf(titel: str, *, hoch: str = "", hier: str = "", beschreibung: str = "",
         stile: tuple[str, ...] = ("ausgabe.css",), eigen: str = "",
         koerper: str = "lesen") -> str:
    """Dokumentkopf und Markenleiste — auf jeder Seite gleich.

    `eigen` nimmt die Regeln auf, die wirklich nur diese eine Seite braucht.
    """
    meta = (f'\n<meta name="description" content="{e(beschreibung)}">'
            if beschreibung else "")
    zusatz = f"<style>\n{eigen.strip()}\n</style>\n" if eigen.strip() else ""
    klasse = f' class="{koerper}"' if koerper else ""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title>{meta}
<style>{stil(*stile, pfad=hoch)}</style>
{zusatz}</head>
<body{klasse}>

<div class="brandbar" id="seitenanfang"><div class="wrap">
  <nav aria-label="Bereiche">
    {navigation(hoch, hier)}
  </nav>
</div></div>
"""


def fuss(hoch: str = "", meta: str = "", ende: bool = True) -> str:
    """Der Fuß — auf jeder Seite gleich.

    Die Seiten sind lang; wer unten ankommt, findet dort dieselben Verweise wie
    oben, statt zurückscrollen zu müssen.
    """
    zusatz = f" &middot; {meta}" if meta else ""
    # `ende=False` fuer Seiten, die nach dem Fuss noch ein Skript mitgeben.
    schluss = "\n</body>\n</html>" if ende else ""
    return f"""
<footer><div class="wrap">
  <nav aria-label="Bereiche">
    {navigation(hoch)}
  </nav>
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
    <p class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr{zusatz}</p>
</div></footer>
<a class="hoch" href="#seitenanfang"><span aria-hidden="true">&uarr;</span><span class="sr">Zum Seitenanfang</span></a>{schluss}"""
