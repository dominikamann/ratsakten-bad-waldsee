#!/usr/bin/env python3
"""Schritt 8 — die durchsuchbare Vorgangsübersicht erzeugen.

Bisher musste man wissen, in welcher Woche etwas verhandelt wurde. Diese Seite
dreht das um: Man sucht nach einem Stichwort und bekommt den Vorgang mit seinem
gesamten Weg durch die Gremien.

Denn ein Bauleitplanverfahren erscheint nicht einmal, sondern fünf- bis achtmal —
Aufstellung, Entwurf, Auslegung, Abwägung, Satzung, oft in mehreren Gremien. Erst
diese Abfolge macht sichtbar, wie eine Entscheidung zustande gekommen ist.

Der Suchindex wird in die Seite hineingeschrieben statt nachgeladen: So
funktioniert sie auch, wenn man die Datei lokal öffnet, und es entsteht kein
weiterer Abruf.

Ergebnis: docs/suche.html

    uv run --with pypdf python scripts/08_suche_bauen.py [--stichtag JJJJ-MM-TT]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import re
from pathlib import Path

from pypdf import PdfReader

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"

ERGEBNIS = re.compile(r"Ergebnis der Beschlussfassung\s*:?\s*(.{0,70})")
VORLAGE = re.compile(r"SV-\d+/\d{4}")
# Die Protokolle schreiben das Ergebnis uneinheitlich: "Ja-Stimme(n) 18",
# "Ja-Stimmen 18" und "Ja-Stimmen: 18" kommen alle vor, ebenso "Enthaltung: 1"
# neben "Enthaltung(en) 3". Das Muster muss alle Varianten fassen — sonst fallen
# einzelne Abstimmungen still aus der Zaehlung.
AUSZAEHLUNG = re.compile(
    r"\s*Ja-Stimmen?(?:\(n\))?\s*:?\s*(\d+)"
    r"\s*Nein-Stimmen?(?:\(n\))?\s*:?\s*(\d+)"
    r"\s*Enthaltung(?:en)?(?:\(en\))?\s*:?\s*(\d+)")

BETRAG = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(Mio\.?\s*)?(?:€|Euro)")
BETRAGSSCHWELLE = 250_000

KURZ = {
    "Gemeinderat": "GR",
    "Verwaltungsausschuss": "VA",
    "Gemeinsamer Ausschuss der Vereinbarten Verwaltungsgemeinschaft "
    "Bad Waldsee-Bergatreute": "GA",
}

# Die Gremiumsnamen sind beim Einlesen am ersten Komma abgeschnitten. Aus
# "Ausschuss für Umwelt, Technik und Nachhaltigkeit" wird "Ausschuss für Umwelt".
# Deshalb wird ueber den Anfang verglichen, nicht ueber Gleichheit.
PRAEFIXE = (
    ("Ausschuss für Umwelt", "AUT"),
    ("Ausschuss für Technik", "AUT"),
    ("Gemeinsamer Ausschuss", "GA"),
    ("Ortschaftsrat", "OR"),
    ("Arbeitskreis", "AK"),
    ("Kulturbeirat", "KB"),
    ("Baumkommission", "BK"),
)


# Viele Titel nennen das Vorhaben in Anfuehrungszeichen: Bebauungsplan
# "Lohbuehl I - Erweiterung". Ein Verfahren durchlaeuft mehrere Vorlagen —
# Aufstellung, Entwurf, Abwaegung, Satzung — mit jeweils eigener Nummer. Erst
# ueber den Namen laesst es sich als ein Vorgang zusammenfuehren.
VORHABEN = re.compile(r'[„"]([^„""]{4,70})["“]')


def vorhaben(titel: str) -> str | None:
    treffer = VORHABEN.search(titel)
    if not treffer:
        return None
    name = treffer.group(1).strip(' ,.-')
    # Zu allgemein, um als Klammer zu taugen
    if len(name) < 4 or name.lower() in ("feuerwehr", "wohnen", "plex"):
        return None
    return name


def vergleichsform(name: str) -> str:
    """Schreibvarianten zusammenfuehren: „Drei-Eichen VI“ und „Drei Eichen VI“."""
    return re.sub(r"[^a-z0-9]", "", name.lower()
                  .replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                  .replace("ß", "ss"))


def kuerzel(name: str) -> str:
    if name in KURZ:
        return KURZ[name]
    for anfang, kurz in PRAEFIXE:
        if name.startswith(anfang):
            return kurz
    return "—"


def dateiname(titel: str) -> str:
    name = re.sub(r",.*", "", titel)
    name = re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", "-", name).strip("-")
    return name[:48]


def pdf_text(pfad: Path) -> str:
    try:
        roh = "\n".join(s.extract_text() or "" for s in PdfReader(pfad).pages)
    except Exception:  # noqa: BLE001
        return ""
    return re.sub(r"[­\s]+", " ", roh)


# Der Beschlusstext steht zwischen der Einleitung „Beschluss:" und der
# Ergebniszeile. Die Ueberschrift benennt den Verwaltungsvorgang, dieser Text
# sagt, was tatsaechlich entschieden wurde.
EINLEITUNG = re.compile(
    r"(?:Modifizierter Beschluss|Beschlussvorschlag an den [^:]{0,40}|Beschluss)\s*:\s*")
SEITENFUSS = re.compile(
    r"Beschlussprotokoll der öffentlichen Sitzung.{0,140}?\d+\s*von\s*\d+\s*")
TRENNUNG = re.compile(r"(\w)-\s+(?!(?:und|oder|bzw|sowie|als|wie)\b)([a-zäöüß])")


def beschlusstext(abschnitt: str, grenze: int = 900) -> str:
    treffer = list(EINLEITUNG.finditer(abschnitt))
    if not treffer:
        return ""
    roh = SEITENFUSS.sub(" ", abschnitt[treffer[-1].end():])
    roh = TRENNUNG.sub(r"\1\2", re.sub(r"\s+", " ", roh)).strip()
    if len(roh) <= grenze:
        return roh
    schnitt = roh.rfind(". ", 0, grenze)
    return (roh[:schnitt + 1] if schnitt > grenze // 2 else roh[:grenze].rstrip()) + " …"


def betrag_lesen(text: str) -> float | None:
    hoechster = None
    for m in BETRAG.finditer(text):
        wert = float(m.group(1).replace(".", "").replace(",", "."))
        if m.group(2):
            wert *= 1_000_000
        if hoechster is None or wert > hoechster:
            hoechster = wert
    return hoechster


def beschluesse_je_sitzung(text: str) -> dict[str, list[str]]:
    """Vorlagennummer -> alle Abstimmungsergebnisse in ihrer Reihenfolge.

    Eine Vorlage kann in derselben Sitzung mehrfach abgestimmt werden: Erst wird
    ueber einen Aenderungsantrag entschieden, dann ueber den Beschluss. Genau
    diese Faelle sind die aufschlussreichsten — beim Gymnasium fiel die
    Verwaltungsvariante mit 9 : 18 durch, bevor die guenstigere mit 20 : 3 : 4
    angenommen wurde. Wer nur das letzte Ergebnis behaelt, verliert die Ablehnung.
    """
    ergebnisse: dict[str, list[str]] = collections.defaultdict(list)
    betraege: dict[str, float] = {}
    texte: dict[str, str] = {}
    for treffer in ERGEBNIS.finditer(text):
        roh = treffer.group(1)
        zahlen = AUSZAEHLUNG.match(roh)
        if zahlen:
            wert = "{} : {} : {}".format(*zahlen.groups())
        elif re.match(r"\s*[Ee]instimmig", roh):
            wert = "einstimmig"
        else:
            continue
        stellen = list(VORLAGE.finditer(text[:treffer.start()]))
        if not stellen:
            continue
        vorlage = stellen[-1].group(0)
        ergebnisse[vorlage].append(wert)
        abschnitt = text[stellen[-1].start():treffer.start()]
        geld = betrag_lesen(abschnitt)
        if geld and geld >= BETRAGSSCHWELLE:
            betraege[vorlage] = max(betraege.get(vorlage, 0), geld)
        wortlaut = beschlusstext(abschnitt)
        if wortlaut and len(wortlaut) > len(texte.get(vorlage, "")):
            texte[vorlage] = wortlaut
    return dict(ergebnisse), betraege, texte


def einordnungen_laden() -> dict:
    """Redaktionelle Einordnungen aus data/einordnungen.json."""
    pfad = DATEN / "einordnungen.json"
    if not pfad.exists():
        return {}
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    return {k: v for k, v in roh.items() if not k.startswith("_")}


def ausgaben_register() -> list[tuple[str, str, str]]:
    """(von, bis, Pfad) je erschienener Ausgabe — für die Verlinkung der Stationen."""
    pfad = DATEN / "ausgaben.json"
    if not pfad.exists():
        return []
    register = json.loads(pfad.read_text(encoding="utf-8"))
    zeitraeume = []
    for jahr, ausgaben in register.items():
        for kw, a in ausgaben.items():
            if a.get("von_iso"):
                zeitraeume.append((a["von_iso"], a["bis_iso"],
                                   f"./ausgaben/{jahr}/kw{int(kw):02d}.html"))
    return sorted(zeitraeume)


def ausgabe_zu(datum: str, zeitraeume: list[tuple[str, str, str]]) -> str:
    for von, bis, pfad in zeitraeume:
        if von <= datum <= bis:
            return pfad
    return ""


def vorgaenge_sammeln(stichtag: str) -> list[dict]:
    quelle = DATEN / "sitzungen.json"
    if not quelle.exists():
        raise SystemExit(
            "data/sitzungen.json fehlt — bitte zuerst Schritt 01 ausführen.")
    sitzungen = json.loads(quelle.read_text(encoding="utf-8"))

    karte = DATEN / "topmap.json"
    if not karte.exists():
        raise SystemExit(
            "data/topmap.json fehlt — bitte zuerst Schritt 01 ausführen:\n"
            "  uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py")
    punkte = [p for p in json.loads(karte.read_text(encoding="utf-8"))
              if p["datum"] <= stichtag]
    zeitraeume = ausgaben_register()

    # Abstimmungsergebnisse einsammeln. Die Protokolle werden der jeweiligen
    # Sitzung ueber den Dateinamen zugeordnet — sonst vermischen sich Ergebnisse
    # zweier Gremien, die am selben Tag tagen.
    protokolle: dict[str, list[Path]] = {}
    for pdf in sorted((DATEN / "protokolle").glob("*.pdf")):
        protokolle.setdefault(pdf.name[:10], []).append(pdf)

    ergebnisse: dict[str, dict[str, list[str]]] = collections.defaultdict(dict)
    betraege: dict[tuple[str, str], float] = {}
    wortlaute: dict[tuple[str, str], str] = {}
    for s in sitzungen:
        datum = s["start"][:10]
        if datum > stichtag or not s["protokolle"]:
            continue
        erwartet = f"{datum}_{dateiname(s['titel'])}"
        for pdf in protokolle.get(datum, []):
            if pdf.stem != erwartet and not pdf.stem.startswith(erwartet + "_"):
                continue
            werte_je_vorlage, geld_je_vorlage, texte_je_vorlage = \
                beschluesse_je_sitzung(pdf_text(pdf))
            for vorlage, werte in werte_je_vorlage.items():
                ergebnisse[datum].setdefault(vorlage, []).extend(werte)
            for vorlage, geld in geld_je_vorlage.items():
                betraege[(datum, vorlage)] = max(betraege.get((datum, vorlage), 0), geld)
            for vorlage, wortlaut in texte_je_vorlage.items():
                wortlaute[(datum, vorlage)] = wortlaut

    # Punkte zu Vorgängen bündeln: bevorzugt über den Namen des Vorhabens,
    # sonst über die Vorlagennummer, sonst als Einzelpunkt.
    namen: dict[str, str] = {}          # Vergleichsform -> schönster Name
    for p in punkte:
        name = vorhaben(p["titel"])
        if name:
            v = vergleichsform(name)
            if v not in namen or len(name) > len(namen[v]):
                namen[v] = name

    gebuendelt: dict[str, list[dict]] = collections.defaultdict(list)
    for p in punkte:
        name = vorhaben(p["titel"])
        if name:
            schluessel = "@" + vergleichsform(name)
        elif p["vorlage"]:
            schluessel = p["vorlage"]
        else:
            schluessel = f"__{p['datum']}_{p['top']}"
        gebuendelt[schluessel].append(p)

    vorgaenge = []
    for schluessel, teile in gebuendelt.items():
        teile.sort(key=lambda p: (p["datum"], int(p["top"]) if p["top"].isdigit() else 99))
        stationen = []
        for p in teile:
            werte = ergebnisse.get(p["datum"], {}).get(p["vorlage"] or "", [])
            stationen.append({
                "d": p["datum"],
                "g": kuerzel(p["gremium"]),
                "gl": p["gremium"],
                "v": p["vorlage"] or "",
                "e": " → ".join(werte),
                "t": p["titel"],
                "a": ausgabe_zu(p["datum"], zeitraeume),
                "b": betraege.get((p["datum"], p["vorlage"] or ""), 0),
                "w": wortlaute.get((p["datum"], p["vorlage"] or ""), ""),
            })
        if schluessel.startswith("@"):
            name = namen[schluessel[1:]]
            titel = name
            nummern = sorted({p["vorlage"] for p in teile if p["vorlage"]})
        else:
            titel = max((p["titel"] for p in teile), key=len)
            nummern = sorted({p["vorlage"] for p in teile if p["vorlage"]})
        vorgaenge.append({
            "v": " · ".join(nummern),
            "t": titel,
            "u": max((p["titel"] for p in teile), key=len) if schluessel.startswith("@") else "",
            "s": stationen,
            "letzte": teile[-1]["datum"],
            "strittig": any(st["e"] and st["e"] != "einstimmig" and
                            not st["e"].endswith(": 0 : 0") for st in stationen),
            "b": max((st["b"] for st in stationen), default=0),
        })

    # Die redaktionellen Einordnungen mit aufnehmen. Sie verbinden mehrere
    # Vorgaenge ueber die Zeit — genau das, was aus den Einzelpunkten nicht
    # hervorgeht. Wer nach „Windkraft" sucht, soll auch den Befund finden,
    # dass dreimal in Folge das Einvernehmen versagt wurde.
    einordnungen = einordnungen_laden()
    ende_je_ausgabe = {}
    for von, bis, pfad in zeitraeume:
        teile = pfad.rstrip(".html").split("/")
        ende_je_ausgabe[f"{teile[-2]}-kw{int(teile[-1][2:]):02d}"] = bis
    for schluessel, ein in sorted(einordnungen.items(), reverse=True):
        jahr, kw = schluessel.split("-kw")
        pfad = f"./ausgaben/{jahr}/kw{int(kw):02d}.html"
        volltext = " ".join(ein.get("absaetze", []))
        vorgaenge.append({
            "art": "einordnung",
            "v": f"Ausgabe KW {int(kw)}/{jahr}",
            "t": ein.get("titel", ""),
            "u": volltext,
            "s": [],
            "a": pfad,
            "geprueft": ein.get("status") == "geprueft",
            "b": 0,
            # Nach dem Ende ihres Berichtszeitraums einsortieren, damit sie
            # zwischen den Vorgaengen derselben Zeit auftauchen.
            "letzte": ende_je_ausgabe.get(schluessel, f"{jahr}-01-01"),
            "strittig": False,
        })

    vorgaenge.sort(key=lambda v: v["letzte"], reverse=True)
    return vorgaenge


def bauen(vorgaenge: list[dict], stichtag: str) -> str:
    stil = (WURZEL / "scripts" / "ausgabe.css").read_text(encoding="utf-8")
    schriften = (WURZEL / "scripts" / "schriften.css").read_text(
        encoding="utf-8").replace("{PFAD}", "./")
    # "</script>" im Titel wuerde das Element vorzeitig beenden und die ganze
    # Seite lahmlegen. Die Titel stammen aus fremdem HTML — also absichern.
    index = (json.dumps(vorgaenge, ensure_ascii=False, separators=(",", ":"))
             .replace("</", "<\\/"))
    mit_beschluss = sum(1 for v in vorgaenge if any(s["e"] for s in v["s"]))
    mehrstufig = sum(1 for v in vorgaenge if len(v["s"]) > 1)

    return f"""<meta charset="utf-8">
<title>Vorgänge durchsuchen</title>
<style>{schriften}</style>
<style>{stil}</style>
<style>
.suchfeld{{
  display:flex;gap:10px;flex-wrap:wrap;margin:28px 0 0;
}}
.suchfeld input{{
  flex:1 1 320px;background:var(--surface);color:var(--ink);
  border:1px solid var(--rule);border-left:3px solid var(--s1);
  padding:15px 18px;font-family:"IBM Plex Serif",Georgia,serif;font-size:18px;
}}
.suchfeld input:focus{{outline:2px solid var(--s1);outline-offset:2px}}
.suchfeld input::placeholder{{color:var(--muted)}}
.filter{{
  display:flex;gap:8px 18px;flex-wrap:wrap;margin:14px 0 0;
  font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-2);
}}
.filter label{{cursor:pointer;display:flex;align-items:center;gap:7px}}
.trefferzahl{{
  font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin:22px 0 0;
}}
/* Das Stylesheet der Ausgaben legt fuer <article> ein zweispaltiges Raster mit
   Randspalte fest. Fuer Suchtreffer gilt das nicht — sonst wird der Titel in
   186 Pixel gequetscht und daneben bleibt die halbe Zeile leer. */
article.vorgang{{
  display:block;padding:20px 0;gap:0;
  border-bottom:1px solid var(--rule);
}}
.vorgang .kopf{{
  display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline;
}}
.vorgang h3{{
  font-family:Archivo,sans-serif;font-weight:600;font-size:17.5px;line-height:1.35;
  margin:0 0 4px;color:var(--ink);
}}
.vorgang .nr{{
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.05em;
  color:var(--muted);
}}
.achse{{
  display:flex;flex-wrap:wrap;gap:0;margin:12px 0 0;
}}
.achse .wortlaut{{
  flex:1 1 100%;margin:2px 0 12px;padding-left:12px;
  border-left:2px solid var(--rule);max-width:74ch;
  font-family:"IBM Plex Serif",Georgia,serif;font-size:14.5px;line-height:1.55;
  color:var(--ink-2);
}}
.station{{
  display:flex;align-items:baseline;gap:9px;
  padding:6px 14px 6px 0;position:relative;
}}
.station:not(:last-child)::after{{
  content:"→";color:var(--muted);opacity:.5;padding-left:14px;
}}
.station .dat{{
  font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink-2);
  font-variant-numeric:tabular-nums;white-space:nowrap;
}}
.station .grem{{
  font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.08em;
  color:var(--muted);border:1px solid var(--rule);padding:1px 5px;
}}
.station .erg{{
  font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.04em;
  color:var(--s1);white-space:nowrap;
}}
.station .erg.split{{color:var(--flag)}}
.station .svnr{{
  font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);
  opacity:.75;white-space:nowrap;
}}
.vorgang .untertitel{{color:var(--muted);font-family:"IBM Plex Serif",serif;font-size:13px}}
a.station{{text-decoration:none;color:inherit}}
a.station:hover .dat{{color:var(--s1);text-decoration:underline}}
a.station:hover .grem{{border-color:var(--s1)}}
.titellink{{color:inherit;text-decoration:none;border-bottom:1px solid var(--rule)}}
.titellink:hover{{color:var(--s1);border-bottom-color:var(--s1)}}
.vorgang.istEinordnung{{border-left:3px solid var(--flag);padding-left:18px;background:var(--flag-bg)}}
.vorgang .einleitung{{margin:8px 0 0;font-size:15.5px;line-height:1.6;color:var(--ink-2);max-width:74ch}}
.betrag{{
  padding:1px 7px;font-family:"IBM Plex Mono",monospace;font-size:10.5px;
  font-variant-numeric:tabular-nums;color:var(--s2);border:1px solid var(--s2);
  background:color-mix(in srgb, var(--s2) 8%, transparent);white-space:nowrap;
}}
.betrag.klein{{font-size:10px;padding:0 5px}}
.filter select{{
  background:var(--surface);color:var(--ink);border:1px solid var(--rule);
  font-family:"IBM Plex Mono",monospace;font-size:12px;padding:3px 6px;margin-left:6px;
}}
mark{{background:rgba(57,135,229,.25);color:var(--ink);padding:0 2px}}
.leer{{padding:40px 0;color:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:14px}}
.ohnejs{{
  margin:28px 0;padding:20px 22px;background:var(--flag-bg);
  border-left:3px solid var(--flag);
}}
.ohnejs p{{margin:0}}
</style>

<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <nav aria-label="Bereiche">
    <a href="./index.html">Startseite</a>
    <span aria-hidden="true">/</span>
    <a href="./suche.html" aria-current="page">Suche</a>
    <span aria-hidden="true">/</span>
    <a href="./ausgaben/index.html">Archiv</a>
  </nav>
  <span class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>

<div class="wrap">
<header class="masthead">
  <h1>Vorg&auml;nge</h1>
  <p class="claim">Jeder Vorgang mit seinem Weg durch die Gremien — von der ersten
  Beratung bis zum Beschluss.</p>
  <div class="issueline">
    <span><b>Vorg&auml;nge</b> {len(vorgaenge)}</span>
    <span><b>mit Beschluss</b> {mit_beschluss}</span>
    <span><b>mehrstufig</b> {mehrstufig}</span>
    <span><b>Stand</b> {stichtag[8:10]}.{stichtag[5:7]}.{stichtag[:4]}</span>
  </div>

  <div class="suchfeld">
    <input type="search" id="q" placeholder="Suchen — etwa Kindergarten, Windenergie, Steinstra&szlig;e, SV-104/2026"
           autocomplete="off" aria-label="Vorg&auml;nge durchsuchen">
  </div>
  <div class="filter">
    <label><input type="checkbox" id="f-beschluss"> nur mit Beschluss</label>
    <label><input type="checkbox" id="f-strittig"> nur nicht einstimmig</label>
    <label><input type="checkbox" id="f-mehr"> nur mehrstufige Vorg&auml;nge</label>
    <label>Betrag ab
      <select id="f-geld">
        <option value="0">beliebig</option>
        <option value="250000">250.000 &euro;</option>
        <option value="500000">500.000 &euro;</option>
        <option value="1000000">1 Mio. &euro;</option>
        <option value="5000000">5 Mio. &euro;</option>
      </select>
    </label>
  </div>

  <noscript>
    <div class="ohnejs">
      <p><b>Die Suche braucht JavaScript.</b> Ohne JavaScript lassen sich dieselben
      Daten als Tabelle auswerten: <a class="doc" href="https://github.com/dominikamann/ratsakten-bad-waldsee/blob/main/data/csv/tagesordnungspunkte.csv">tagesordnungspunkte.csv</a>
      und <a class="doc" href="https://github.com/dominikamann/ratsakten-bad-waldsee/blob/main/data/csv/beschluesse.csv">beschluesse.csv</a> —
      beide lassen sich in Excel oder LibreOffice &ouml;ffnen und filtern.</p>
    </div>
  </noscript>
</header>

<p class="trefferzahl" id="zahl"></p>
<div id="treffer"></div>

<section class="kolophon">
  <h3>Was hier steht</h3>
  <p>Ein Vorgang ist alles, was unter derselben Vorlagennummer verhandelt wurde.
  Die Kette zeigt jede Station: Datum, Gremium und — wo ein Beschlussprotokoll
  vorliegt — das Abstimmungsergebnis. Die Schreibweise <span class="mono">25 : 0 : 1</span>
  steht f&uuml;r Ja : Nein : Enthaltungen.</p>
  <p>Unter jeder Station steht der <b>beschlossene Wortlaut</b> — der Text, den das
  Gremium tatsächlich gefasst hat. Er ist aussagekräftiger als die Überschrift, die
  nur den Verwaltungsvorgang benennt. Angezeigt werden rund 340 Zeichen;
  <b>durchsucht wird der vollständige Beschluss</b>, und wenn der Treffer hinter der
  Kürzung liegt, erscheint der ganze Text. Maßgeblich bleibt das Protokoll.</p>
  <p><b>Beträge sind Fundstellen, keine Kostenangaben.</b> Angezeigt wird der größte
  im Beschlusstext genannte Betrag ab 250.000 &euro;. Das kann der Preis eines
  Vorhabens sein, aber ebenso ein Haushaltsansatz oder eine Planungsgröße — bei
  einer Haushaltssatzung etwa der Ertrag der gesamten Stadt. Maßgeblich ist der
  Beschlusstext.</p>
  <p>Punkte ohne Vorlagennummer erscheinen als einzelne Station. Gremien ohne
  ver&ouml;ffentlichte Tagesordnung — die Ortschaftsr&auml;te — fehlen hier
  vollst&auml;ndig, weil es von ihnen nichts zu indizieren gibt.</p>
  <p class="note">Mit der Vorlagennummer l&auml;sst sich jeder Vorgang im
  <a class="doc" href="https://ris.bad-waldsee.de/vorlagen" rel="noopener">Ratsinformationssystem</a>
  unter „Vorlagen“ auffinden.</p>
</section>
</div>

<footer><div class="wrap">
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
  <p>Alle Angaben und Insights ohne Gew&auml;hr &middot; Stand {stichtag}</p>
</div></footer>

<script id="daten" type="application/json">{index}</script>
<script>
(function(){{
  "use strict";
  var daten = JSON.parse(document.getElementById("daten").textContent);
  var feld  = document.getElementById("q");
  var liste = document.getElementById("treffer");
  var zahl  = document.getElementById("zahl");
  var fB = document.getElementById("f-beschluss");
  var fS = document.getElementById("f-strittig");
  var fM = document.getElementById("f-mehr");
  var fG = document.getElementById("f-geld");

  /* Umlaute und Grossschreibung sollen beim Suchen keine Rolle spielen.
     ä→ae verlaengert die Zeichenkette. Fuer die Hervorhebung brauchen wir
     deshalb zusaetzlich eine Zuordnung: welche Stelle im normalisierten Text
     gehoert zu welcher Stelle im Original? Ohne sie verrutschen die Markierungen
     um ein Zeichen je Umlaut davor. */
  var ERSATZ = {{ "ä":"ae", "ö":"oe", "ü":"ue", "ß":"ss",
                 "„":'"', "“":'"', "»":'"', "«":'"' }};

  function kuerzen(t, grenze){{
    if(t.length <= grenze) return t;
    var schnitt = t.lastIndexOf(". ", grenze);
    return (schnitt > grenze / 2 ? t.slice(0, schnitt + 1) : t.slice(0, grenze).trim()) + " …";
  }}

  function euro(n){{
    return n.toLocaleString("de-DE", {{maximumFractionDigits:0}}) + " \u20AC";
  }}

  function normal(t){{
    var aus = "";
    var lower = t.toLowerCase();
    for(var i=0;i<lower.length;i++) aus += (ERSATZ[lower[i]] || lower[i]);
    return aus;
  }}

  /* Wie normal(), liefert zusaetzlich je Zeichen der Ausgabe den Index im Original. */
  function normalMitKarte(t){{
    var aus = "", karte = [];
    var lower = t.toLowerCase();
    for(var i=0;i<lower.length;i++){{
      var e = ERSATZ[lower[i]] || lower[i];
      for(var j=0;j<e.length;j++) karte.push(i);
      aus += e;
    }}
    karte.push(lower.length);   // Endmarke
    return [aus, karte];
  }}
  daten.forEach(function(v){{ v._s = normal(v.t + " " + v.v + " " + (v.u||"") + " " + v.s.map(function(s){{return s.t + " " + (s.w||"");}}).join(" ")); }});

  function hervorheben(text, woerter){{
    var e = document.createElement("span");
    if(!woerter.length){{ e.textContent = text; return e; }}
    var rest = text, i = 0;
    var muster = new RegExp("(" + woerter.map(function(w){{
      return w.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
    }}).join("|") + ")", "gi");
    // Auf der normalisierten Fassung suchen, ueber die Karte im Original markieren
    var paar = normalMitKarte(text), norm = paar[0], karte = paar[1], treffer = [], m;
    while((m = muster.exec(norm)) !== null){{
      treffer.push([karte[m.index], karte[m.index + m[0].length]]);
      if(m.index === muster.lastIndex) muster.lastIndex++;
    }}
    treffer.forEach(function(t){{
      if(t[0] > i) e.appendChild(document.createTextNode(text.slice(i, t[0])));
      var mk = document.createElement("mark");
      mk.textContent = text.slice(t[0], t[1]);
      e.appendChild(mk); i = t[1];
    }});
    e.appendChild(document.createTextNode(text.slice(i)));
    return e;
  }}

  function zeichne(){{
    var roh = feld.value.trim();
    var woerter = normal(roh).split(/\\s+/).filter(Boolean);
    var treffer = daten.filter(function(v){{
      if(fB.checked && !v.s.some(function(s){{ return s.e; }})) return false;
      if(fS.checked && !v.strittig) return false;
      if(fM.checked && v.s.length < 2) return false;
      var schwelle = parseInt(fG.value, 10);
      if(schwelle && (v.b || 0) < schwelle) return false;
      return woerter.every(function(w){{ return v._s.indexOf(w) > -1; }});
    }});

    zahl.textContent = treffer.length === 0 ? "Kein Treffer"
      : treffer.length + (treffer.length === 1 ? " Vorgang" : " Vorgänge")
        + (roh ? " für „" + roh + "“" : "");

    liste.textContent = "";
    if(!treffer.length){{
      var l = document.createElement("p");
      l.className = "leer";
      l.textContent = "Nichts gefunden. Andere Schreibweise versuchen — die Titel "
        + "stammen wörtlich aus den Tagesordnungen.";
      liste.appendChild(l); return;
    }}

    var zeigen = treffer.slice(0, 300);
    zeigen.forEach(function(v){{
      var d = document.createElement("article");
      d.className = "vorgang" + (v.art === "einordnung" ? " istEinordnung" : "");

      var kopf = document.createElement("div");
      kopf.className = "kopf";
      var h = document.createElement("h3");
      if(v.art === "einordnung"){{
        var marke = document.createElement("span");
        marke.className = "herkunft ki";
        marke.textContent = v.geprueft ? "Einordnung" : "KI-Deutung";
        d.appendChild(marke);
      }}
      var ziel = v.a || (v.s.length ? v.s[v.s.length-1].a : "");
      if(ziel){{
        var link = document.createElement("a");
        link.href = ziel; link.className = "titellink";
        link.appendChild(hervorheben(v.t, woerter));
        h.appendChild(link);
      }} else {{
        h.appendChild(hervorheben(v.t, woerter));
      }}
      kopf.appendChild(h);
      d.appendChild(kopf);
      var teile = v.v ? v.v.split(" · ") : [];
      var nr = document.createElement("p");
      nr.className = "nr";
      if(teile.length > 4){{
        nr.textContent = teile.length + " Vorlagen · " + v.s.length + " Stationen";
      }} else if(teile.length){{
        nr.appendChild(hervorheben(v.v, woerter));
      }}
      if(v.u && v.u !== v.t){{
        var u = document.createElement("span");
        u.className = "untertitel";
        u.textContent = (teile.length ? " — " : "") + v.u;
        nr.appendChild(u);
      }}
      if(nr.textContent) kopf.appendChild(nr);
      if(v.b){{
        var geld = document.createElement("span");
        geld.className = "betrag";
        geld.title = "größter im Beschlusstext genannter Betrag — nicht zwingend die Kosten";
        geld.textContent = euro(v.b);
        kopf.appendChild(geld);
      }}

      if(v.art === "einordnung"){{
        var txt = document.createElement("p");
        txt.className = "einleitung";
        txt.appendChild(hervorheben(v.u.slice(0, 320) + (v.u.length > 320 ? " …" : ""), woerter));
        d.appendChild(txt);
        liste.appendChild(d);
        return;
      }}
      var achse = document.createElement("div");
      achse.className = "achse";
      v.s.forEach(function(s){{
        var st = document.createElement(s.a ? "a" : "div");
        st.className = "station";
        if(s.a){{ st.href = s.a; st.title = "Zur Ausgabe dieser Woche"; }}
        var dat = document.createElement("span");
        dat.className = "dat";
        dat.textContent = s.d.slice(8,10) + "." + s.d.slice(5,7) + "." + s.d.slice(0,4);
        st.appendChild(dat);
        var g = document.createElement("span");
        g.className = "grem"; g.textContent = s.g; g.title = s.gl;
        st.appendChild(g);
        if(s.v){{
          var nr = document.createElement("span");
          nr.className = "svnr"; nr.textContent = s.v; nr.title = s.t;
          st.appendChild(nr);
        }}
        if(s.b){{
          var g = document.createElement("span");
          g.className = "betrag klein"; g.textContent = euro(s.b);
          g.title = "größter im Beschlusstext genannter Betrag";
          st.appendChild(g);
        }}
        if(s.e){{
          var e = document.createElement("span");
          e.className = "erg" + (s.e !== "einstimmig" && !/: 0 : 0$/.test(s.e) ? " split" : "");
          e.textContent = s.e;
          st.appendChild(e);
        }}
        achse.appendChild(st);
        if(s.w){{
          var w = document.createElement("p");
          w.className = "wortlaut";
          // Gesucht wird im vollen Wortlaut, angezeigt eine gekuerzte Fassung —
          // es sei denn, der Treffer liegt hinter der Kuerzung.
          var kurz = kuerzen(s.w, 340);
          var zeigen = (woerter.length && normal(kurz).indexOf(woerter[0]) === -1
                        && normal(s.w).indexOf(woerter[0]) > -1) ? s.w : kurz;
          w.appendChild(hervorheben(zeigen, woerter));
          achse.appendChild(w);
        }}
      }});
      d.appendChild(achse);
      liste.appendChild(d);
    }});

    if(treffer.length > zeigen.length){{
      var mehr = document.createElement("p");
      mehr.className = "leer";
      mehr.textContent = "… und " + (treffer.length - zeigen.length)
        + " weitere. Suche eingrenzen.";
      liste.appendChild(mehr);
    }}
  }}

  feld.addEventListener("input", zeichne);
  [fB, fS, fM, fG].forEach(function(f){{ f.addEventListener("change", zeichne); }});
  zeichne();
}})();
</script>
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stichtag", default=dt.date.today().isoformat())
    args = p.parse_args()

    vorgaenge = vorgaenge_sammeln(args.stichtag)
    DOCS.mkdir(exist_ok=True)
    ziel = DOCS / "suche.html"
    ziel.write_text(bauen(vorgaenge, args.stichtag), encoding="utf-8")

    mehrstufig = sum(1 for v in vorgaenge if len(v["s"]) > 1)
    print(f"  {ziel.relative_to(WURZEL)}  —  {len(vorgaenge)} Vorgänge, "
          f"{mehrstufig} mehrstufig, {ziel.stat().st_size / 1024:.0f} KB")
    if vorgaenge:
        laengste = max(vorgaenge, key=lambda v: len(v["s"]))
        print(f"  längster Vorgang: {len(laengste['s'])} Stationen — "
              f"{laengste['v']} {laengste['t'][:60]}")
    else:
        print("  Achtung: kein Vorgang bis zum Stichtag — die Seite bleibt leer.")

    # Kennzahlen fuer die Startseite, damit sie nicht aus dem HTML gelesen
    # werden muessen (Befund aus dem Code-Review).
    (DATEN / "suche.json").write_text(json.dumps({
        "vorgaenge": len(vorgaenge),
        "mehrstufig": mehrstufig,
        "stichtag": args.stichtag,
    }, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
