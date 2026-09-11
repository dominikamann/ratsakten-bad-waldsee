#!/usr/bin/env python3
"""Prüfung — kontrolliert das erzeugte Ergebnis, bevor es veröffentlicht wird.

Läuft am Ende des Wochenlaufs und zusätzlich bei jedem Push auf GitHub. Findet
sie einen Fehler, endet sie mit einem Fehlercode und der Lauf bricht ab.

Geprüft wird:
  1. Jeder interne Verweis in docs/ zeigt auf eine vorhandene Datei
  2. Jede eingebundene Schriftdatei ist vorhanden
  3. Keine Seite lädt Ressourcen von fremden Servern
  4. Die Berichtszeiträume der Ausgaben schließen lückenlos aneinander an
  5. Die Tabellen unter data/csv/ stimmen mit data/kennzahlen.json überein

Punkt 5 hat beim ersten Einsatz neun fehlende Abstimmungen aufgedeckt.

    uv run --with lxml python scripts/pruefen.py
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import json
import re
import sys
import urllib.parse
from pathlib import Path

from lxml import html as H

WURZEL = Path(__file__).resolve().parent.parent
DOCS = WURZEL / "docs"
DATEN = WURZEL / "data"

# Server, die in Verweisen vorkommen dürfen — sie werden verlinkt, aber nicht
# beim Seitenaufruf abgerufen.
ERLAUBTE_ZIELE = ("amannlabs.eu", "ris.bad-waldsee.de", "www.bad-waldsee.de",
                  "bad-waldsee.de", "landesrecht-bw.de", "creativecommons.org",
                  "github.com", "w3.org")

fehler: list[str] = []
notiz: list[str] = []
hinweise: list[str] = []


def pruefe_verweise() -> None:
    gesamt = 0
    for f in sorted(DOCS.rglob("*.html")):
        for ziel in H.parse(str(f)).getroot().xpath("//a/@href"):
            if ziel.startswith(("http", "mailto:", "#")):
                continue
            gesamt += 1
            # Sprungmarke abschneiden: „seite.html#stelle" verweist auf die
            # Datei, nicht auf einen Pfad mit Raute im Namen.
            pfad = urllib.parse.unquote(ziel.split("#", 1)[0])
            if not pfad:
                continue
            if not (f.parent / pfad).resolve().exists():
                meldung = f"toter Verweis: {f.relative_to(WURZEL)} → {ziel}"
                if meldung not in fehler:
                    fehler.append(meldung)
    notiz.append(f"{gesamt} interne Verweise")


def pruefe_schriften() -> None:
    gesamt = 0
    for f in sorted(DOCS.rglob("*.html")):
        for ziel in re.findall(r"url\(([^)]+\.woff2)\)", f.read_text(encoding="utf-8")):
            gesamt += 1
            if not (f.parent / ziel).resolve().exists():
                meldung = f"fehlende Schrift: {f.relative_to(WURZEL)} → {ziel}"
                if meldung not in fehler:
                    fehler.append(meldung)
    notiz.append(f"{gesamt} Schriftverweise")


def pruefe_fremde_abrufe() -> None:
    """Beim Seitenaufruf darf nichts von fremden Servern nachgeladen werden."""
    treffer = set()
    muster = re.compile(r'(?:src|href)=["\'](https?://[^"\']+)', re.I)
    for f in sorted(DOCS.rglob("*.html")):
        for url in muster.findall(f.read_text(encoding="utf-8")):
            wirt = urllib.parse.urlparse(url).netloc
            if not any(wirt.endswith(e) for e in ERLAUBTE_ZIELE):
                treffer.add(f"{f.relative_to(WURZEL)} lädt von {wirt}")
    fehler.extend(sorted(treffer))
    notiz.append("keine fremden Abrufe" if not treffer else f"{len(treffer)} fremde Abrufe")


def pruefe_zeitraeume() -> None:
    pfad = DATEN / "ausgaben.json"
    if not pfad.exists():
        notiz.append("kein Ausgabenregister — übersprungen")
        return
    register = json.loads(pfad.read_text(encoding="utf-8"))
    geprueft = 0
    for jahr, ausgaben in register.items():
        paare = [(dt.date.fromisoformat(a["von_iso"]), dt.date.fromisoformat(a["bis_iso"]))
                 for _, a in sorted(ausgaben.items(), key=lambda kv: int(kv[0]))
                 if a.get("von_iso")]
        geprueft += len(paare)
        for (_, ende), (start, _) in zip(paare, paare[1:]):
            if ende >= start:
                fehler.append(f"{jahr}: Berichtszeiträume überschneiden sich bei "
                              f"{ende} / {start}")
            elif (start - ende).days > 1:
                fehler.append(f"{jahr}: Lücke zwischen {ende} und {start}")
    notiz.append(f"{geprueft} Berichtszeiträume")


def pruefe_tabellen() -> None:
    """Die Tabellen müssen dieselben Zahlen ergeben wie die Kennzahlen."""
    kennzahlen = DATEN / "kennzahlen.json"
    tabelle = DATEN / "csv" / "beschluesse.csv"
    if not (kennzahlen.exists() and tabelle.exists()):
        notiz.append("Kennzahlen oder Tabellen fehlen — übersprungen")
        return
    k = json.loads(kennzahlen.read_text(encoding="utf-8"))
    with tabelle.open(encoding="utf-8-sig") as f:
        zeilen = list(csv.DictReader(f, delimiter=";"))
    strittig = sum(1 for z in zeilen if z["einstimmig"] == "nein")

    for was, ist, soll in [
        ("Abstimmungen", len(zeilen), k["abstimmungen"]["gesamt"]),
        ("nicht einstimmige Beschlüsse", strittig, k["abstimmungen"]["nicht_einstimmig"]),
    ]:
        if ist != soll:
            fehler.append(f"{was}: Tabelle {ist}, Kennzahlen {soll}")
    notiz.append(f"{len(zeilen)} Abstimmungen gegengerechnet")


def pruefe_seitenkopf() -> None:
    """Doctype, Sprache und Viewport — ohne sie bricht die Handydarstellung.

    Fehlt die Viewport-Angabe, rendert ein Telefon die Seite auf rund 980 Pixel
    Breite und skaliert herunter: winzige Schrift, Zoomen nötig. Fehlt der
    Doctype, rechnet der Browser im Quirks-Modus mit anderen Größen. Beides
    fällt am Rechner nicht auf — genau deshalb wird es hier geprüft.
    """
    ohne = collections.Counter()
    for f in sorted(DOCS.rglob("*.html")):
        kopf = f.read_text(encoding="utf-8")[:800]
        if not kopf.lower().lstrip().startswith("<!doctype"):
            ohne["Doctype"] += 1
        if not re.search(r"<html[^>]*lang=", kopf):
            ohne["Sprachangabe"] += 1
        if 'name="viewport"' not in kopf:
            ohne["Viewport"] += 1
    for was, n in ohne.items():
        fehler.append(f"{n} Seite(n) ohne {was}")
    notiz.append("Seitenkopf vollständig" if not ohne else "Seitenkopf unvollständig")


# Formulierungen, die eine Aussage über den BESTAND einer Unterlage treffen,
# obwohl nur deren Abrufbarkeit geprüft wurde. Nach § 38 Abs. 1 GemO ist über
# jede Sitzung eine Niederschrift zu fertigen — dass keine online steht, heißt
# nicht, dass keine existiert. Die Unterscheidung ist der Kern der Belastbarkeit
# dieses Projekts und darf nicht unbemerkt zurückfallen.
BEHAUPTUNGEN = [
    # Beide Wortstellungen: „existiert kein Protokoll" und „kein Protokoll
    # existiert". Die zweite stand bis 11.09.2026 auf der Startseite und ist
    # dem Waechter entgangen, weil er nur die erste kannte.
    (r"existiert (?:ein|kein)\s+Protokoll|kein(?:e)? (?:Protokoll|Niederschrift)\w*\s+"
     r"(?:existiert|besteht|vorliegt|vorhanden)",
     "Aussage über den Bestand — geprüft ist nur die Abrufbarkeit"),
    (r"ohne jede Dokumentation", "„ohne jede Dokumentation“ — sagt etwas über den Bestand aus"),
    (r"Dokumentationsl(?:ü|ue)cke", "„Dokumentationslücke“ — wertend und bestandsbezogen"),
    (r"nicht dokumentiert", "„nicht dokumentiert“ — gemeint ist: nicht online abrufbar"),
    (r"ohne (?:jede )?(?:Überlieferung|Ueberlieferung)", "„ohne Überlieferung“ — bestandsbezogen"),
    (r"keine nachvollziehbare Spur", "„keine nachvollziehbare Spur“ — zu stark"),
    (r"kein einziges Protokoll ver(?:ö|oe)ffentlicht", "Formulierung legt ein Versäumnis nahe"),
    # Diese Fassung stand bis 11.09.2026 in jeder Wochenausgabe und ist am
    # Waechter vorbeigelaufen, weil er nur die Variante mit „kein einziges"
    # kannte. Erhoben ist die Abrufbarkeit, nicht die Veroeffentlichung.
    (r"kein(?:e)? (?:Protokoll|Niederschrift)\w* ver(?:ö|oe)ffentlicht",
     "„kein Protokoll veröffentlicht“ — geprüft ist nur die Abrufbarkeit"),
]



def pruefe_readme() -> None:
    """Zahlen in der README gegen die Daten halten.

    Die README wird von Hand gepflegt. Zweimal stand dort eine Zahl, die aus
    einem frueheren Lauf stammte — „436 Dokumente", als es laengst 625 waren.
    Solche Angaben veralten still, weil niemand sie nachrechnet.
    """
    readme = WURZEL / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    kennzahlen = json.loads((WURZEL / "data" / "kennzahlen.json").read_text(encoding="utf-8"))

    # Gezaehlt werden die Eintraege selbst, nicht die Ueberschriften: Unter den
    # <h3> steckt auch die des Kolophons („Warum diese Seite existiert"). Diese
    # Pruefung hat deshalb einmal eine richtige Zahl in eine falsche geaendert.
    befunde = DOCS / "befunde.html"
    erkenntnisse = (befunde.read_text(encoding="utf-8").count(
        '<article class="befundblock">') if befunde.exists() else None)

    pruefungen = [
        (r"(\d+) Dokumente sind so erreichbar", kennzahlen.get("dokumente"), "Dokumente"),
        (r"alle (\d+) Erkenntnisse", erkenntnisse, "Erkenntnisse auf der Befundeseite"),
    ]
    for muster, soll, was in pruefungen:
        if soll is None:
            continue
        m = re.search(muster, text)
        if not m:
            continue
        if int(m.group(1)) != soll:
            fehler.append(
                f"README nennt {m.group(1)} {was}, tatsaechlich sind es {soll}.")


def pruefe_fundstuecke() -> None:
    """Jedes Fundstueck gegen die Tagesordnungen halten.

    Die 50 Fundstuecke des Reports nennen Datum, Gremium und Vorlagennummer.
    Stimmt eine dieser Angaben nicht, fuehrt sie den Leser ins Leere — und
    faellt sonst niemandem auf, weil der Text fuer sich schluessig bleibt.

    Braucht data/topmap.json; ohne die Crawl-Daten wird uebersprungen.
    """
    karte = DATEN / "topmap.json"
    quelle = WURZEL / "src" / "report.html"
    if not (karte.exists() and quelle.exists()):
        return
    src = quelle.read_text(encoding="utf-8")
    i = src.find("var F=[")
    if i < 0:
        return
    eintraege = re.findall(
        r'\["((?:[^"\\]|\\.)*)","((?:[^"\\]|\\.)*)","(?:[^"\\]|\\.)*"\]',
        src[i:src.find("\n];", i)])

    gremien_am: dict[str, set[str]] = {}
    vorlagen_am: dict[str, set[str]] = {}
    for p in json.loads(karte.read_text(encoding="utf-8")):
        tag = ".".join(reversed(p["datum"].split("-")))
        gremien_am.setdefault(tag, set()).add(p["gremium"])
        if p.get("vorlage"):
            vorlagen_am.setdefault(tag, set()).add(p["vorlage"])

    kurz = {"GR": "Gemeinderat", "VA": "Verwaltungsausschuss",
            "AUT": "Ausschuss für Umwelt", "GA": "Gemeinsamer Ausschuss",
            "OR": "Ortschaftsrat", "KB": "Kulturbeirat"}
    ohne_vorlage = 0
    for titel, meta in eintraege:
        teile = [t.strip() for t in meta.split("·")]
        tag = teile[0]
        kuerzel = teile[1] if len(teile) > 1 else ""
        vorlage = next((t for t in teile if t.startswith("SV-")), None)
        if tag not in gremien_am:
            fehler.append(f"Fundstueck „{titel[:40]}“: kein Tagesordnungspunkt am {tag}")
            continue
        name = kurz.get(kuerzel)
        if name and not any(g.startswith(name) for g in gremien_am[tag]):
            fehler.append(f"Fundstueck „{titel[:40]}“: am {tag} tagte kein {kuerzel}")
        if vorlage:
            if vorlage not in vorlagen_am.get(tag, set()):
                fehler.append(
                    f"Fundstueck „{titel[:40]}“: {vorlage} steht am {tag} nicht "
                    f"auf der Tagesordnung")
        else:
            ohne_vorlage += 1

    m = re.search(r"(Fünf|Sechs|Sieben|Vier|Acht) der 50 Punkte haben systemseitig "
                  r"keine Vorlagennummer", src)
    if m:
        zahlwort = {"Vier": 4, "Fünf": 5, "Sechs": 6, "Sieben": 7, "Acht": 8}[m.group(1)]
        if zahlwort != ohne_vorlage:
            fehler.append(
                f"Der Report nennt {m.group(1).lower()} Fundstuecke ohne "
                f"Vorlagennummer, tatsaechlich sind es {ohne_vorlage}.")
    # Die Kapitelueberschrift nennt die Zahl der Beobachtungen als Wort. Sie
    # stand auf "Zehn", nachdem zwei Eintraege aufgeloest worden waren — eine
    # Ueberschrift rechnet niemand nach.
    zahlwoerter = {"Sechs": 6, "Sieben": 7, "Acht": 8, "Neun": 9, "Zehn": 10,
                   "Elf": 11, "Zwölf": 12}
    k = re.search(r"<h2>(\w+) Punkte, die Fragen aufwerfen</h2>", src)
    if k and k.group(1) in zahlwoerter:
        i2 = src.find("var C=[")
        anzahl = len(re.findall(r'^\["', src[i2:src.find("\n];", i2)], re.M)) if i2 > 0 else 0
        if anzahl and zahlwoerter[k.group(1)] != anzahl:
            fehler.append(
                f"Kapitel 06 ist mit „{k.group(1)} Punkte“ ueberschrieben, "
                f"tatsaechlich sind es {anzahl}.")

    notiz.append(f"{len(eintraege)} Fundstücke gegengeprüft")


def pruefe_themenverweise() -> None:
    """Die Suche verlinkt Themenseiten — gibt es die auch?

    Die Verweise entstehen erst im Browser, der Verweis-Waechter sieht sie im
    erzeugten HTML deshalb nicht. Geprueft wird stattdessen die Datenseite:
    Jeder in data/vorgaenge.json vermerkte Kuerzel muss eine Datei haben.
    """
    quelle = DATEN / "vorgaenge.json"
    ordner = DOCS / "themen"
    if not (quelle.exists() and ordner.exists()):
        return
    vorhanden = {p.stem for p in ordner.glob("*.html")}
    verwiesen = {v["th"] for v in json.loads(quelle.read_text(encoding="utf-8"))
                 if v.get("th")}
    fehlend = sorted(verwiesen - vorhanden)
    for x in fehlend:
        fehler.append(f"Suche verweist auf docs/themen/{x}.html — die Seite fehlt")
    if verwiesen:
        notiz.append(f"{len(verwiesen)} Themenverweise geprüft")

def pruefe_wortwahl() -> None:
    """Keine Aussage über den Bestand von Unterlagen, die nicht geprüft wurde."""
    treffer = []
    for f in sorted(DOCS.rglob("*.html")):
        text = f.read_text(encoding="utf-8")
        for muster, erklaerung in BEHAUPTUNGEN:
            if re.search(muster, text, re.I):
                treffer.append(f"{f.relative_to(WURZEL)}: {erklaerung}")
    # Je Formulierung nur einmal melden, sonst 89 gleichlautende Zeilen
    gesehen = set()
    for t in treffer:
        kern = t.split(": ", 1)[1]
        if kern in gesehen:
            continue
        gesehen.add(kern)
        fehler.append(f"Bestandsbehauptung: {t}")
    notiz.append("Wortwahl geprüft" if not gesehen else "Wortwahl beanstandet")


def pruefe_reportalter() -> None:
    """Ist der jüngste Report noch auf dem Stand der Daten?

    Kein Fehler, sondern ein Hinweis: Der Report ist ein datiertes Standbild.
    Sobald neue Sitzungen dazukommen, weichen seine Zahlen ab — dann gehört ein
    neuer, datierter Report erzeugt. Ohne Erinnerung fällt das niemandem auf,
    weil die Seite weiterhin einwandfrei aussieht.
    """
    kennzahlen = DATEN / "kennzahlen.json"
    berichte = sorted((DOCS / "report").glob("*.html")) if (DOCS / "report").exists() else []
    if not (kennzahlen.exists() and berichte):
        return
    stand = json.loads(kennzahlen.read_text(encoding="utf-8")).get("stichtag", "")
    try:
        datiert = berichte[-1].stem
        dt.date.fromisoformat(datiert)
    except ValueError:
        return
    # Entscheidend ist nicht der Stichtag, sondern ob seither eine Sitzung
    # stattgefunden hat. Sonst mahnt die Pruefung jeden Tag, an dem nichts
    # passiert ist — und wird bald ueberlesen.
    sitzungen = DATEN / "sitzungen.json"
    neuer = []
    if sitzungen.exists():
        neuer = [e for e in json.loads(sitzungen.read_text(encoding="utf-8"))
                 if datiert < e["start"][:10] <= stand]
    if neuer:
        hinweise.append(
            f"Seit dem Report vom {datiert} haben {len(neuer)} Sitzung(en) "
            f"stattgefunden (Daten bis {stand}). Ein neuer Report gehört nach "
            f"docs/report/{stand}.html — Stichtag in src/report.html nachziehen "
            f"und Schritt 04 ausführen.")
    notiz.append(f"Report vom {datiert}")


def main() -> None:
    if not DOCS.exists():
        sys.exit("docs/ fehlt — zuerst die Dokumente erzeugen.")

    for pruefung in (pruefe_verweise, pruefe_schriften, pruefe_fremde_abrufe,
                     pruefe_zeitraeume, pruefe_tabellen, pruefe_seitenkopf,
                     pruefe_readme, pruefe_fundstuecke, pruefe_themenverweise,
                     pruefe_wortwahl,
                     pruefe_reportalter):
        pruefung()

    seiten = len(list(DOCS.rglob("*.html")))
    print(f"   {seiten} Seiten · " + " · ".join(notiz))

    for h in hinweise:
        print(f"   Hinweis: {h}")

    if fehler:
        print(f"\n   {len(fehler)} Problem(e):", file=sys.stderr)
        for f in fehler:
            print(f"     ✗ {f}", file=sys.stderr)
        sys.exit(1)
    print("   alles in Ordnung")


if __name__ == "__main__":
    main()
