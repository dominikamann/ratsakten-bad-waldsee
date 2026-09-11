"""Schritt 12 — der vollstaendige Sitzungskalender.

Die Startseite zeigt die naechsten zehn Termine, das Archiv die erschienenen
Ausgaben. Was fehlte, war der Kalender selbst: alle Sitzungen, vergangene wie
kuenftige, an einem Ort.

Die Seite beginnt bei dem, was ansteht, und geht darunter rueckwaerts durch das
Vergangene. Damit ist der heutige Tag der Anfang der Seite — ohne dass etwas
springen muss, ohne JavaScript und unabhaengig davon, wie die Seite geoeffnet
wird. Ein Anker „#heute" fuehrt zusaetzlich genau auf die Trennlinie.

Jede vergangene Sitzung verweist auf die Wochenausgabe, in der sie ausgewertet
ist; jede Sitzung mit veroeffentlichter Tagesordnung laesst diese aufklappen.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from seite import navigation

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"

TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "M&auml;rz", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


def e(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lang(d: dt.date) -> str:
    return f"{TAGE[d.weekday()]}, {d.day}. {MONATE[d.month - 1]} {d.year}"


def kopf(titel: str) -> str:
    stil = (WURZEL / "scripts" / "ausgabe.css").read_text(encoding="utf-8")
    schriften = (WURZEL / "scripts" / "schriften.css").read_text(
        encoding="utf-8").replace("{PFAD}", "")
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title>
<style>{schriften}</style>
<style>{stil}</style>
<style>
/* Nur diese Seite braucht die Kalenderliste. */
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--s2);margin:0 0 10px}}
.lede{{font-size:clamp(16px,2vw,18px);line-height:1.55;color:var(--muted);max-width:62ch}}
ol.kalender{{list-style:none;margin:18px 0 0;padding:0}}
ol.kalender > li{{padding:13px 0 15px;border-top:1px solid var(--rule)}}
ol.kalender > li:last-child{{border-bottom:1px solid var(--rule)}}
.zeile{{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px}}
.wann{{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted)}}
.gremium{{font-size:16.5px;color:var(--fg)}}
.zustand{{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin-left:auto}}
.zustand a{{color:var(--s1);text-decoration:none}}
.zustand a:hover{{text-decoration:underline}}
details.agenda{{margin-top:7px}}
details.agenda > summary{{
  cursor:pointer;list-style:none;display:inline-flex;align-items:center;gap:7px;
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--s1);
}}
details.agenda > summary::-webkit-details-marker{{display:none}}
details.agenda > summary::before{{content:"\\25B8";font-size:12px}}
details.agenda[open] > summary::before{{content:"\\25BE"}}
details.agenda > summary:hover{{text-decoration:underline}}
ol.tops{{margin:9px 0 0;padding:0 0 0 20px;color:var(--muted)}}
ol.tops li{{margin:0 0 6px;font-size:14.5px;line-height:1.5}}
ol.tops .sv{{margin-left:9px;font-family:"IBM Plex Mono",monospace;font-size:11px;
  color:var(--muted);white-space:nowrap}}
ol.tops .unterlagen{{display:block;margin-top:3px}}
ol.tops .doc{{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--s1);
  text-decoration:none;border-bottom:1px solid rgba(57,135,229,.35)}}
.heute{{
  display:flex;align-items:center;gap:14px;margin:30px 0 6px;
  font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--s1);scroll-margin-top:16px;
}}
.heute::before,.heute::after{{content:"";flex:1;height:1px;background:var(--s1);opacity:.4}}
h2.abschnitt{{
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--s2);margin:34px 0 0;font-weight:400;
}}
</style>
</head>
<body class="lesen">

<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <nav aria-label="Bereiche">
    {navigation("./", "termine")}
  </nav>
  <span class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>
"""


def agenda_html(t: dict) -> str:
    punkte = t.get("punkte") or []
    if not punkte:
        return ""
    zeilen = []
    for p in punkte:
        dok = "".join(
            f'<a class="doc" href="{e(x["url"])}" target="_blank" '
            f'rel="noopener noreferrer">{e(x["titel"])}</a>'
            for x in p["dokumente"])
        nummer = f'<span class="sv">{e(p["vorlage"])}</span>' if p["vorlage"] else ""
        zeilen.append(
            f'      <li>{e(p["titel"])}{nummer}'
            + (f'<span class="unterlagen">{dok}</span>' if dok else "")
            + "</li>")
    wort = "Tagesordnungspunkt" if len(punkte) == 1 else "Tagesordnungspunkte"
    return (f'    <details class="agenda">\n'
            f'      <summary>{len(punkte)} {wort}</summary>\n'
            f'      <ol class="tops">\n' + "\n".join(zeilen) + "\n      </ol>\n"
            "    </details>")


def eintrag(t: dict, register: dict, vergangen: bool) -> str:
    d = dt.date.fromisoformat(t["datum"])
    jahr, kw, _ = d.isocalendar()
    ausgabe = register.get(str(jahr), {}).get(f"{kw:02d}")
    if vergangen and ausgabe:
        zustand = (f'<a href="./ausgaben/{jahr}/kw{kw:02d}.html">In der Ausgabe '
                   f'KW {kw}/{jahr}</a>')
    elif t.get("url"):
        zustand = (f'<a href="{e(t["url"])}" target="_blank" rel="noopener noreferrer">'
                   f'Im Ratsinformationssystem</a>')
    else:
        zustand = ""
    return (f'  <li>\n'
            f'    <div class="zeile">\n'
            f'      <span class="wann">{lang(d)} &middot; {t["zeit"]} Uhr</span>\n'
            f'      <span class="gremium">{e(t["gremium"])}</span>\n'
            + (f'      <span class="zustand">{zustand}</span>\n' if zustand else "")
            + '    </div>\n'
            + (agenda_html(t) + "\n" if agenda_html(t) else "")
            + "  </li>")


def main() -> None:
    quelle = DATEN / "termine.json"
    if not quelle.exists():
        raise SystemExit("data/termine.json fehlt — bitte zuerst Schritt 03 ausführen.")
    termine = json.loads(quelle.read_text(encoding="utf-8"))
    register = json.loads((DATEN / "ausgaben.json").read_text(encoding="utf-8"))
    kennzahlen = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))
    heute = dt.date.fromisoformat(kennzahlen["stichtag"])

    kuenftig = [t for t in termine if dt.date.fromisoformat(t["datum"]) > heute]
    vergangen = [t for t in termine if dt.date.fromisoformat(t["datum"]) <= heute]
    kuenftig.sort(key=lambda t: t["datum"])
    vergangen.sort(key=lambda t: t["datum"], reverse=True)

    mit_agenda = sum(1 for t in kuenftig if t.get("punkte"))

    t = [kopf("Termine"), '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Sitzungskalender</p>
  <h1>Termine</h1>
  <p class="lede">Alle öffentlichen Sitzungen der Stadt — was ansteht und was war.
  Die Sitzungen sind öffentlich, soweit nicht ausdrücklich nichtöffentlich beraten
  wird; wer hingehen möchte, kann das ohne Anmeldung.</p>
  <p class="herkunft regel">Regelbasiert zusammengestellt · keine Deutung</p>
</header>

<div class="rail">
  <div class="field"><span class="lab">Termine</span><span class="val">{len(termine)}</span></div>
  <div class="field"><span class="lab">Angekündigt</span><span class="val">{len(kuenftig)}</span></div>
  <div class="field"><span class="lab">Mit Tagesordnung</span><span class="val">{mit_agenda}</span></div>
  <div class="field"><span class="lab">Stand</span><span class="val">{lang(heute)}</span></div>
</div>

<h2 class="abschnitt">Was ansteht</h2>
<ol class="kalender">
{chr(10).join(eintrag(x, register, False) for x in kuenftig)}
</ol>

<p class="heute" id="heute">Heute &middot; {lang(heute)}</p>

<h2 class="abschnitt">Was war</h2>
<ol class="kalender">
{chr(10).join(eintrag(x, register, True) for x in vergangen)}
</ol>
""")
    t.append("</div>")
    t.append("""
<footer class="kolophon"><div class="wrap">
  <p>Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a>
  &middot; Alle Angaben und Insights ohne Gew&auml;hr</p>
  <p><a href="./index.html">Startseite</a> &middot;
     <a href="./ausgaben/index.html">Archiv</a> &middot;
     <a href="https://ris.bad-waldsee.de/termine" rel="noopener">Ratsinformationssystem</a></p>
</div></footer>
</body>
</html>""")

    ziel = DOCS / "termine.html"
    ziel.write_text("\n".join(t), encoding="utf-8")
    print(f"  {ziel.relative_to(WURZEL)}  —  {len(kuenftig)} angekündigt, "
          f"{len(vergangen)} vergangen, {ziel.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
