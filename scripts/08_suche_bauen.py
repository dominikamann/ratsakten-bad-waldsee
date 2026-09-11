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
import json
import logging
import re
from pathlib import Path

from seite import fuss, kopf, kurz

from vorhaben import seiten_je_vorgang, vergleichsname
from textwerk import schwaerzen, pdf_text as roh_text, trennung_reparieren, wortschatz_laden

# pypdf meldet bei vielen Protokollen "Ignoring wrong pointing object" — ein
# Schoenheitsfehler in den erzeugten PDFs, der die Textextraktion nicht stoert.
# Gezielt stummschalten, statt die gesamte Fehlerausgabe zu verwerfen: Echte
# Fehler sollen sichtbar bleiben.
logging.getLogger("pypdf").setLevel(logging.ERROR)

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"

# Silbentrennungen des PDF zusammenfuehren. Welcher Bindestrich eine
# Trennung ist und welcher ein Gedankenstrich, entscheidet der Wortschatz
# aus 03_auswerten.py — siehe textwerk.py.
WORTSCHATZ = wortschatz_laden(DATEN / "wortschatz.json")
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
    for anfang, zeichen in PRAEFIXE:
        if name.startswith(anfang):
            return zeichen
    return "—"


def dateiname(titel: str) -> str:
    # Achtung: Hier wird bewusst am ersten Komma geschnitten, obwohl das
    # den Gremiumsnamen verkuerzt. Die bereits geladenen Protokolle auf
    # der Platte tragen genau diese Namen; eine Aenderung wuerde sie
    # unauffindbar machen. Fuer die Anzeige gibt es gremium().
    name = re.sub(r",.*", "", titel)
    name = re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", "-", name).strip("-")
    return name[:48]


def pdf_text(pfad: Path) -> str:
    """Rohtext aus dem Zwischenspeicher, Silbentrennung zusammengefuehrt.

    Die Reparatur passiert hier und nicht im Zwischenspeicher, weil der
    Wortschatz erst in Schritt 03 entsteht — der Speicher haelt deshalb den
    unbehandelten Text.
    """
    return trennung_reparieren(roh_text(pfad), WORTSCHATZ)


# Der Beschlusstext steht zwischen der Einleitung „Beschluss:" und der
# Ergebniszeile. Die Ueberschrift benennt den Verwaltungsvorgang, dieser Text
# sagt, was tatsaechlich entschieden wurde.
EINLEITUNG = re.compile(
    r"(?:Modifizierter Beschluss|Beschlussvorschlag an den [^:]{0,40}|Beschluss)\s*:\s*")
SEITENFUSS = re.compile(
    r"Beschlussprotokoll der öffentlichen Sitzung.{0,140}?\d+\s*von\s*\d+\s*")


def beschlusstext(abschnitt: str, grenze: int = 900) -> str:
    treffer = list(EINLEITUNG.finditer(abschnitt))
    if not treffer:
        return ""
    roh = SEITENFUSS.sub(" ", abschnitt[treffer[-1].end():])
    # Einmal an der Quelle schwaerzen, damit keine der Rueckgaben daran vorbeigeht.
    roh = schwaerzen(re.sub(r"\s+", " ", roh).strip())
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
                "dok": p.get("dokumente", []),
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

    # Zu jedem Vorgang die Themenseite vermerken, sofern es eine gibt. Die
    # Zuordnung stammt aus demselben Modul, aus dem Schritt 11 die Seiten baut —
    # sonst verwiese die Suche auf Seiten, die es nicht gibt.
    seiten = seiten_je_vorgang(vorgaenge)
    for v in vorgaenge:
        ziel = seiten.get(vergleichsname(v["t"]))
        if ziel:
            v["th"] = ziel

    # Die redaktionellen Einordnungen mit aufnehmen. Sie verbinden mehrere
    # Vorgaenge ueber die Zeit — genau das, was aus den Einzelpunkten nicht
    # hervorgeht. Wer nach „Windkraft" sucht, soll auch die Erkenntnis finden,
    # dass dreimal in Folge das Einvernehmen versagt wurde.
    einordnungen = einordnungen_laden()
    ende_je_ausgabe = {}
    for _von, bis, pfad in zeitraeume:
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


EIGEN = """
.suchfeld{
  display:flex;gap:10px;flex-wrap:wrap;margin:28px 0 0;
}
.suchfeld input{
  flex:1 1 320px;background:var(--surface);color:var(--ink);
  border:1px solid var(--rule);border-left:3px solid var(--s1);
  padding:15px 18px;font-family:"IBM Plex Serif",Georgia,serif;font-size:18px;
}
.suchfeld input:focus{outline:2px solid var(--s1);outline-offset:2px}
.suchfeld input::placeholder{color:var(--muted)}
.filter{
  display:flex;gap:8px 18px;flex-wrap:wrap;margin:14px 0 0;
  font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-2);
}
.filter label{cursor:pointer;display:flex;align-items:center;gap:7px}
.trefferzahl{
  font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin:22px 0 0;
}
/* Das Stylesheet der Ausgaben legt fuer <article> ein zweispaltiges Raster mit
   Randspalte fest. Fuer Suchtreffer gilt das nicht — sonst wird der Titel in
   186 Pixel gequetscht und daneben bleibt die halbe Zeile leer. */
article.vorgang{
  display:block;padding:20px 0;gap:0;
  border-bottom:1px solid var(--rule);
}
.vorgang .kopf{
  display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline;
}
.vorgang h3{
  font-family:Archivo,sans-serif;font-weight:600;font-size:17.5px;line-height:1.35;
  margin:0 0 4px;color:var(--ink);
}
.vorgang .nr{
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.05em;
  color:var(--muted);
}
.achse{
  display:flex;flex-wrap:wrap;gap:0;margin:12px 0 0;
}
.achse .unterlagen{
  flex:1 1 100%;display:flex;flex-wrap:wrap;gap:6px 10px;margin:4px 0 8px;
}
.achse .unterlagen a{
  font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.03em;
  color:var(--s1);text-decoration:none;border:1px solid var(--rule);padding:3px 8px;
}
.achse .unterlagen a::before{content:"↗ ";opacity:.6}
.achse .unterlagen a:hover{border-color:var(--s1)}
.achse .unterlagen a:focus-visible{outline:2px solid var(--s1);outline-offset:2px}
.achse .wortlaut{
  flex:1 1 100%;margin:2px 0 12px;padding-left:12px;
  border-left:2px solid var(--rule);max-width:74ch;
  font-family:"IBM Plex Serif",Georgia,serif;font-size:14.5px;line-height:1.55;
  color:var(--ink-2);
}
.station{
  display:flex;align-items:baseline;gap:9px;
  padding:6px 14px 6px 0;position:relative;
}
.station:not(:last-child)::after{
  content:"→";color:var(--muted);opacity:.5;padding-left:14px;
}
.station .dat{
  font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink-2);
  font-variant-numeric:tabular-nums;white-space:nowrap;
}
.station .grem{
  font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.08em;
  color:var(--muted);border:1px solid var(--rule);padding:1px 5px;
}
.station .erg{
  font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.04em;
  color:var(--s1);white-space:nowrap;
}
.station .erg.split{color:var(--s1)}
.station .svnr{
  font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);
  opacity:.75;white-space:nowrap;
}
.vorgang .untertitel{color:var(--muted);font-family:"IBM Plex Serif",serif;font-size:13px}
.vorgang .wege{display:flex;flex-wrap:wrap;gap:6px 14px;margin:7px 0 0}
.vorgang .wege a{font-family:"IBM Plex Mono",monospace;font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--s1);
  text-decoration:none;border-bottom:1px solid rgba(57,135,229,.35)}
.vorgang .wege a:hover{border-bottom-color:var(--s1)}
a.station{text-decoration:none;color:inherit}
a.station:hover .dat{color:var(--s1);text-decoration:underline}
a.station:hover .grem{border-color:var(--s1)}
.titellink{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--s1)}
.titellink:hover{color:var(--s1)}
.titellink:focus-visible{outline:2px solid var(--s1);outline-offset:3px}
.fundort{
  font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);
  border:1px solid var(--rule);padding:1px 6px;
}
/* Die Herkunft markiert die Marke oben im Treffer — nicht die ganze Karte.
   Eingefaerbt und mit farbigem Balken sah jede Einordnung aus wie eine Warnung,
   obwohl die Faerbung nur sagte, wie die Aussage entstanden ist. Bleibt eine
   ruhige Flaeche, die den Treffer als zusammengehoerig zeigt. */
.vorgang.istEinordnung{
  border-left:1px solid var(--rule);padding-left:18px;background:var(--surface);
}
.vorgang.istEinordnung + .vorgang.istEinordnung{margin-top:12px}
.vorgang .einleitung{margin:8px 0 0;font-size:15.5px;line-height:1.6;color:var(--ink-2);max-width:74ch}
.gekuerzt{
  display:-webkit-box;-webkit-box-orient:vertical;
  -webkit-line-clamp:var(--zeilen,4);line-clamp:var(--zeilen,4);overflow:hidden;
}
.gekuerzt.offen{-webkit-line-clamp:unset;line-clamp:unset;display:block}
/* Dasselbe Aufklapp-Element wie bei den Tagesordnungen auf der Startseite und
   im Kalender: Winkel, Wort, sonst nichts. Als umrandeter Kasten wurde der
   Knopf in der Zeitachse — einem Flex-Container — auf die volle Zeilenhoehe
   gedehnt und stand als leeres Rechteck neben dem Text. */
button.mehr{
  display:inline-flex;align-items:center;gap:7px;align-self:flex-start;
  margin:6px 0 0;padding:0;background:none;border:0;
  color:var(--s1);font-family:var(--mono);font-size:10.5px;
  letter-spacing:.08em;text-transform:uppercase;cursor:pointer;
}
button.mehr::before{content:"\\25B8";font-size:12px;line-height:1}
button.mehr[aria-expanded="true"]::before{content:"\\25BE"}
button.mehr:hover{text-decoration:underline}
button.mehr:focus-visible{outline:2px solid var(--s1);outline-offset:3px}
/* In der Zeitachse eine eigene Zeile unter dem Wortlaut, nicht daneben. */
.achse button.mehr{flex:0 0 100%;margin-left:0}
.betrag{
  padding:1px 7px;font-family:"IBM Plex Mono",monospace;font-size:10.5px;
  /* Ein Betrag ist eine Angabe, keine Warnung. */
  font-variant-numeric:tabular-nums;color:var(--ink-2);border:1px solid var(--rule);
  background:var(--surface-2);white-space:nowrap;
}
.betrag.klein{font-size:10px;padding:0 5px}
.filter select{
  background:var(--surface);color:var(--ink);border:1px solid var(--rule);
  font-family:"IBM Plex Mono",monospace;font-size:12px;padding:3px 6px;margin-left:6px;
}
mark{background:rgba(57,135,229,.25);color:var(--ink);padding:0 2px}

/* Suchfeld und Filter auf schmalen Bildschirmen: alles untereinander, damit
   nichts aus dem Bild laeuft und die Ziele gross genug zum Antippen sind. */
@media (max-width:620px){
  .suchfeld input{flex:1 1 100%;font-size:16px;padding:13px 15px}
  .filter{flex-direction:column;gap:10px;align-items:flex-start}
  .filter label{min-height:32px}
  .filter select{margin-left:8px;padding:5px 8px;font-size:13px}
  .vorgang .kopf{gap:6px 10px}
  button.mehr{padding:7px 12px}
}
.leer{padding:40px 0;color:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:14px}
/* Ein Hinweis auf eine technische Voraussetzung ist keine Warnung. */
.ohnejs{
  margin:28px 0;padding:20px 22px;background:var(--surface);
  border-left:3px solid var(--s1);
}
.ohnejs p{margin:0}
"""


def bauen(vorgaenge: list[dict], stichtag: str) -> str:
    # "</script>" im Titel wuerde das Element vorzeitig beenden und die ganze
    # Seite lahmlegen. Die Titel stammen aus fremdem HTML — also absichern.
    index = (json.dumps(vorgaenge, ensure_ascii=False, separators=(",", ":"))
             .replace("</", "<\\/"))
    einordnungen = sum(1 for v in vorgaenge if v.get("art") == "einordnung")
    sachvorgaenge = [v for v in vorgaenge if v.get("art") != "einordnung"]
    mit_beschluss = sum(1 for v in sachvorgaenge if any(s["e"] for s in v["s"]))
    mehrstufig = sum(1 for v in sachvorgaenge if len(v["s"]) > 1)

    return f"""{kopf("Vorgänge durchsuchen · Ratsakten Bad Waldsee", hier="suche",
                     beschreibung="Alle erfassten Vorgänge der Stadt Bad Waldsee mit "
                                  "ihrem Weg durch die Gremien — durchsuchbar nach "
                                  "Stichwort und Vorlagennummer.",
                     eigen=EIGEN)}
<div class="wrap">
<header>
  <p class="eyebrow">Vorgänge &middot; durchsuchbar</p>
  <h1>Vorg&auml;nge</h1>
  <p class="lede">Jeder Vorgang mit seinem Weg durch die Gremien — von der ersten
  Beratung bis zum Beschluss. Mitdurchsucht werden die redaktionellen
  Einordnungen, die mehrere Vorg&auml;nge &uuml;ber die Zeit verbinden.</p>
  <div class="issueline">
    <span><b>Vorg&auml;nge</b> {len(sachvorgaenge)}</span>
    <span><b>mit Beschluss</b> {mit_beschluss}</span>
    <span><b>mehrstufig</b> {mehrstufig}</span>
    <span><b>Einordnungen</b> {einordnungen}</span>
    <span><b>Stand</b> {kurz(stichtag)}</span>
  </div>
</header>

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

<p class="trefferzahl" id="zahl"></p>
<div id="treffer"></div>

<section class="kolophon">
  <h3>Was hier steht</h3>
  <p>Ein Vorgang b&uuml;ndelt alles, was zum selben Vorhaben verhandelt wurde. Ist im
  Titel ein Vorhaben genannt — etwa der Bebauungsplan „Drei Eichen VI" —, dient
  dieser Name als Klammer; ein Bauleitplanverfahren durchl&auml;uft n&auml;mlich mehrere
  Vorlagen mit jeweils eigener Nummer. Fehlt ein solcher Name, wird nach
  Vorlagennummer geb&uuml;ndelt, sonst steht der Punkt f&uuml;r sich.</p>
  <p>Die Kette zeigt jede Station: Datum, Gremium und — wo ein Beschlussprotokoll
  vorliegt — das Abstimmungsergebnis. Die Schreibweise <span class="mono">25 : 0 : 1</span>
  steht f&uuml;r Ja : Nein : Enthaltungen; mehrere Ergebnisse an einer Station bedeuten,
  dass zuerst &uuml;ber einen &Auml;nderungsantrag und danach &uuml;ber den Beschluss
  abgestimmt wurde.</p>

  <h3>Einordnungen</h3>
  <p>Neben den Vorg&auml;ngen sind die <b>redaktionellen Einordnungen</b> der
  Wochenausgaben durchsuchbar. Sie verbinden mehrere Vorg&auml;nge &uuml;ber die Zeit —
  etwa die Erkenntnis, dass Bad Waldsee binnen elf Monaten dreimal in Folge das
  Einvernehmen f&uuml;r Windkraft versagt hat. Aus den Einzelpunkten geht das nicht
  hervor.</p>
  <p>Solche Treffer sind mit <span class="herkunft ki">KI-Deutung</span> gekennzeichnet:
  maschinell erzeugt, auf belegten Zahlen beruhend, <b>nicht redaktionell gepr&uuml;ft</b>.
  Gesammelt stehen sie auf der Seite <a class="doc" href="./befunde.html">Erkenntnisse</a>.</p>

  <h3>Reihenfolge der Treffer</h3>
  <p>Zuerst kommt, was den Suchbegriff in der &Uuml;berschrift oder der Vorlagennummer
  tr&auml;gt. Treffer, bei denen das Wort nur im Flie&szlig;text vorkommt, stehen dahinter
  und sind mit <i>Treffer im Text</i> markiert — sonst w&uuml;rde die Suche nach
  „Feuerwehr" eine Einordnung mit der &Uuml;berschrift „F&uuml;nf Windr&auml;der
  abgelehnt" nach oben sp&uuml;len, nur weil das Wort in deren Text steht.</p>
  <p>Unter jeder Station steht der <b>beschlossene Wortlaut</b> — der Text, den das
  Gremium tatsächlich gefasst hat. Er ist aussagekräftiger als die Überschrift, die
  nur den Verwaltungsvorgang benennt. Angezeigt werden rund 340 Zeichen;
  <b>durchsucht wird der vollständige Beschluss</b>, und wenn der Treffer hinter der
  Kürzung liegt, erscheint der ganze Text. Maßgeblich bleibt das Protokoll.</p>
  <p>Wo Unterlagen am Tagesordnungspunkt hängen — Sitzungsvorlage, Planteil,
  Umweltbericht —, sind sie <b>verlinkt und öffnen in einem neuen Tab</b>. Die
  Sitzungsvorlage enthält den Abschnitt „Zum Sachverhalt": dort steht, warum die
  Verwaltung etwas vorschlägt. Wiedergegeben wird er hier nicht — wer ihn lesen
  will, liest ihn im Original.</p>
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

{fuss(meta=f"Stand {kurz(stichtag)}", ende=False)}

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

  /* Der volle Text steht immer im Dokument — er wird nur optisch auf wenige
     Zeilen begrenzt. So bleibt er durchsuchbar und kopierbar, und ein Klick
     zeigt ihn ganz. Liegt ein Suchtreffer hinter der Begrenzung, klappt der
     Text von selbst auf. */
  function aufklappbar(behaelter, element, zeilen){{
    element.style.setProperty("--zeilen", zeilen);
    element.classList.add("gekuerzt");
    var knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "mehr";
    knopf.textContent = "Vollständig anzeigen";
    knopf.addEventListener("click", function(){{
      var offen = element.classList.toggle("offen");
      knopf.textContent = offen ? "Weniger anzeigen" : "Vollständig anzeigen";
      knopf.setAttribute("aria-expanded", offen ? "true" : "false");
    }});
    knopf.setAttribute("aria-expanded", "false");
    behaelter.appendChild(knopf);
    // Nach dem Einfuegen pruefen, ob ueberhaupt gekuerzt wird
    requestAnimationFrame(function(){{
      var beschnitten = element.scrollHeight - element.clientHeight > 4;
      var treffer = element.querySelector("mark");
      if(!beschnitten){{ knopf.remove(); element.classList.remove("gekuerzt"); return; }}
      if(treffer && treffer.offsetTop > element.clientHeight - 8){{
        element.classList.add("offen");
        knopf.textContent = "Weniger anzeigen";
        knopf.setAttribute("aria-expanded", "true");
      }}
    }});
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
  daten.forEach(function(v){{
    v._kopf = normal(v.t + " " + v.v);
    v._voll = normal(v.t + " " + v.v + " " + (v.u||"") + " "
                     + v.s.map(function(s){{return s.t + " " + (s.w||"");}}).join(" "));
  }});

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
    // Ohne Suchbegriff zeigt die Liste, was die Seite ist: Vorgaenge. Die
    // Einordnungen tragen als Datum das Ende ihres Berichtszeitraums und sind
    // damit immer das Neueste — ungefiltert standen deshalb zwei KI-Deutungen
    // ganz oben und die 506 Vorgaenge darunter. Sobald gesucht wird, sind sie
    // wieder dabei; gesammelt stehen sie auf der Erkenntnisseite.
    var nurVorgaenge = !roh;
    var treffer = daten.filter(function(v){{
      if(nurVorgaenge && v.art === "einordnung") return false;
      if(fB.checked && !v.s.some(function(s){{ return s.e; }})) return false;
      if(fS.checked && !v.strittig) return false;
      if(fM.checked && v.s.length < 2) return false;
      var schwelle = parseInt(fG.value, 10);
      if(schwelle && (v.b || 0) < schwelle) return false;
      if(!woerter.every(function(w){{ return v._voll.indexOf(w) > -1; }})) return false;
      // Steht der Suchbegriff in der Überschrift oder nur irgendwo im Text?
      // Ein Treffer, der nur im Fließtext steckt, wirkt sonst wie ein Irrläufer:
      // Die Suche nach „Feuerwehr" lieferte einen Fund mit der Überschrift
      // „Fünf Windräder abgelehnt", weil das Wort in dessen Text vorkam.
      v._imKopf = woerter.every(function(w){{ return v._kopf.indexOf(w) > -1; }});
      return true;
    }});

    if(woerter.length){{
      treffer.sort(function(a, b){{
        if(a._imKopf !== b._imKopf) return a._imKopf ? -1 : 1;
        return a.letzte < b.letzte ? 1 : (a.letzte > b.letzte ? -1 : 0);
      }});
    }}

    if(treffer.length === 0){{
      zahl.textContent = "Kein Treffer";
    }} else {{
      var imKopf = treffer.filter(function(v){{ return v._imKopf; }}).length;
      var text = treffer.length + (treffer.length === 1 ? " Vorgang" : " Vorgänge")
                 + (roh ? " für „" + roh + "“" : "");
      if(roh && imKopf < treffer.length){{
        text += " — " + imKopf + " in der Überschrift, "
                + (treffer.length - imKopf) + " nur im Text";
      }}
      zahl.textContent = text;
    }}

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
      // Wo es eine Chronik des Vorhabens gibt, fuehrt der Titel dorthin: Sie
      // zeigt den ganzen Verlauf, die Wochenausgabe nur einen Ausschnitt. Der
      // Weg in die Ausgabe bleibt daneben erhalten, benannt statt versteckt.
      var ausgabe = v.a || (v.s.length ? v.s[v.s.length-1].a : "");
      var chronik = v.th ? ("./themen/" + v.th + ".html") : "";
      var ziel = chronik || ausgabe;
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
      if(chronik || ausgabe){{
        var wege = document.createElement("p");
        wege.className = "wege";
        if(chronik){{
          var a1 = document.createElement("a");
          a1.href = chronik;
          a1.textContent = "Chronik des Vorhabens · " + v.s.length + " Stationen";
          wege.appendChild(a1);
        }}
        if(ausgabe){{
          var a2 = document.createElement("a");
          a2.href = ausgabe;
          a2.textContent = chronik ? "Wochenausgabe" : "In der Wochenausgabe";
          wege.appendChild(a2);
        }}
        d.appendChild(wege);
      }}
      var teile = v.v ? v.v.split(" · ") : [];
      var nr = document.createElement("p");
      nr.className = "nr";
      if(teile.length > 4){{
        nr.textContent = teile.length + " Vorlagen · " + v.s.length + " Stationen";
      }} else if(teile.length){{
        nr.appendChild(hervorheben(v.v, woerter));
      }}
      if(v.art !== "einordnung" && v.u && v.u !== v.t){{
        var u = document.createElement("span");
        u.className = "untertitel";
        u.textContent = (teile.length ? " — " : "") + v.u;
        nr.appendChild(u);
      }}
      if(nr.textContent) kopf.appendChild(nr);
      if(woerter.length && !v._imKopf){{
        var wo = document.createElement("span");
        wo.className = "fundort";
        wo.textContent = "Treffer im Text";
        kopf.appendChild(wo);
      }}
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
        txt.appendChild(hervorheben(v.u, woerter));
        d.appendChild(txt);
        aufklappbar(d, txt, 6);
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
        if(s.dok && s.dok.length){{
          var u = document.createElement("p");
          u.className = "unterlagen";
          s.dok.forEach(function(d){{
            var a = document.createElement("a");
            a.href = d.url; a.target = "_blank"; a.rel = "noopener noreferrer";
            a.textContent = d.titel;
            u.appendChild(a);
          }});
          achse.appendChild(u);
        }}
        if(s.w){{
          var w = document.createElement("p");
          w.className = "wortlaut";
          w.appendChild(hervorheben(s.w, woerter));
          achse.appendChild(w);
          aufklappbar(achse, w, 4);
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
        # Zwei Zahlen, weil die Seite selbst zwei nennt: die Sachvorgaenge und
        # die Einordnungen, die mehrere davon verbinden. Frueher stand hier nur
        # die Summe, und die Startseite beschriftete sie als „Vorgaenge" — was
        # der Suche widersprach, die 506 anzeigte.
        "vorgaenge": len(vorgaenge),
        "sachvorgaenge": sum(1 for v in vorgaenge if v.get("art") != "einordnung"),
        "mehrstufig": mehrstufig,
        "stichtag": args.stichtag,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # Die vollstaendig gruppierten Vorgaenge einmal ablegen. Schritt 11 baut
    # daraus die Themenseiten, ohne die Gruppierung ein zweites Mal zu
    # implementieren — zwei Fassungen derselben Logik wuerden auseinanderlaufen.
    (DATEN / "vorgaenge.json").write_text(
        json.dumps(vorgaenge, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
