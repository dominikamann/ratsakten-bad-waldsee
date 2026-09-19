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

# Zahlen bis 25 als Wort. Stand zweimal im Quelltext — einmal großgeschrieben
# für den Satzanfang auf der Startseite, einmal klein für die Themenseiten.
# Zwei Tabellen derselben Sache laufen früher oder später auseinander. Hier und
# nicht in textwerk.py, weil jenes Modul pypdf hereinzieht: Schritt 06 und 11
# kämen sonst ohne PDF-Bibliothek nicht mehr durch.
ZAHLWORT = {
    1: "Eine", 2: "Zwei", 3: "Drei", 4: "Vier", 5: "Fünf", 6: "Sechs",
    7: "Sieben", 8: "Acht", 9: "Neun", 10: "Zehn", 11: "Elf", 12: "Zwölf",
    13: "Dreizehn", 14: "Vierzehn", 15: "Fünfzehn", 16: "Sechzehn",
    17: "Siebzehn", 18: "Achtzehn", 19: "Neunzehn", 20: "Zwanzig",
    21: "Einundzwanzig", 22: "Zweiundzwanzig", 23: "Dreiundzwanzig",
    24: "Vierundzwanzig", 25: "Fünfundzwanzig",
}


def zahlwort(n: int, gross: bool = True) -> str:
    """Die Zahl als Wort; jenseits der Tabelle als Ziffer."""
    wort = ZAHLWORT.get(n)
    if wort is None:
        return str(n)
    return wort if gross else wort.lower()


# Fuer Rubriken und Marken: ein Name, den man lesen kann. Der volle Name des
# Gemeinsamen Ausschusses ist 86 Zeichen lang und sprengt jede Zeile. Stand
# vorher nur in 05; die Themenseiten brauchen ihn seit der Gremienmarke auch.
RUBRIKNAME = {
    "Gemeinsamer Ausschuss der Vereinbarten Verwaltungsgemeinschaft "
    "Bad Waldsee-Bergatreute": "Gemeinsamer Ausschuss",
}


def rubrikname(name: str) -> str:
    return RUBRIKNAME.get(name, name)


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

_AKTUELLE_AUSGABE: str | None = None


def aktuelle_ausgabe_setzen(pfad: str) -> None:
    """Das Ziel des Menuepunkts von aussen vorgeben.

    Schritt 05 kennt die neueste Ausgabe, **bevor** er sie schreibt — das
    Register auf der Platte ist zu diesem Zeitpunkt noch das der Vorwoche.
    Ohne diesen Weg zeigte der Menuepunkt auf jeder frisch gebauten Seite
    eine Woche zurueck, bis der naechste Lauf ihn einholte.
    """
    global _AKTUELLE_AUSGABE
    _AKTUELLE_AUSGABE = pfad


def aktuelle_ausgabe() -> str:
    """Pfad der juengsten Wochenausgabe, relativ zu docs/.

    Der Menuepunkt „Aktuelle Ausgabe" kann nicht fest in navigation.json
    stehen: Sein Ziel wechselt jede Woche. Ermittelt wird es aus dem
    Ausgabenregister — derselben Quelle, aus der die Startseite verlinkt.
    """
    # Einmal gesetzt oder einmal gelesen — `navigation()` fragt je Menueeintrag
    # nach, das waeren sonst sechzehn Dateizugriffe pro Seite.
    global _AKTUELLE_AUSGABE
    if _AKTUELLE_AUSGABE is not None:
        return _AKTUELLE_AUSGABE

    register = WURZEL / "data" / "ausgaben.json"
    if not register.exists():
        return "ausgaben/index.html"          # Archiv als Rueckfallebene
    r = json.loads(register.read_text(encoding="utf-8"))
    if not r:
        return "ausgaben/index.html"
    jahr = max(r, key=int)
    _AKTUELLE_AUSGABE = f"ausgaben/{jahr}/kw{max(r[jahr], key=int)}.html"
    return _AKTUELLE_AUSGABE


def navigation(hoch: str = "", hier: str = "") -> str:
    """Die Verweise der Markenleiste.

    `hoch` ist der relative Weg zum docs-Verzeichnis, `hier` markiert die
    aktuelle Seite.
    """
    teile = []
    for x in EINTRAEGE:
        aktuell = ' aria-current="page"' if x["name"] == hier else ""
        ziel = x["ziel"].replace("{aktuelle_ausgabe}", aktuelle_ausgabe())
        teile.append(f'<a href="{hoch}{ziel}"{aktuell}>{x["text"]}</a>')
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


def fuss(hoch: str = "", meta: str = "", ende: bool = True,
         stand: bool = True) -> str:
    """Der Fuß — auf jeder Seite gleich.

    Die Seiten sind lang; wer unten ankommt, findet dort dieselben Verweise wie
    oben, statt zurückscrollen zu müssen.

    Das Datum des letzten Laufs steht auf **jeder** Seite. Es stand vorher nur
    auf dreien, und wer eine der uebrigen aufrief, konnte nicht erkennen, ob er
    den Stand von gestern oder von vor drei Monaten vor sich hat. Bei einer
    Seite, die Beschluesse wiedergibt, ist das keine Nebensache.
    """
    teile = [meta] if meta else []
    if stand:
        teile.append(f"aktualisiert am {kurz(dt.date.today())}")
    zusatz = "".join(f" &middot; {x}" for x in teile)
    # Der Fuss trug bisher nur den Kurzhinweis; der ausfuehrliche
    # Haftungsausschluss stand allein auf der Startseite. Wer ueber eine
    # Wochenausgabe oder eine Themenseite einsteigt — und das ist der Regelfall,
    # weil Verweise dorthin geteilt werden —, fand ihn nie. Jetzt von ueberall.
    hinweise = f'<a href="{hoch}index.html#hinweise">Hinweise</a>'
    # `ende=False` fuer Seiten, die nach dem Fuss noch ein Skript mitgeben.
    schluss = "\n</body>\n</html>" if ende else ""
    return f"""
<footer><div class="wrap">
  <nav aria-label="Bereiche">
    {navigation(hoch)}
  </nav>
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
    <p class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr
    &middot; {hinweise}{zusatz}</p>
</div></footer>
<a class="hoch" href="#seitenanfang"><span aria-hidden="true">&uarr;</span><span class="sr">Zum Seitenanfang</span></a>{schluss}"""
