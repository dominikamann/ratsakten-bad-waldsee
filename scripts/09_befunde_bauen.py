#!/usr/bin/env python3
"""Schritt 9 — alle Befunde an einem Ort sammeln.

Die interessanten Erkenntnisse lagen verstreut: vier Befunde und zehn kritische
Beobachtungen im Report, acht Einordnungen in einzelnen Wochenausgaben. Über die
Suche waren sie erreichbar — aber nur, wenn man das richtige Stichwort erriet.

Diese Seite führt sie zusammen. Sie erzeugt nichts Neues und deutet nichts
zusätzlich; sie sammelt, was an anderer Stelle bereits steht, und verweist dorthin.

Die Report-Inhalte werden strukturiert aus dem erzeugten Dokument gelesen, nicht
per Textmuster. Stimmt die erwartete Anzahl nicht, bricht der Lauf ab — eine
stillschweigend halbleere Seite wäre schlimmer als ein Fehler.

Ergebnis: docs/befunde.html

    uv run --with lxml python scripts/09_befunde_bauen.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

from lxml import html as H

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"

ERWARTET_BEFUNDE = 4
ERWARTET_BEOBACHTUNGEN = 10

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


def e(t: str) -> str:
    return html.escape(str(t), quote=False)


def juengster_report() -> Path | None:
    kandidaten = sorted((DOCS / "report").glob("*.html")) if (DOCS / "report").exists() else []
    return kandidaten[-1] if kandidaten else None


def aus_report(pfad: Path) -> tuple[list[dict], list[dict]]:
    """Befund-Kästen und kritische Beobachtungen strukturiert auslesen."""
    baum = H.parse(str(pfad)).getroot()

    befunde = []
    for kasten in baum.xpath('//div[contains(@class,"befund")]'):
        titel = kasten.xpath('.//p[@class="lab"]/text()')
        if not titel or "Lernprojekt" in titel[0]:
            continue          # der Haftungshinweis nutzt dieselbe Auszeichnung
        absaetze = [" ".join(p.xpath('.//text()')).strip()
                    for p in kasten.xpath('./p[not(@class)]')]
        kapitel = kasten.xpath('ancestor::section/p[@class="sec-no"]/text()')
        befunde.append({
            "titel": titel[0].strip(),
            "absaetze": [a for a in absaetze if a],
            "kapitel": kapitel[0].strip() if kapitel else "",
        })

    beobachtungen = []
    for li in baum.xpath('//ol[@id="concerns"]/li'):
        kopf = li.xpath('./p[@class="c-head"]/text()')
        absaetze = [" ".join(p.xpath('.//text()')).strip()
                    for p in li.xpath('./p[not(@class)]')]
        beleg = li.xpath('./p[@class="evidence"]/text()')
        beobachtungen.append({
            "titel": kopf[0].strip() if kopf else "",
            "absaetze": [a for a in absaetze if a],
            "beleg": beleg[0].strip() if beleg else "",
        })

    if len(befunde) != ERWARTET_BEFUNDE or len(beobachtungen) != ERWARTET_BEOBACHTUNGEN:
        sys.exit(
            f"Report unerwartet aufgebaut: {len(befunde)} Befunde (erwartet "
            f"{ERWARTET_BEFUNDE}), {len(beobachtungen)} Beobachtungen (erwartet "
            f"{ERWARTET_BEOBACHTUNGEN}).\nHat sich die Auszeichnung in src/report.html "
            f"geändert? Dann sind die Erwartungswerte in diesem Skript nachzuziehen.")
    return befunde, beobachtungen


def aus_einordnungen() -> list[dict]:
    pfad = DATEN / "einordnungen.json"
    if not pfad.exists():
        return []
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    register = json.loads((DATEN / "ausgaben.json").read_text(encoding="utf-8")) \
        if (DATEN / "ausgaben.json").exists() else {}

    eintraege = []
    for schluessel, ein in roh.items():
        if schluessel.startswith("_"):
            continue
        jahr, kw = schluessel.split("-kw")
        meta = register.get(jahr, {}).get(f"{int(kw):02d}", {})
        eintraege.append({
            "titel": ein.get("titel", ""),
            "absaetze": ein.get("absaetze", []),
            "geprueft": ein.get("status") == "geprueft",
            "quelle": f"Aktenlage KW {int(kw)}/{jahr}",
            "zeitraum": meta.get("zeitraum", ""),
            "sortier": meta.get("bis_iso", f"{jahr}-01-01"),
            "pfad": f"./ausgaben/{jahr}/kw{int(kw):02d}.html",
        })
    return sorted(eintraege, key=lambda x: x["sortier"], reverse=True)


def block(titel: str, absaetze: list[str], quelle: str, pfad: str,
          beleg: str = "", geprueft: bool = False) -> str:
    marke = ('<p class="herkunft geprueft">Redaktionell geprüft</p>' if geprueft else
             '<p class="herkunft ki">KI-Deutung · nicht redaktionell geprüft</p>')
    text = "\n".join(f"    <p>{e(a)}</p>" for a in absaetze)
    belegzeile = f'\n    <p class="evidence">{e(beleg)}</p>' if beleg else ""
    return f"""  <article class="befundblock">
    {marke}
    <h3>{e(titel)}</h3>
{text}{belegzeile}
    <p class="quelle"><a class="doc" href="{pfad}">{e(quelle)}</a></p>
  </article>"""


def bauen() -> str:
    stil = (WURZEL / "scripts" / "ausgabe.css").read_text(encoding="utf-8")
    schriften = (WURZEL / "scripts" / "schriften.css").read_text(
        encoding="utf-8").replace("{PFAD}", "./")

    report = juengster_report()
    if not report:
        sys.exit("Kein Report in docs/report/ — bitte zuerst Schritt 04 ausführen.")
    befunde, beobachtungen = aus_report(report)
    einordnungen = aus_einordnungen()
    rpfad = f"./report/{report.name}"
    rname = f"Ratsanalyse, Stand {report.stem[8:10]}.{report.stem[5:7]}.{report.stem[:4]}"

    teile = [f"""<meta charset="utf-8">
<title>Befunde</title>
<style>{schriften}</style>
<style>{stil}</style>
<style>
.befundblock{{
  display:block;padding:26px 0 22px;border-bottom:1px solid var(--rule);gap:0;
}}
.befundblock h3{{
  font-family:Archivo,sans-serif;font-weight:600;font-size:20px;line-height:1.3;
  margin:0 0 12px;color:var(--ink);letter-spacing:-.01em;
}}
.befundblock p{{max-width:72ch}}
.befundblock .quelle{{
  margin:14px 0 0;font-family:"IBM Plex Mono",monospace;font-size:11px;
  letter-spacing:.05em;color:var(--muted);
}}
.befundblock .evidence{{
  margin-top:12px;padding-top:10px;border-top:1px solid var(--rule);
  font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  letter-spacing:.02em;max-width:74ch;
}}
.gruppe{{padding:44px 0 0}}
.gruppe > h2{{
  font-family:Archivo,sans-serif;font-weight:700;font-size:26px;
  letter-spacing:-.02em;margin:0 0 6px;
}}
.gruppe > .einleitung{{color:var(--ink-2);max-width:70ch;margin:0 0 4px}}
</style>

<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <nav aria-label="Bereiche">
    <a href="./index.html">Startseite</a>
    <span aria-hidden="true">/</span>
    <a href="./suche.html">Suche</a>
    <span aria-hidden="true">/</span>
    <a href="./befunde.html" aria-current="page">Befunde</a>
    <span aria-hidden="true">/</span>
    <a href="./ausgaben/index.html">Archiv</a>
  </nav>
  <span class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>

<div class="wrap">
<header class="masthead">
  <h1>Befunde</h1>
  <p class="claim">Alles, was über das Auszählen hinausgeht — an einem Ort statt
  verstreut über Report und Wochenausgaben.</p>
  <div class="issueline">
    <span><b>Befunde</b> {len(befunde)}</span>
    <span><b>kritische Beobachtungen</b> {len(beobachtungen)}</span>
    <span><b>Einordnungen</b> {len(einordnungen)}</span>
    <span><b>Herkunft</b> KI-Deutung</span>
  </div>

  <div class="kasten warn">
    <p class="lab">Was auf dieser Seite steht</p>
    <p>Ausschließlich <b>KI-Deutungen</b>: Auswahl, Verknüpfung und Gewichtung von
    Fakten, maschinell erzeugt und <b>nicht redaktionell geprüft</b>. Die zugrunde
    liegenden Zahlen stammen aus den Beschlussprotokollen und sind dort nachprüfbar
    — die daraus gezogene Schlussfolgerung ist es nicht.</p>
    <p>Diese Seite erzeugt nichts Neues. Jeder Eintrag verweist auf die Stelle, an
    der er im Zusammenhang steht.</p>
  </div>
</header>"""]

    teile.append(f"""
<section class="gruppe">
  <h2>Kritische Beobachtungen</h2>
  <p class="einleitung">Stellen, an denen die Aktenlage Fragen offenlässt oder ein
  Verfahren formal korrekt, in seiner Wirkung aber fragwürdig ist. Keine Vorwürfe —
  jeder Punkt nennt seinen Beleg.</p>""")
    for b in beobachtungen:
        teile.append(block(b["titel"], b["absaetze"], rname, rpfad, beleg=b["beleg"]))
    teile.append("</section>")

    teile.append("""
<section class="gruppe">
  <h2>Befunde aus der Gesamtauswertung</h2>
  <p class="einleitung">Was beim Auszählen aller Sitzungen sichtbar wurde und in
  einer einzelnen Woche nicht zu erkennen ist.</p>""")
    for b in befunde:
        quelle = f"{rname} · {b['kapitel']}" if b["kapitel"] else rname
        teile.append(block(b["titel"], b["absaetze"], quelle, rpfad))
    teile.append("</section>")

    teile.append("""
<section class="gruppe">
  <h2>Einordnungen aus den Wochenausgaben</h2>
  <p class="einleitung">Was in der jeweiligen Woche bemerkenswert war — oft erst
  im Vergleich mit früheren Sitzungen erkennbar.</p>""")
    for ein in einordnungen:
        quelle = (f"{ein['quelle']} · {ein['zeitraum']}" if ein["zeitraum"]
                  else ein["quelle"])
        teile.append(block(ein["titel"], ein["absaetze"], quelle, ein["pfad"],
                           geprueft=ein["geprueft"]))
    teile.append("</section>")

    heute = dt.date.today()
    teile.append(f"""
<section class="kolophon" style="border-bottom:none">
  <h3>Warum diese Seite existiert</h3>
  <p>Die Zahlen dieses Projekts sind auszählbar und reproduzierbar. Was darüber
  hinausgeht — dass eine Enthaltung ausgerechnet bei dem Verfahren fiel, gegen das
  eine Fachbehörde Bedenken hatte, oder dass dreimal in Folge dasselbe abgelehnt
  wurde — entsteht erst durch Vergleich über die Zeit.</p>
  <p>Solche Aussagen lagen verstreut in einzelnen Wochenausgaben und Kapiteln. Wer
  sie finden wollte, musste das richtige Stichwort raten. Hier stehen sie
  zusammen, klar als Deutung gekennzeichnet und jeweils mit Weg zur Quelle.</p>
  <p class="note">Erzeugt am {heute.strftime('%d.%m.%Y')} aus
  <span class="mono">docs/report/{report.name}</span> und
  <span class="mono">data/einordnungen.json</span>.</p>
</section>
</div>

<footer><div class="wrap">
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
  <p>Alle Angaben und Insights ohne Gew&auml;hr &middot; sämtlich KI-Deutung</p>
</div></footer>""")
    return "\n".join(teile)


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    ziel = DOCS / "befunde.html"
    ziel.write_text(bauen(), encoding="utf-8")
    print(f"  {ziel.relative_to(WURZEL)}  —  {ziel.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
