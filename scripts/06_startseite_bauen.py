#!/usr/bin/env python3
"""Schritt 6 — die Startseite aus den Daten erzeugen.

Bis hierher war die Startseite handgepflegt: Kennzahlen, der Link auf die neueste
Ausgabe und die Zahl der Ausgaben standen als fester Text darin. Das veraltet
wöchentlich und fällt niemandem auf, weil die Seite weiter funktioniert — sie
zeigt nur auf die falsche Ausgabe.

Jetzt kommt alles aus den Dateien, die die Verarbeitungskette ohnehin schreibt:
  data/kennzahlen.json   die Kennzahlen (Schritt 3)
  data/ausgaben.json     das Ausgabenregister (Schritt 5)
  docs/report/*.html     der jüngste Report

Ergebnis: docs/index.html

    uv run python scripts/06_startseite_bauen.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

ZAHLWORT = {
    1: "Eine", 2: "Zwei", 3: "Drei", 4: "Vier", 5: "Fünf", 6: "Sechs",
    7: "Sieben", 8: "Acht", 9: "Neun", 10: "Zehn", 11: "Elf", 12: "Zwölf",
    13: "Dreizehn", 14: "Vierzehn", 15: "Fünfzehn", 16: "Sechzehn",
    17: "Siebzehn", 18: "Achtzehn", 19: "Neunzehn", 20: "Zwanzig",
    21: "Einundzwanzig", 22: "Zweiundzwanzig", 23: "Dreiundzwanzig",
    24: "Vierundzwanzig", 25: "Fünfundzwanzig",
}


def e(t: str) -> str:
    return html.escape(str(t), quote=False)


def datum_lang(d: dt.date) -> str:
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def zahlwort(n: int) -> str:
    return ZAHLWORT.get(n, str(n))


def juengster_report() -> tuple[str, dt.date] | None:
    """Neueste Datei in docs/report/, benannt nach ihrem Stichtag."""
    kandidaten = sorted((DOCS / "report").glob("*.html")) if (DOCS / "report").exists() else []
    if not kandidaten:
        return None
    neuester = kandidaten[-1]
    try:
        stand = dt.date.fromisoformat(neuester.stem)
    except ValueError:
        stand = dt.date.fromtimestamp(neuester.stat().st_mtime)
    return f"./report/{neuester.name}", stand


def neueste_ausgabe(register: dict) -> tuple[str, int, int, dict] | None:
    if not register:
        return None
    jahr = max(register, key=int)
    if not register[jahr]:
        return None
    kw = max(register[jahr], key=int)
    return f"./ausgaben/{jahr}/kw{int(kw):02d}.html", int(jahr), int(kw), register[jahr][kw]


def bauen() -> str:
    kennzahlen = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))
    register = json.loads((DATEN / "ausgaben.json").read_text(encoding="utf-8"))
    stil = (WURZEL / "scripts" / "startseite.css").read_text(encoding="utf-8")

    a = kennzahlen["abstimmungen"]
    kacheln = [
        (kennzahlen["sitzungen"], "Sitzungen"),
        (kennzahlen["tagesordnungspunkte"], "Tagesordnungs-<br>punkte"),
        (kennzahlen["vorlagen"], "Vorlagen"),
        (kennzahlen["protokolle"], "Protokolle"),
        (a["gesamt"], "Abstimmungen"),
    ]
    kachel_html = "\n".join(
        f'    <div class="tile"><span class="v">{v}</span><span class="k">{t}</span></div>'
        for v, t in kacheln)

    karten = []

    report = juengster_report()
    if report:
        pfad, stand = report
        karten.append(f"""    <a class="karte" href="{pfad}">
      <p class="art">Report &middot; Vollauswertung</p>
      <h3>Ratsanalyse Bad Waldsee</h3>
      <p>Auswertung der gesamten dokumentierten Gremienarbeit: Transparenz, Themen,
      Abstimmungsverhalten, Finanzen — dazu die 50 auff&auml;lligsten Tagesordnungspunkte
      und zehn kritische Beobachtungen.</p>
      <p class="meta">Stand {datum_lang(stand)} &middot; 8 Kapitel &middot; 5 Diagramme</p>
    </a>""")

    aktuell = neueste_ausgabe(register)
    if aktuell:
        pfad, jahr, kw, meta = aktuell
        n_b = meta["beschluesse"]
        beschreibung = (
            f"{n_b} {'Beschluss' if n_b == 1 else 'Beschl&uuml;sse'} mit Vorlagennummer und "
            f"Stimmenverh&auml;ltnis" if n_b else
            "In diesem Berichtszeitraum wurde kein Beschlussprotokoll ver&ouml;ffentlicht")
        if meta["ohne_protokoll"]:
            beschreibung += (f", dazu {meta['ohne_protokoll']} &ouml;ffentliche "
                             f"{'Sitzung' if meta['ohne_protokoll'] == 1 else 'Sitzungen'} "
                             f"ohne Protokoll")
        karten.append(f"""    <a class="karte" href="{pfad}">
      <p class="art">Aktenlage &middot; aktuelle Ausgabe</p>
      <h3>Waldseer Aktenlage, KW {kw}/{jahr}</h3>
      <p>Was der Gemeinderat und seine Aussch&uuml;sse zuletzt entschieden haben.
      {beschreibung}.</p>
      <p class="meta">Berichtszeitraum {e(meta['zeitraum'])}</p>
    </a>""")

    if register:
        ges_a = sum(len(v) for v in register.values())
        ges_b = sum(x["beschluesse"] for v in register.values() for x in v.values())
        ges_o = sum(x["ohne_protokoll"] for v in register.values() for x in v.values())
        jahre = sorted(register, reverse=True)
        spanne = (f"Jahrg&auml;nge {jahre[-1]}–{jahre[0]}" if len(jahre) > 1
                  else f"Jahrgang {jahre[0]}")
        karten.append(f"""    <a class="karte" href="./ausgaben/index.html">
      <p class="art">Aktenlage &middot; Archiv</p>
      <h3>Alle bisherigen Ausgaben</h3>
      <p>{zahlwort(ges_a)} Ausgaben mit zusammen {ges_b} Beschl&uuml;ssen — dazu {ges_o}
      &ouml;ffentliche Sitzungen, von denen kein Protokoll existiert.</p>
      <p class="meta">{spanne} &middot; maschinell erzeugt</p>
    </a>""")

    heute = dt.date.today()
    stichtag = kennzahlen.get("stichtag", heute.isoformat())

    return f"""<meta charset="utf-8">
<title>Ratsakten Bad Waldsee</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&amp;family=IBM+Plex+Mono:wght@400;500&amp;family=IBM+Plex+Serif:wght@400;500&amp;display=swap">
<style>{stil}</style>

<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <span>Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>

<div class="wrap">

<header>
  <p class="eyebrow">Lernprojekt &middot; Kommunaldaten</p>
  <h1>Ratsakten Bad Waldsee</h1>
  <p class="lede">Kommunalpolitik ist &ouml;ffentlich — aber nicht zug&auml;nglich. Dieses
  Projekt wertet die frei verf&uuml;gbaren Sitzungsunterlagen der Stadt Bad Waldsee
  maschinell aus und macht daraus etwas Lesbares.</p>

  <div class="tiles">
{kachel_html}
  </div>
</header>

<section>
  <h2>Ver&ouml;ffentlichungen</h2>
  <div class="karten">
{chr(10).join(karten)}
  </div>
</section>

<section>
  <h2>Worum es geht</h2>
  <p>Lokaljournalismus ist vielerorts zur&uuml;ckgegangen, w&auml;hrend kommunale Unterlagen
  so vollst&auml;ndig online stehen wie nie. Dazwischen klafft eine L&uuml;cke: Die
  Information ist &ouml;ffentlich, aber praktisch ungelesen — nicht weil sie geheim w&auml;re,
  sondern weil niemand die Zeit hat, Bebauungsplanverfahren und Geb&uuml;hrenkalkulationen
  durchzuarbeiten.</p>
  <p>Das Projekt geht drei technischen Fragen nach:</p>
  <ul class="plain">
    <li>Wie gut lassen sich kommunale Ratsinformationssysteme maschinell erschlie&szlig;en?</li>
    <li>Wie viel Substanz steckt tats&auml;chlich in den Dokumenten — und wie viel ist Formalie?</li>
    <li>Wo endet das, was aus Akten allein erkennbar ist?</li>
  </ul>
  <p>Alle Auswertungen beruhen ausschlie&szlig;lich auf &ouml;ffentlich zug&auml;nglichen
  Dokumenten des <a href="https://ris.bad-waldsee.de/" rel="noopener">Ratsinformationssystems</a>
  und der <a href="https://www.bad-waldsee.de/buerger/de/rathaus-service/aktuelles-bekanntmachungen/oeffentliche-bekanntmachungen" rel="noopener">&ouml;ffentlichen
  Bekanntmachungen</a>. Es wurden keine Zugangsbeschr&auml;nkungen umgangen.</p>
</section>

<section style="border-bottom:none">
  <h2>Hinweise</h2>
  <div class="hinweis">
    <p class="lab">Lernprojekt &middot; keine Gew&auml;hr &middot; keine Vorw&uuml;rfe</p>
    <p><b>Dies ist ein privates Lern- und Technikprojekt</b> zur automatisierten Auswertung
    &ouml;ffentlich zug&auml;nglicher Verwaltungsdokumente. Es ist kein journalistisches
    Erzeugnis, kein Pr&uuml;fbericht und keine rechtliche oder fachliche Bewertung.</p>
    <p><b>F&uuml;r Richtigkeit, Vollst&auml;ndigkeit und Aktualit&auml;t wird keine
    Gew&auml;hr &uuml;bernommen.</b> Alle Auswertungen beruhen auf maschineller Verarbeitung
    von PDF-Dokumenten; Fehler bei Texterkennung und Zuordnung sind m&ouml;glich. Verbindlich
    ist ausschlie&szlig;lich das jeweilige Originaldokument der Stadt Bad Waldsee.</p>
    <p><b>Es werden keine Vorw&uuml;rfe erhoben.</b> Weder der Stadtverwaltung noch einzelnen
    Personen wird rechtswidriges oder schuldhaftes Verhalten unterstellt. Einordnungen sind
    gekennzeichnet und stellen die pers&ouml;nliche Einsch&auml;tzung des Autors dar.</p>
    <p><b>Korrekturen sind erw&uuml;nscht</b> und werden zeitnah eingearbeitet. Es besteht
    keine Verbindung zur Stadt Bad Waldsee.</p>
  </div>
</section>

</div>

<footer><div class="wrap">
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
  <p>Alle Angaben und Insights ohne Gew&auml;hr &middot; Datenstand {e(stichtag)}
  &middot; Seite erzeugt am {heute.strftime('%d.%m.%Y')}</p>
</div></footer>
"""


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(bauen(), encoding="utf-8")
    register = json.loads((DATEN / "ausgaben.json").read_text(encoding="utf-8"))
    aktuell = neueste_ausgabe(register)
    print("docs/index.html erzeugt"
          + (f" — verlinkt auf KW {aktuell[2]}/{aktuell[1]}" if aktuell else ""))


if __name__ == "__main__":
    main()
