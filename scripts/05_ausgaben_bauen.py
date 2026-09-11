#!/usr/bin/env python3
"""Schritt 5 — die wöchentliche „Waldseer Aktenlage“ erzeugen.

Eine Ausgabe entsteht für jede Kalenderwoche, in der mindestens eine Sitzung
stattgefunden hat — und zusätzlich immer für die laufende Woche, damit es stets
eine aktuelle Ausgabe gibt. Dazwischenliegende sitzungsfreie Wochen bekommen
keine; eine Zeitung über nichts zu erfinden wäre unredlich.

Redaktionelle Einordnungen kommen optional aus data/einordnungen.json.

Inhalt je Ausgabe:
  * die gefassten Beschlüsse mit Vorlagennummer und Stimmenverhältnis
  * Bekanntgaben aus nichtöffentlicher Sitzung, soweit protokolliert
  * Sitzungen ohne Protokoll („Blinder Fleck“)
  * Vorschau auf die nächste öffentliche Sitzung

Ergebnis: docs/ausgaben/JJJJ/kwNN.html   die einzelnen Ausgaben
          docs/ausgaben/index.html      Archiv über alle Jahrgänge

    uv run --with pypdf python scripts/05_ausgaben_bauen.py --jahr 2026 --bis 2026-09-09
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import logging
import re
from pathlib import Path

from begriffe import begriffe_finden
from seite import navigation
from textwerk import pdf_text as roh_text, trennung_reparieren, wortschatz_laden

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
AUSGABEN = WURZEL / "docs" / "ausgaben"

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

# Ab diesem Betrag gilt ein Beschluss als finanziell bedeutsam. Bewusst hoch
# angesetzt: Haushalts- und Wirtschaftsplaene enthalten stets grosse Summen und
# sollen die Rubrik nicht fluten.
BETRAGSSCHWELLE = 250_000

# Titelmuster, die auf eine nicht eingeplante Ausgabe hindeuten.
UNGEPLANT = re.compile(r"au(?:ß|ss)erplanm(?:ä|ae)(?:ß|ss)ig|(?:ü|ue)berplanm(?:ä|ae)(?:ß|ss)ig",
                       re.I)

# Ein Bebauungsplan endet mit dem Satzungsbeschluss (§ 10 Abs. 1 BauGB) —
# das Gegenstueck zu den Abweichungsregeln: ein abgeschlossenes Verfahren.
ABSCHLUSS = re.compile(r"Satzungsbeschluss|als Satzung beschlossen|wird als Satzung", re.I)

# Jahresabschluesse und Rechenschaftsberichte nennen das Haushaltsjahr, das sie
# betreffen. Liegt es weit zurueck, wird ein Rueckstand aufgearbeitet.
RUECKSTAND = re.compile(r"Jahresabschluss\w*\s+(?:der\s+\w+\s+)?(\d{4})", re.I)

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

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


# --------------------------------------------------------------------- Daten

# Sitzungstitel lauten „<Gremium>, N. Sitzung". Entfernt wird nur die
# Zaehlung — ein Schnitt am ersten Komma machte aus dem „Ausschuss fuer
# Umwelt, Technik und Nachhaltigkeit" ein Gremium, das es nicht gibt.
NUR_ZAEHLUNG = re.compile(r",\s*\d+\.\s*Sitzung\s*$")


def gremium(titel: str) -> str:
    return NUR_ZAEHLUNG.sub("", titel)


def kuerzel(name: str) -> str:
    if name in KURZ:
        return KURZ[name]
    for anfang, kurz in PRAEFIXE:
        if name.startswith(anfang):
            return kurz
    return "—"


def dateiname(titel: str) -> str:
    """Muss exakt der Benennung aus 02_protokolle_laden.py entsprechen."""
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


def ergebnis_lesen(roh: str) -> tuple[str | None, bool]:
    z = AUSZAEHLUNG.match(roh)
    if z:
        ja, nein, enth = z.groups()
        return f"{ja} : {nein} : {enth}", bool(int(nein) or int(enth))
    if re.match(r"\s*[Ee]instimmig", roh):
        return "Einstimmig", False
    return None, False


def betrag_lesen(text: str) -> float | None:
    """Groesster Geldbetrag in einem Textabschnitt, in Euro."""
    hoechster = None
    for m in BETRAG.finditer(text):
        wert = float(m.group(1).replace(".", "").replace(",", "."))
        if m.group(2):  # "Mio."
            wert *= 1_000_000
        if hoechster is None or wert > hoechster:
            hoechster = wert
    return hoechster


# Der Beschlusstext steht im Protokoll zwischen der Einleitung „Beschluss:" und
# der Ergebniszeile. Er ist das, was tatsaechlich entschieden wurde — waehrend
# die Ueberschrift nur den Verwaltungsvorgang benennt.
EINLEITUNG = re.compile(
    r"(?:Modifizierter Beschluss|Beschlussvorschlag an den [^:]{0,40}|Beschluss)\s*:\s*")
SEITENFUSS = re.compile(
    r"Beschlussprotokoll der öffentlichen Sitzung.{0,140}?\d+\s*von\s*\d+\s*")


def beschlusstext(abschnitt: str, grenze: int = 1400) -> str:
    """Den beschlossenen Wortlaut aus dem Protokollabschnitt herausloesen."""
    treffer = list(EINLEITUNG.finditer(abschnitt))
    if not treffer:
        return ""
    roh = SEITENFUSS.sub(" ", abschnitt[treffer[-1].end():])
    roh = re.sub(r"\s+", " ", roh).strip()
    if len(roh) <= grenze:
        return roh
    schnitt = roh.rfind(". ", 0, grenze)
    return (roh[:schnitt + 1] if schnitt > grenze // 2 else roh[:grenze].rstrip()) + " …"


def beschluesse_lesen(text: str) -> list[dict]:
    """Jede Abstimmung der zuletzt davor genannten Vorlagennummer zuordnen.

    Der Abschnitt zwischen Vorlagennummer und Abstimmungsergebnis ist der
    Beschlusstext. Aus ihm lesen wir zusaetzlich, ob der Rat vom Vorschlag der
    Verwaltung abgewichen ist und welcher Betrag im Beschluss steht.
    """
    ergebnisse = []
    for treffer in ERGEBNIS.finditer(text):
        wert, strittig = ergebnis_lesen(treffer.group(1))
        if not wert:
            continue
        vorher = list(VORLAGE.finditer(text[:treffer.start()]))
        beginn = vorher[-1].start() if vorher else max(0, treffer.start() - 1500)
        abschnitt = text[beginn:treffer.start()]
        ergebnisse.append({
            "vorlage": vorher[-1].group(0) if vorher else None,
            "ergebnis": wert,
            "strittig": strittig,
            "modifiziert": "Modifizierter Beschluss" in abschnitt,
            "betrag": betrag_lesen(abschnitt),
            "wortlaut": beschlusstext(abschnitt),
        })
    return ergebnisse


def bekanntgaben_lesen(text: str) -> str | None:
    """Den Text unter „Bekanntgabe der in nichtöffentlicher Sitzung …“ holen."""
    m = re.search(r"Bekanntgabe der in nichtöffentlicher Sitzung getroffenen "
                  r"Entscheidung/?e?n?\s*(.{0,900})", text)
    if not m:
        return None
    roh = m.group(1).strip()
    roh = re.split(r"\s\d{1,2}\s+(?:Informationen des|Ehrungen|Verschiedenes|"
                   r"Bekanntgaben|Einwohnerfragestunde)", roh)[0]
    roh = re.sub(r"Beschlussprotokoll der öffentlichen Sitzung.{0,80}", "", roh)
    if len(roh) < 40 or re.match(r"^(Ohne Beschlussfassung|Keine Punkte)", roh):
        return None
    return roh.strip()[:700]


def datum_lang(d: dt.date) -> str:
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def euro(betrag: float) -> str:
    return f"{betrag:,.0f}".replace(",", ".") + " €"


def auffaelligkeiten(w: dict) -> list[dict]:
    """Regelbasierte Hinweise auf das, was aus dem Rahmen faellt.

    Bewusst nur Regeln, keine Deutung: Jeder Punkt ist am Protokoll ueberpruefbar.
    Die Rubrik findet keine Zusammenhaenge — sie zeigt, was auffaellt.

    Die Regeln sprechen absichtlich auf beides an: auf Abweichungen (nicht
    einstimmig, ausserplanmaessig, ohne Protokoll) und auf Abschluesse
    (Satzungsbeschluss, aufgearbeiteter Rueckstand, durchweg einstimmig). Eine
    Rubrik, die nur Abweichungen kennt, waere im Ergebnis eine Wertung — auch
    wenn jeder einzelne Satz neutral bleibt.
    """
    treffer = []

    strittig = [b for b in w["beschluesse"] if b["strittig"]]
    if strittig:
        treffer.append({
            "art": "Nicht einstimmig",
            "text": f"{len(strittig)} von {len(w['beschluesse'])} Beschlüssen fielen nicht "
                    f"einstimmig. Das Stimmenverhältnis steht bei den Beschlüssen.",
            "posten": [f"{b['vorlage']} — {b['ergebnis']}" for b in strittig],
        })

    modifiziert = [b for b in w["beschluesse"] if b.get("modifiziert")]
    if modifiziert:
        treffer.append({
            "art": "Rat weicht vom Verwaltungsvorschlag ab",
            "text": "Das Protokoll kennzeichnet diese Beschlüsse als „Modifizierter "
                    "Beschluss“ — der beschlossene Text weicht vom Vorschlag der "
                    "Verwaltung ab.",
            "posten": [f"{b['vorlage']} — {b['titel']}" for b in modifiziert],
        })

    ungeplant = [b for b in w["beschluesse"] if b["titel"] and UNGEPLANT.search(b["titel"])]
    if ungeplant:
        treffer.append({
            "art": "Nicht im Haushalt vorgesehen",
            "text": "Diese Ausgaben wurden als außer- oder überplanmäßig beschlossen, "
                    "standen also nicht im Haushaltsplan.",
            "posten": [f"{b['vorlage']} — {b['titel']}" for b in ungeplant],
        })

    teuer = sorted((b for b in w["beschluesse"]
                    if b.get("betrag") and b["betrag"] >= BETRAGSSCHWELLE),
                   key=lambda b: -b["betrag"])
    if teuer:
        treffer.append({
            "art": "Größere Beträge",
            "text": f"In diesen Beschlusstexten steht ein Betrag ab "
                    f"{euro(BETRAGSSCHWELLE)}. Haushalts- und Wirtschaftspläne "
                    f"enthalten naturgemäß große Summen.",
            "posten": [f"{euro(b['betrag'])} — {b['vorlage']} {b['titel']}" for b in teuer[:6]],
        })

    wieder = [b for b in w["beschluesse"] if b.get("frueher")]
    if wieder:
        treffer.append({
            "art": "Erneut auf der Tagesordnung",
            "text": "Diese Vorlagen standen schon früher auf einer Tagesordnung — "
                    "durch Vorberatung in einem Ausschuss, durch Vertagung oder durch "
                    "erneute Befassung.",
            "posten": [f"{b['vorlage']} — zuvor am "
                       f"{', '.join(dt.date.fromisoformat(d).strftime('%d.%m.%Y') for d in b['frueher'][-3:])}"
                       for b in wieder],
        })

    # --- Abschluesse und Aufarbeitung; dieselbe Regellogik, andere Richtung
    abgeschlossen = [b for b in w["beschluesse"]
                     if ABSCHLUSS.search((b.get("wortlaut") or "") + " " + (b["titel"] or ""))]
    if abgeschlossen:
        treffer.append({
            "art": "Verfahren abgeschlossen",
            "ton": "neutral",
            "text": "Ein Planverfahren endet damit, dass das Ergebnis als Satzung "
                    "beschlossen wird. Das Verfahren ist dann abgeschlossen — über "
                    "die Qualität des Ergebnisses sagt das nichts, wohl aber, dass es "
                    "nicht liegen geblieben ist.",
            "posten": [f"{b['vorlage']} — {b['titel']}" for b in abgeschlossen],
        })

    # Gemessen wird der Verzug nach Ablauf der Zwoelfmonatsfrist des § 95b GemO —
    # dieselbe Bezugsgroesse wie im Report, sonst nennen zwei Seiten fuer
    # denselben Sachverhalt verschiedene Zahlen. Die Differenz der Kalenderjahre
    # taugt nicht: Sie machte aus 4,2 Jahren "5 Jahre", also eine
    # Ueberzeichnung zu Lasten der Stadt.
    aufgearbeitet = []
    for b in w["beschluesse"]:
        m = RUECKSTAND.search(b["titel"] or "")
        if not m:
            continue
        jahr = int(m.group(1))
        # Tagegenau und durch die mittlere Monatslaenge geteilt — dieselbe
        # Rechenweise wie im Report. In Kalendermonaten gezaehlt kaeme man je
        # nach Beschlusstag auf einen Monat mehr, und zwei Seiten nennten fuer
        # denselben Abschluss verschiedene Zahlen.
        verzug = round((b["datum"] - dt.date(jahr + 1, 12, 31)).days / 30.44)
        if verzug >= 12:
            aufgearbeitet.append((b, jahr, verzug))
    if aufgearbeitet:
        treffer.append({
            "art": "Rückstand aufgearbeitet",
            "ton": "neutral",
            "text": "Diese Beschlüsse betreffen zurückliegende Haushaltsjahre. Sie zeigen, "
                    "dass ein Rückstand abgearbeitet wird — und zugleich, wie groß er war.",
            "posten": [f"{b['vorlage']} — {b['titel']} ({verzug} Monate nach Ablauf "
                       f"der Zwölfmonatsfrist des § 95b GemO)"
                       for b, jahr, verzug in aufgearbeitet],
        })

    if w["beschluesse"] and not strittig:
        treffer.append({
            "art": "Durchweg einstimmig",
            "ton": "neutral",
            "text": f"Alle {len(w['beschluesse'])} Beschlüsse dieser Woche fielen einstimmig. "
                    f"Das kann breiten Konsens abbilden; Beschlussprotokolle halten keine "
                    f"Aussprache fest, aus ihnen allein ist das nicht zu unterscheiden.",
            "posten": [],
        })

    # Sitzungen ohne abrufbare Unterlagen stehen bewusst NICHT hier, sondern in
    # der eigenen Rubrik „Blinder Fleck". Dort ist der Sachverhalt genauer
    # gefasst — erhoben ist die Abrufbarkeit, nicht der Bestand einer
    # Niederschrift — und er bekommt den Zusammenhang ueber den ganzen
    # Zeitraum. Stuende er zusaetzlich hier, waere derselbe Umstand zweimal
    # gezaehlt und die Rubrik im Ergebnis eine Wertung.

    return treffer


def einordnungen_laden() -> dict:
    pfad = DATEN / "einordnungen.json"
    if not pfad.exists():
        return {}
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    return {k: v for k, v in roh.items() if not k.startswith("_")}


# ------------------------------------------------------------------ Sammeln

def wochen_sammeln(jahr: int, bis: str, erschienen: dict | None = None) -> dict[int, dict]:
    quelle = DATEN / "sitzungen.json"
    if not quelle.exists():  # HINWEIS_01
        raise SystemExit(
            "data/sitzungen.json fehlt. Die Datei ist ein Zwischenergebnis und wird "
            "nicht versioniert — bitte zuerst Schritt 01 ausführen:\n"
            "  uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py")
    sitzungen = json.loads(quelle.read_text(encoding="utf-8"))
    punkte = json.loads((DATEN / "topmap.json").read_text(encoding="utf-8"))
    titel_je_vorlage = {p["vorlage"]: p["titel"] for p in punkte if p["vorlage"]}

    # Wann stand eine Vorlage schon einmal auf einer Tagesordnung? Mehrfache
    # Auftritte deuten auf Vorberatung, Vertagung oder erneute Befassung hin.
    # Die an einem Punkt haengenden Dokumente — Sitzungsvorlage, Planteil,
    # Umweltbericht. Wer es genau wissen will, liest im Original nach.
    dokumente_je_punkt: dict[tuple[str, str], list[dict]] = {}
    for p in punkte:
        if p.get("dokumente"):
            dokumente_je_punkt[(p["datum"], p["vorlage"] or "")] = p["dokumente"]

    termine_je_vorlage: dict[str, list[str]] = collections.defaultdict(list)
    for p in punkte:
        if p["vorlage"]:
            termine_je_vorlage[p["vorlage"]].append(p["datum"])
    for v in termine_je_vorlage.values():
        v.sort()

    protokolle = {p.name[:10]: [] for p in (DATEN / "protokolle").glob("*.pdf")}
    for p in sorted((DATEN / "protokolle").glob("*.pdf")):
        protokolle.setdefault(p.name[:10], []).append(p)

    alle = sorted(sitzungen, key=lambda s: s["start"])
    kuenftig = [s for s in alle if s["start"][:10] > bis]

    wochen: dict[int, dict] = collections.defaultdict(
        lambda: {"sitzungen": [], "beschluesse": [], "bekanntgaben": [], "blind": []})

    for s in alle:
        tag = dt.date.fromisoformat(s["start"][:10])
        if tag.year != jahr or s["start"][:10] > bis:
            continue
        kw = tag.isocalendar()[1]
        w = wochen[kw]
        name = gremium(s["titel"])
        w["sitzungen"].append({"datum": tag, "gremium": name, "kuerzel": kuerzel(name),
                               "protokoll": bool(s["protokolle"])})
        if not s["protokolle"]:
            w["blind"].append({"datum": tag, "gremium": name})
            continue
        # Eine Sitzung kann mehrere Protokolldateien haben — etwa wenn eine
        # Anwesenheitsliste getrennt abgelegt ist. Es werden alle ausgewertet:
        # welche davon den Beschlusstext enthaelt, ist nicht vorhersehbar.
        erwartet = f"{s['start'][:10]}_{dateiname(s['titel'])}"
        for pfad in protokolle.get(s["start"][:10], []):
            if pfad.stem != erwartet and not pfad.stem.startswith(erwartet + "_"):
                continue
            text = pdf_text(pfad)
            for b in beschluesse_lesen(text):
                b["titel"] = titel_je_vorlage.get(b["vorlage"], None)
                b["frueher"] = [d for d in termine_je_vorlage.get(b["vorlage"], [])
                                if d < s["start"][:10]]
                b["dokumente"] = dokumente_je_punkt.get(
                    (s["start"][:10], b["vorlage"] or ""), [])
                b["gremium"] = name
                b["kuerzel"] = kuerzel(name)
                b["datum"] = tag
                if b["titel"]:
                    w["beschluesse"].append(b)
            bg = bekanntgaben_lesen(text)
            if bg:
                w["bekanntgaben"].append({"datum": tag, "gremium": name, "text": bg})

    # Die laufende Woche bekommt immer eine Ausgabe, damit stets eine aktuelle
    # existiert — auch wenn in ihr nicht getagt wurde.
    stichtag = dt.date.fromisoformat(bis)
    if stichtag.year == jahr:
        wochen[stichtag.isocalendar()[1]]  # legt bei Bedarf eine leere Woche an

    # Berichtszeitraum: vom Ende der vorigen erschienenen Ausgabe bis zum Ende
    # dieser Woche. Der Anschluss haengt am tatsaechlichen Ende der Vorgaenger-
    # ausgabe aus dem Register, nicht am Sonntag ihrer Kalenderwoche — sonst
    # entsteht eine Luecke, wenn eine Ausgabe vor dem Wochenende Redaktions-
    # schluss hatte, oder eine Ueberschneidung, wenn eine sitzungsfreie Woche
    # in diesem Lauf nicht noch einmal erzeugt wird.
    enden = {int(k): dt.date.fromisoformat(v["bis_iso"])
             for k, v in (erschienen or {}).items() if v.get("bis_iso")}

    letztes_ende: dt.date | None = None
    for kw in sorted(wochen):
        w = wochen[kw]
        frueher = [d for k, d in enden.items() if k < kw]
        anker = max(frueher) if frueher else None
        if letztes_ende and (anker is None or letztes_ende > anker):
            anker = letztes_ende
        beginn = (anker + dt.timedelta(days=1) if anker
                  else dt.date.fromisocalendar(jahr, kw, 1))
        ende = min(dt.date.fromisocalendar(jahr, kw, 7), stichtag)
        letztes_ende = ende
        w["von"], w["bis"] = beginn, ende
        # Sitzungen ohne Protokoll aus dem gesamten Berichtszeitraum aufnehmen,
        # nicht nur aus der Kalenderwoche selbst.
        w["blind"] = [
            {"datum": dt.date.fromisoformat(x["start"][:10]), "gremium": gremium(x["titel"])}
            for x in alle
            if not x["protokolle"]
            and beginn <= dt.date.fromisoformat(x["start"][:10]) <= ende
        ]
        spaeter = [x for x in alle if dt.date.fromisoformat(x["start"][:10]) > ende]
        w["naechste"] = spaeter[0] if spaeter else None
        w["kuenftig"] = kuenftig
    return dict(sorted(wochen.items()))


# ------------------------------------------------------------------ Rendern

def e(t: str) -> str:
    return html.escape(t, quote=False)


def kopf(titel: str, hoch: str = "", hier: str = "") -> str:
    """Seitenkopf. `hoch` ist der relative Weg zum docs-Verzeichnis, `hier`
    markiert die aktuelle Seite in der Navigation."""
    stil = (WURZEL / "scripts" / "ausgabe.css").read_text(encoding="utf-8")
    schriften = (WURZEL / "scripts" / "schriften.css").read_text(
        encoding="utf-8").replace("{PFAD}", hoch)

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titel)}</title>
<style>{schriften}</style>
<style>{stil}</style>
</head>
<body>
<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <nav aria-label="Bereiche">
    {navigation(hoch, hier)}
  </nav>
  <span class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>
"""


def fuss(zusatz: str = "") -> str:
    return f"""
<footer><div class="wrap">
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
  <p>Alle Angaben und Insights ohne Gew&auml;hr{zusatz}</p>
</div></footer>
</body>
</html>
"""


DISCLAIMER = """
  <div class="kasten warn">
    <p class="lab">Lernprojekt &middot; keine Gew&auml;hr &middot; keine Vorw&uuml;rfe</p>
    <p><b>Diese Publikation ist ein privates Lern- und Technologieprojekt</b> zur automatisierten
    Auswertung &ouml;ffentlich zug&auml;nglicher Verwaltungsdokumente. Sie ist kein
    journalistisches Erzeugnis, kein Pr&uuml;fbericht und keine rechtliche oder fachliche
    Bewertung.</p>
    <p><b>F&uuml;r Richtigkeit, Vollst&auml;ndigkeit und Aktualit&auml;t wird keine Gew&auml;hr
    &uuml;bernommen.</b> Alle Angaben beruhen auf maschineller Verarbeitung von PDF-Dokumenten;
    Fehler bei Texterkennung und Zuordnung sind m&ouml;glich. Verbindlich ist ausschlie&szlig;lich
    das jeweilige Originaldokument der Stadt Bad Waldsee.</p>
    <p><b>Es werden keine Vorw&uuml;rfe erhoben.</b> Weder der Stadtverwaltung noch einzelnen
    Personen wird rechtswidriges oder schuldhaftes Verhalten unterstellt. Einordnungen
    und Wertungen sind als <b>KI-Deutung</b> gekennzeichnet: maschinell erzeugt und
    nicht redaktionell gepr&uuml;ft. Namen von Privatpersonen werden nicht wiedergegeben. Korrekturen sind erw&uuml;nscht und werden
    zeitnah eingearbeitet. Es besteht keine Verbindung zur Stadt Bad Waldsee.</p>
  </div>
"""


def ausgabe_bauen(jahr: int, kw: int, w: dict, einordnung: dict | None) -> str:
    mo, so = w["von"], w["bis"]
    n_besch = len(w["beschluesse"])
    mit_prot = sum(1 for s in w["sitzungen"] if s["protokoll"])

    t = [kopf(f"Aktenlage KW {kw}/{jahr}", hoch="../../"), '<div class="wrap">']
    t.append(f"""
<header class="masthead">
  <h1>Waldseer Aktenlage</h1>
  <p class="claim">Was der Gemeinderat und seine Ausschüsse entschieden haben —
  gelesen aus den Originalunterlagen.</p>
  <div class="issueline">
    <span><b>Ausgabe</b> KW {kw} / {jahr}</span>
    <span><b>Berichtszeitraum</b> {mo.strftime('%d.%m.')}–{so.strftime('%d.%m.%Y')}</span>
    <span><b>Sitzungen</b> {len(w['sitzungen'])} · {mit_prot} protokolliert</span>
    <span><b>Beschlüsse</b> {n_besch}</span>
  </div>
</header>""")

    # --- Redaktionelle Einordnung, falls hinterlegt
    if einordnung:
        absaetze = "\n".join(f"    <p>{e(a)}</p>" for a in einordnung.get("absaetze", []))
        geprueft = einordnung.get("status") == "geprueft"
        marke = ('<p class="herkunft geprueft">Redaktionell geprüft</p>' if geprueft else
                 '<p class="herkunft ki">KI-Deutung · am Beleg nachprüfbar</p>')
        fussnote = ("" if geprueft else
                    '\n    <p class="note">Dieser Abschnitt ist eine maschinell erzeugte '
                    'Einordnung. Die genannten Zahlen und Beschlüsse stammen aus den '
                    'Protokollen und sind dort nachprüfbar; die Verknüpfung und Gewichtung '
                    'wurde nicht von einem Menschen geprüft.</p>')
        t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Berichtszeitraum</span><span class="val">{mo.strftime('%d.%m.')}–{so.strftime('%d.%m.%Y')}</span></div>
    <div class="field"><span class="lab">Sitzungen</span><span class="val">{len(w['sitzungen'])}</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">{e(einordnung.get('rubrik', 'Zur Lage'))}</p>
    {marke}
    <h2 class="headline">{e(einordnung.get('titel', ''))}</h2>
{absaetze}{fussnote}
  </div>
</article>""")

    # --- Wenn nichts entschieden wurde, das ausdrücklich sagen
    if not w["beschluesse"] and not einordnung:
        t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Berichtszeitraum</span><span class="val">{mo.strftime('%d.%m.')}–{so.strftime('%d.%m.%Y')}</span></div>
    <div class="field"><span class="lab">Beschlüsse</span><span class="val">0</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Zur Lage</p>
    <h2 class="headline">Kein dokumentierter Beschluss in diesem Zeitraum</h2>
    <p>In diesem Berichtszeitraum wurde kein Beschlussprotokoll veröffentlicht. Entweder
    hat kein protokollierendes Gremium getagt, oder die Protokolle der stattgefundenen
    Sitzungen lagen zum Redaktionsschluss noch nicht vor.</p>
  </div>
</article>""")

    # --- Auffälligkeiten
    hinweise = auffaelligkeiten(w)
    if hinweise:
        bloecke = []
        for h in hinweise:
            posten = "".join(
                f'        <li><span class="sache">{e(p)}</span></li>\n' for p in h["posten"])
            liste = (f'      <ul class="beschluesse kompakt">\n{posten}      </ul>\n'
                     if h["posten"] else "")
            klasse = "kasten warn" if h.get("ton", "warn") == "warn" else "kasten"
            bloecke.append(f"""    <div class="{klasse}">
      <p class="lab">{e(h['art'])}</p>
      <p>{e(h['text'])}</p>
{liste}    </div>""")
        t.append(f"""
<article id="auffaelligkeiten">
  <div class="rail">
    <div class="field"><span class="lab">Hinweise</span><span class="val">{len(hinweise)}</span></div>
    <div class="field"><span class="lab">Erzeugt</span><span class="val">regelbasiert</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Auffälligkeiten</p>
    <p class="herkunft regel">Regelbasiert gezählt · keine Deutung</p>
    <h2 class="headline">Wo sich Hinschauen lohnt</h2>
    <p>Diese Rubrik entsteht aus festen Regeln, nicht aus einer Bewertung. Sie zeigt,
    was formal aus dem Rahmen fällt — ob es inhaltlich bedeutsam ist, steht damit
    nicht fest. Jeder Punkt ist am Originalprotokoll überprüfbar.</p>
    <p>Die Regeln sprechen auf beides an: auf Abweichungen und auf Abschlüsse.
    Rot hinterlegt ist, was vom Üblichen abweicht; ohne Farbe steht, was
    abgeschlossen oder aufgearbeitet wurde.</p>
{chr(10).join(bloecke)}
  </div>
</article>""")

    # --- Begriffe, die in dieser Ausgabe vorkommen
    # Steht bewusst vor den Beschlusslisten: Der Leser soll die Erklaerung
    # haben, bevor er ueber den Begriff stolpert.
    # Nur gegen den Text pruefen, den der Leser auch sieht. Wuerde man die
    # ganze Wochenstruktur serialisieren, loesten Dateinamen von Anlagen und
    # interne Felder Erklaerungen fuer Begriffe aus, die in der Ausgabe gar
    # nicht vorkommen.
    sichtbar = " ".join(filter(None, (
        [b.get("titel") or "" for b in w["beschluesse"]]
        + [b.get("wortlaut") or "" for b in w["beschluesse"]]
        + [b.get("gremium") or "" for b in w["beschluesse"]]
        + [s.get("gremium") or "" for s in w["sitzungen"]]
        + [b.get("gremium") or "" for b in w["blind"]]
        + [h["art"] + " " + h["text"] for h in hinweise]
    )))
    gefunden = begriffe_finden(sichtbar)
    if gefunden:
        eintraege = "\n".join(
            f"""      <div class="begriff">
        <p class="wort">{e(b['name'])}</p>
        <p>{b['satz']}</p>
        <p class="fundstelle">{e(b['fundstelle'])}</p>
      </div>""" for b in gefunden)
        t.append(f"""
<article id="begriffe">
  <div class="rail">
    <div class="field"><span class="lab">Begriffe</span><span class="val">{len(gefunden)}</span></div>
    <div class="field"><span class="lab">Herkunft</span><span class="val">Gesetz</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Begriffe</p>
    <p class="herkunft geprueft">Beleg · Gesetzestext und Hauptsatzung</p>
    <h2 class="headline">Was die Amtssprache meint</h2>
    <p>Die Beschlüsse unten stehen im Wortlaut des Protokolls. Diese Begriffe kommen
    darin vor und bedeuten nicht immer das, was sie auf den ersten Blick nahelegen.
    Ausführlicher steht das unter <a href="../../gremien.html">Wer entscheidet was</a>.</p>
    <details class="begriffe" open>
      <summary>{len(gefunden)} Begriffe in dieser Ausgabe</summary>
{eintraege}
    </details>
  </div>
</article>""")

    # --- Beschlüsse
    if w["beschluesse"]:
        je_gremium: dict[tuple, list] = collections.defaultdict(list)
        for b in w["beschluesse"]:
            je_gremium[(b["datum"], b["gremium"], b["kuerzel"])].append(b)
        for (tag, name, kz), liste in sorted(je_gremium.items()):
            t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Sitzung</span><span class="val">{e(name)}</span></div>
    <div class="field"><span class="lab">Datum</span><span class="val">{tag.strftime('%d.%m.%Y')}</span></div>
    <div class="field"><span class="lab">Beschlüsse</span><span class="val">{len(liste)}</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Beschlossen · {e(kz)}</p>
    <h2 class="headline">{len(liste)} {'Beschluss' if len(liste) == 1 else 'Beschlüsse'} am {datum_lang(tag)}</h2>
    <ul class="beschluesse">""")
            for b in liste:
                klasse = " split" if b["strittig"] else ""
                # Der groesste im Beschlusstext genannte Betrag. Bewusst neutral
                # bezeichnet: Es ist die hoechste dort vorkommende Summe, nicht
                # zwingend "die Kosten" — bei Haushaltspunkten etwa eine
                # Planungsgroesse.
                geld = ""
                if b.get("betrag") and b["betrag"] >= BETRAGSSCHWELLE:
                    geld = (f"""<span class="betrag" title="größter im Beschlusstext """
                            f"""genannter Betrag">{euro(b['betrag'])}</span>""")
                wortlaut = (f"""<span class="wortlaut">{e(b['wortlaut'])}</span>"""
                            if b.get("wortlaut") else "")
                unterlagen = ""
                if b.get("dokumente"):
                    verweise = "".join(
                        f'<a href="{d["url"]}" target="_blank" rel="noopener noreferrer">'
                        f'{e(d["titel"])}</a>' for d in b["dokumente"])
                    unterlagen = f'<span class="unterlagen">{verweise}</span>' 
                t.append(f"""      <li><span class="sache">{e(b['titel'])}"""
                         f"""<span class="sv">{e(b['vorlage'] or '—')}{geld}</span>"""
                         f"""{wortlaut}{unterlagen}</span>"""
                         f"""<span class="erg{klasse}">{e(b['ergebnis'])}</span></li>""")
            t.append("    </ul>")
            if any(b["strittig"] for b in liste):
                st = [b for b in liste if b["strittig"]]
                t.append(f"""    <div class="kasten warn">
      <p class="lab">Nicht einstimmig</p>
      <p>{len(st)} von {len(liste)} Beschlüssen fielen nicht einstimmig:
      {', '.join(f"<b>{e(b['vorlage'] or '—')}</b> ({e(b['ergebnis'])})" for b in st)}.
      Die Schreibweise steht für Ja : Nein : Enthaltungen.</p>
    </div>""")
            t.append("  </div>\n</article>")

    # --- Bekanntgaben aus nichtöffentlicher Sitzung
    for bg in w["bekanntgaben"]:
        t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Bekanntgabe</span><span class="val">{e(bg['gremium'])}</span></div>
    <div class="field"><span class="lab">Datum</span><span class="val">{bg['datum'].strftime('%d.%m.%Y')}</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Aus nichtöffentlicher Sitzung</p>
    <h2 class="headline">Was hinter verschlossenen Türen entschieden wurde</h2>
    <p>Zu Beginn der Sitzung gibt das Gremium bekannt, was es zuvor nichtöffentlich
    beschlossen hat. Im Protokoll steht dazu wörtlich:</p>
    <div class="kasten"><p class="lab">Wortlaut des Protokolls</p><p>{e(bg['text'])}</p></div>
    <p class="note">Bekanntgaben nennen das Ergebnis, nicht die Begründung, die Kosten oder
    die Alternativen. Wie viel insgesamt nichtöffentlich entschieden wird, ist aus den
    Unterlagen nicht ermittelbar.</p>
  </div>
</article>""")

    # --- Blinder Fleck
    if w["blind"]:
        zeilen = "".join(
            f"      <li><span class=\"sache\">{e(b['gremium'])}"
            f"<span class=\"sv\">Sitzung vom {b['datum'].strftime('%d.%m.%Y')}</span></span>"
            f"<span class=\"erg split\">kein Protokoll</span></li>\n"
            for b in sorted(w["blind"], key=lambda x: x["datum"]))
        t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Betroffen</span><span class="val">{len(w['blind'])} Sitzung(en)</span></div>
    <div class="field"><span class="lab">Protokolle</span><span class="val">0</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Blinder Fleck</p>
    <h2 class="headline">{len(w['blind'])} öffentliche {'Sitzung' if len(w['blind']) == 1 else 'Sitzungen'} ohne online abrufbare Unterlagen</h2>
    <p>Diese Gremien tagten öffentlich; im Ratsinformationssystem ist zu ihnen keine
    Niederschrift abrufbar:</p>
    <ul class="beschluesse">
{zeilen}    </ul>
    <div class="kasten warn">
      <p class="lab">Wiederkehrende Rubrik</p>
      <p>Seit Januar 2024 tagten die vier Ortschaftsräte <b>85 Mal öffentlich</b> — rund die
      Hälfte aller öffentlichen Sitzungen der Stadt. Zu keiner dieser Sitzungen ist im
      Ratsinformationssystem eine Niederschrift abrufbar; die Sitzungsseiten enthalten
      Datum und Ort.</p>
      <p>Über den Bestand der Niederschriften sagt das nichts: § 38 Abs. 1 GemO verlangt
      sie, § 38 Abs. 2 Satz 4 GemO gibt Einwohnern ein Einsichtsrecht, eine Pflicht zur
      Veröffentlichung im Internet besteht nicht. Es geht um Zugänglichkeit.</p>
      <p>Nach § 16 Abs. 4 der Hauptsatzung entscheiden die Ortschaftsräte allerdings auch
      selbst — etwa über Haushaltsmittel bis 26.000 € und Grundstücksgeschäfte bis
      52.000 € im Einzelfall.</p>
    </div>
  </div>
</article>""")

    # --- Vorschau
    if w["naechste"]:
        n = w["naechste"]
        tag = dt.date.fromisoformat(n["start"][:10])
        uhr = n["start"][11:16]
        name = gremium(n["titel"])
        punkte = "".join(f"      <li><span>{e(p)}</span></li>\n" for p in n["tops"][:8])
        liste = (f'    <ol class="agenda">\n{punkte}    </ol>' if punkte else
                 '    <p class="note">Zum Redaktionsschluss war für diese Sitzung noch '
                 'keine Tagesordnung im Ratsinformationssystem veröffentlicht.</p>')
        t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Termin</span><span class="val">{tag.strftime('%d.%m.%Y')}<br>{uhr} Uhr</span></div>
    <div class="field"><span class="lab">Gremium</span><span class="val">{e(name)}</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Demnächst · öffentlich</p>
    <h2 class="headline">Als Nächstes: {e(name)} am {datum_lang(tag)}</h2>
{liste}
  </div>
</article>""")

    # --- Kolophon
    t.append(f"""
<section class="kolophon">
  <p class="rubrik">Zur Ausgabe</p>
  <h3>Zu den Menschen hinter den Beschlüssen</h3>
  <p>Die Beschlüsse dieser Ausgabe stammen aus Sitzungen, die fast ausnahmslos abends
  nach der Arbeit stattfinden. Die Mitglieder der Räte und Ausschüsse tun das
  ehrenamtlich, unter ihrem Namen und in öffentlicher Sitzung — und ihre
  Entscheidungen werden anschließend öffentlich diskutiert. Diese Auswertung misst
  Unterlagen, nicht Personen: Sie zeigt, was in den Akten steht, und sagt nichts
  darüber, mit welcher Sorgfalt oder Absicht jemand entschieden hat.</p>

  <h3>Wie diese Ausgabe entsteht</h3>
  <p>Diese Ausgabe wurde maschinell aus den Beschlussprotokollen und Tagesordnungen des
  <a class="doc" href="https://ris.bad-waldsee.de/" rel="noopener">Ratsinformationssystems
  der Stadt Bad Waldsee</a> erzeugt. Beschlusstitel stammen aus der Tagesordnung,
  Abstimmungsergebnisse wörtlich aus der Zeile „Ergebnis der Beschlussfassung“ des
  Protokolls. Die Schreibweise <span class="mono">25 : 0 : 1</span> steht für
  Ja : Nein : Enthaltungen.</p>
  <p>Jeder Beschluss nennt seine Vorlagennummer (<span class="mono">SV-000/JJJJ</span>);
  damit ist der Vorgang im Ratsinformationssystem unter „Vorlagen“ auffindbar. Wo eine
  Sitzungsvorlage oder Anlage vorliegt, ist sie zusätzlich direkt verlinkt. Diese Adressen
  waren im Test über Tage hinweg abrufbar; zugesichert ist ihre Haltbarkeit aber nirgends.
  Die Vorlagennummer bleibt deshalb der verlässlichere Weg.</p>
  <p class="note">Beschlussprotokolle halten keine Aussprache fest: <em>wie</em> abgestimmt
  wurde, ist nachlesbar, <em>warum</em> nicht. Nichtöffentliche Sitzungsteile sind
  vollständig unsichtbar.</p>
{DISCLAIMER}
  <p class="note"><a class="doc" href="../index.html">Alle Ausgaben im Archiv</a></p>
</section>
</div>""")
    t.append(fuss(f" &middot; Ausgabe KW {kw}/{jahr} &middot; erzeugt am "
                  f"{dt.date.today().strftime('%d.%m.%Y')}"))
    return "\n".join(t)


def archiv_bauen(register: dict) -> str:
    """Archiv über alle Jahrgänge, gespeist aus data/ausgaben.json."""
    jahre = sorted(register, reverse=True)
    ges_a = sum(len(register[j]) for j in jahre)
    ges_b = sum(a["beschluesse"] for j in jahre for a in register[j].values())
    ges_s = sum(a["sitzungen"] for j in jahre for a in register[j].values())

    t = [kopf("Aktenlage — Archiv", hoch="../", hier="archiv"), '<div class="wrap">']
    t.append(f"""
<header class="masthead">
  <h1>Aktenlage &middot; Archiv</h1>
  <p class="claim">Alle bisher erschienenen Ausgaben der Waldseer Aktenlage.</p>
  <div class="issueline">
    <span><b>Jahrgänge</b> {', '.join(jahre)}</span>
    <span><b>Ausgaben</b> {ges_a}</span>
    <span><b>Sitzungen</b> {ges_s}</span>
    <span><b>Beschlüsse</b> {ges_b}</span>
  </div>
</header>
<section class="kolophon">
  <p class="rubrik">Übersicht</p>
  <h3>Erscheinungsweise</h3>
  <p>Es erscheint eine Ausgabe für jede Kalenderwoche, in der mindestens eine Sitzung
  stattgefunden hat, sowie stets eine Ausgabe für die laufende Woche. Dazwischenliegende
  sitzungsfreie Wochen bekommen keine Ausgabe — deshalb ist die Nummerierung
  lückenhaft.</p>
</section>""")

    for jahr in jahre:
        ausgaben = register[jahr]
        t.append(f"""
<section class="kolophon">
  <p class="rubrik">Jahrgang {jahr}</p>
  <h3>{len(ausgaben)} Ausgaben</h3>
  <ul class="beschluesse">""")
        for kw in sorted(ausgaben, key=int, reverse=True):
            a = ausgaben[kw]
            teile = []
            if a["beschluesse"]:
                teile.append(f"{a['beschluesse']} "
                             f"{'Beschluss' if a['beschluesse'] == 1 else 'Beschlüsse'}")
            if a["ohne_protokoll"]:
                teile.append(f"{a['ohne_protokoll']} ohne Protokoll")
            gremien = " · ".join(a["gremien"]) if a["gremien"] else "keine Sitzung"
            t.append(f"""    <li><span class="sache">
      <a class="doc" href="./{jahr}/kw{int(kw):02d}.html">KW {int(kw)} / {jahr}</a>
      <span class="sv">{e(a['zeitraum'])} &middot; {e(gremien)}</span></span>
      <span class="erg">{e(' · '.join(teile)) or 'ohne Beschluss'}</span></li>""")
        t.append("  </ul>\n</section>")

    t.append(f"""
<section class="kolophon" style="border-bottom:none">
{DISCLAIMER}
  <p class="note"><a class="doc" href="../index.html">Zur Startseite</a></p>
</section>
</div>""")
    t.append(fuss(" &middot; Archiv"))
    return "\n".join(t)


def register_lesen() -> dict:
    pfad = DATEN / "ausgaben.json"
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jahr", type=int, default=dt.date.today().year)
    p.add_argument("--bis", default=dt.date.today().isoformat(),
                   help="Redaktionsschluss; spätere Sitzungen bleiben unberücksichtigt")
    args = p.parse_args()

    ordner = AUSGABEN / str(args.jahr)
    ordner.mkdir(parents=True, exist_ok=True)
    einordnungen = einordnungen_laden()

    register = register_lesen()
    register.setdefault(str(args.jahr), {})
    wochen = wochen_sammeln(args.jahr, args.bis, register[str(args.jahr)])

    for kw, w in wochen.items():
        schluessel = f"{args.jahr}-kw{kw:02d}"
        text = ausgabe_bauen(args.jahr, kw, w, einordnungen.get(schluessel))
        (ordner / f"kw{kw:02d}.html").write_text(text, encoding="utf-8")
        register[str(args.jahr)][f"{kw:02d}"] = {
            "zeitraum": f"{w['von'].strftime('%d.%m.')}–{w['bis'].strftime('%d.%m.%Y')}",
            "von_iso": w["von"].isoformat(),
            "bis_iso": w["bis"].isoformat(),
            "sitzungen": len(w["sitzungen"]),
            "beschluesse": len(w["beschluesse"]),
            "ohne_protokoll": len(w["blind"]),
            "gremien": sorted({s["kuerzel"] for s in w["sitzungen"]}),
            "einordnung": schluessel in einordnungen,
            # Die Abschluss-Regeln dieser Woche mitschreiben. Schritt 09 sammelt
            # sie fuer die Rubrik „Was eingehalten wird" — so zeigt die
            # Befundeseite genau das, was auch in den Ausgaben steht, statt eine
            # zweite Zaehlung mit eigenem Ergebnis aufzumachen.
            "abschluesse": {h["art"]: h["posten"]
                            for h in auffaelligkeiten(w)
                            if h.get("ton") == "neutral"},
        }
        marke = " ←" if schluessel in einordnungen else ""
        print(f"  KW {kw:2d}  {len(w['sitzungen'])} Sitzung(en), "
              f"{len(w['beschluesse'])} Beschlüsse, {len(w['blind'])} ohne Protokoll{marke}")

    # Sortiert schreiben, damit die Datei nicht davon abhängt, in welcher
    # Reihenfolge die Jahrgänge erzeugt wurden — sonst entstehen bei jedem Lauf
    # Änderungen, die keine sind.
    (DATEN / "ausgaben.json").write_text(
        json.dumps(register, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    (AUSGABEN / "index.html").write_text(archiv_bauen(register), encoding="utf-8")

    neueste = max(wochen)
    print(f"\n{len(wochen)} Ausgaben in docs/ausgaben/{args.jahr}/, "
          f"Archiv über {len(register)} Jahrgang/Jahrgänge aktualisiert.")
    print(f"Neueste Ausgabe: KW {neueste}/{args.jahr}")


if __name__ == "__main__":
    main()
