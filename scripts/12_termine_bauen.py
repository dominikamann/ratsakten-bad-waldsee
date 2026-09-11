"""Schritt 12 — der vollstaendige Sitzungskalender.

Die Startseite zeigt die naechsten zehn Termine, das Archiv die erschienenen
Ausgaben. Was fehlte, war der Kalender selbst: alle Sitzungen, vergangene wie
kuenftige, an einem Ort.

Eine durchgehende Reihe, aelteste Sitzung zuerst, mit dem heutigen Tag an seiner
Stelle darin. Zwei gegenlaeufige Listen — Kuenftiges vorwaerts, Vergangenes
rueckwaerts — lasen sich beim Scrollen wie ein Bruch. Der Anker „#heute" fuehrt
auf den heutigen Tag; darauf zeigt auch der Menueeintrag.

Jede vergangene Sitzung verweist auf die Wochenausgabe, in der sie ausgewertet
ist; jede Sitzung mit veroeffentlichter Tagesordnung laesst diese aufklappen.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from seite import e, fuss, kopf, kurz, lang

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"

EIGEN = """
/* Nur diese Seite braucht die Kalenderliste: eine durchgehende Reihe mit
   Jahresmarken und dem heutigen Tag an seiner Stelle darin. */
ol.kalender{list-style:none;margin:18px 0 0;padding:0}
ol.kalender > li{padding:13px 0 15px;border-top:1px solid var(--rule)}
ol.kalender > li:last-child{border-bottom:1px solid var(--rule)}
.zeile{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px}
.zeile .wann,.zeile .gremium{margin:0}
.zeile .zustand{margin-left:auto}
/* Der heutige Tag steht als Marke in der Reihe — nicht am Anfang der Seite,
   sondern dort, wo er chronologisch hingehoert. */
li.marke{
  border-top:none;padding:22px 0 8px;display:flex;align-items:center;gap:14px;
  font-family:var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--s1);font-size:11.5px;
}
li.marke::before,li.marke::after{
  content:"";flex:1;height:1px;background:currentColor;opacity:.3;
}
/* Jahresmarke: das laufende Jahr als Ueberschrift, die zurueckliegenden als
   zugeklappter Block. Beide sehen gleich aus, damit die Reihe nicht bricht. */
h2.jahrmarke,details.jahrblock > summary{
  display:flex;align-items:baseline;gap:14px;margin:34px 0 0;padding:10px 0;
  border-bottom:1px solid var(--rule);
  font-family:var(--sans);font-weight:700;font-size:20px;letter-spacing:-.01em;
  color:var(--ink);
}
details.jahrblock > summary{cursor:pointer;list-style:none}
details.jahrblock > summary::-webkit-details-marker{display:none}
details.jahrblock > summary::after{
  content:"aufklappen";margin-left:auto;font-family:var(--mono);font-weight:400;
  font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--s1);
}
details.jahrblock[open] > summary::after{content:"zuklappen"}
details.jahrblock > summary:hover{color:var(--s1)}
.anzahl{
  font-family:var(--mono);font-weight:400;font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);
}
.sprungmarken{
  display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin:22px 0 0;
  font-family:var(--mono);font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;
}
.sprungmarken .jetzt{
  padding:7px 14px;border:1px solid var(--s1);color:var(--s1);text-decoration:none;
}
.sprungmarken .jetzt:hover{background:rgba(57,135,229,.10)}
.sprungmarken .jahre{display:flex;gap:12px;color:var(--muted)}
.sprungmarken .jahre a{color:var(--muted);text-decoration:none}
.sprungmarken .jahre a:hover{color:var(--s1)}
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

    # Eine durchgehende Chronik, aelteste Sitzung zuerst. Zwei gegenlaeufige
    # Listen — Kuenftiges vorwaerts, Vergangenes rueckwaerts — lasen sich beim
    # Scrollen wie ein Bruch. Der heutige Tag steht an seiner Stelle in der
    # Reihe; dorthin fuehrt eine Sprungmarke.
    termine.sort(key=lambda t: (t["datum"], t["zeit"]))
    kuenftig = [t for t in termine if dt.date.fromisoformat(t["datum"]) > heute]
    mit_agenda = sum(1 for t in kuenftig if t.get("punkte"))

    # Jahrgaenge, die nicht das laufende Jahr sind, stehen zugeklappt da. Sonst
    # scrollt man durch zwei volle Jahre, ehe das laufende beginnt — die Reihe
    # bleibt durchgehend, sie faengt nur nicht mehr 2024 an.
    jahre = sorted({dt.date.fromisoformat(x["datum"]).year for x in termine} | {heute.year})
    je_jahr: dict[int, list[str]] = {j: [] for j in jahre}
    heute_gesetzt = False
    marke = (f'  <li class="marke" id="heute"><span>Heute &middot; '
             f'{lang(heute)}</span></li>')
    for x in termine:
        d = dt.date.fromisoformat(x["datum"])
        if not heute_gesetzt and d > heute:
            je_jahr[heute.year].append(marke)
            heute_gesetzt = True
        je_jahr[d.year].append(eintrag(x, register, d <= heute))
    if not heute_gesetzt:                     # alle Termine liegen zurueck
        je_jahr[heute.year].append(marke)

    bloecke: list[str] = []
    for j in jahre:
        liste = f'<ol class="kalender">\n{chr(10).join(je_jahr[j])}\n</ol>'
        anzahl = sum(1 for x in termine if x["datum"].startswith(str(j)))
        wort = "Sitzung" if anzahl == 1 else "Sitzungen"
        if j == heute.year:
            bloecke.append(f'<h2 class="jahrmarke" id="jahr{j}">{j}'
                           f'<span class="anzahl">{anzahl} {wort}</span></h2>\n{liste}')
        else:
            bloecke.append(
                f'<details class="jahrblock" id="jahr{j}">\n'
                f'  <summary>{j}<span class="anzahl">{anzahl} {wort}</span></summary>\n'
                f'{liste}\n</details>')

    sprung = " &middot; ".join(f'<a href="#jahr{j}">{j}</a>' for j in jahre)

    t = [kopf("Termine · Ratsakten Bad Waldsee", hier="termine",
          beschreibung="Alle öffentlichen Sitzungen der Stadt Bad Waldsee — vergangene wie angekündigte — in einer durchgehenden Reihe.",
          stile=("ausgabe.css", "termine.css"), eigen=EIGEN),
     '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Sitzungskalender</p>
  <h1>Termine</h1>
  <p class="lede">Alle öffentlichen Sitzungen der Stadt in einer durchgehenden Reihe —
  von der ersten erfassten Sitzung bis zum letzten angekündigten Termin. Die Sitzungen
  sind öffentlich, soweit nicht ausdrücklich nichtöffentlich beraten wird; wer hingehen
  möchte, kann das ohne Anmeldung.</p>
  <div class="issueline">
    <span><b>Termine</b> {len(termine)}</span>
    <span><b>angekündigt</b> {len(kuenftig)}</span>
    <span><b>mit Tagesordnung</b> {mit_agenda}</span>
    <span><b>Stand</b> {kurz(heute)}</span>
    <span><b>Herkunft</b> regelbasiert gezählt</span>
  </div>
</header>

<p class="sprungmarken"><a class="jetzt" href="#heute">Zum heutigen Tag</a>
<span class="jahre">{sprung}</span></p>

{chr(10).join(bloecke)}
""")
    t.append("</div>")
    t.append(fuss(meta=f"Stand {lang(heute)}"))

    ziel = DOCS / "termine.html"
    ziel.write_text("\n".join(t), encoding="utf-8")
    print(f"  {ziel.relative_to(WURZEL)}  —  {len(termine)} Termine, "
          f"{len(kuenftig)} angekündigt, {ziel.stat().st_size // 1024} KB")

if __name__ == "__main__":
    main()
