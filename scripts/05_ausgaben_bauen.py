#!/usr/bin/env python3
"""Schritt 5 — die wöchentliche „Waldseer Ratswoche“ erzeugen.

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

from begriffe import markieren
from seite import aktuelle_ausgabe_setzen, fuss, kopf
from textwerk import (
    haeufigkeiten_laden,
    leertrennung_reparieren,
    sachverhalt_lesen,
    schwaerzen,
    stichtag_vorgabe,
    trennung_reparieren,
    vermerk_lesen,
    wortschatz_laden,
)
from textwerk import pdf_text as roh_text

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
HAEUFIGKEITEN = haeufigkeiten_laden(DATEN / "wortschatz.json")
AUSGABEN = WURZEL / "docs" / "ausgaben"
VORLAGEN = DATEN / "vorlagen"

# Wie lange ein Beschlussprotokoll nach der Sitzung auf sich warten darf, ehe
# sein Fehlen als „Blinder Fleck" gilt.
#
# Nicht gegriffen, sondern gemessen: `scripts/14_protokollfrist.py` haelt das
# Aenderungsdatum jedes der 72 Beschlussprotokolle gegen sein Sitzungsdatum.
# Der Median liegt bei 2 Tagen; nach 14 Tagen liegen 64 von 72 vor (88,9 %) —
# und **bis 28 Tage kommt danach kein einziges mehr nach**. Was bis dahin
# fehlt, fehlt dann 42 bis 391 Tage lang: Nachreichungen, keine laufende
# Bearbeitung. Genau dort liegt der Schnitt.
#
# Die Frist ist bewusst grosszuegig. Sie soll niemandem ein Versaeumnis
# vorwerfen, das keines ist. Wird sie nachgerechnet, die Zahl hier mitziehen —
# das Skript nennt sie am Ende.
# Wiederkehrende Punkte wie „Verschiedenes" oder „Bekanntgaben" wurden eine
# Zeit lang gesondert behandelt: aus der Themenliste herausgefiltert und in
# einem Nachsatz zusammengefasst. Das ist wieder entfallen. Jede Sonderregel
# braucht eine Erklaerung, und die Erklaerung war laenger als das, was sie
# ersparte — „Dazu ohne Ergebnis: …" ist selbst ein Satz, den niemand braucht.
#
# Jedes Thema wird jetzt gleich dargestellt: Titel, was daran haengt, und was
# das Protokoll dazu vermerkt. Bei „Verschiedenes" steht dann eben „Keine
# Punkte seitens der Verwaltung" — das ist kurz, wahr und verlangt kein
# Vorwissen ueber die Bauart der Ausgabe.

KARENZ_TAGE = 14

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

# Fuer Rubriken: ein Name, den man lesen kann. Das Kuerzel („GR", „GA") ist
# die Sprache des Ratsinformationssystems und sagt einem Buerger nichts; der
# volle Name des Gemeinsamen Ausschusses ist dagegen 86 Zeichen lang und
# sprengt jede Rubrikzeile.
RUBRIKNAME = {
    "Gemeinsamer Ausschuss der Vereinbarten Verwaltungsgemeinschaft "
    "Bad Waldsee-Bergatreute": "Gemeinsamer Ausschuss",
}


def rubrikname(name: str) -> str:
    return RUBRIKNAME.get(name, name)


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
    # Erst die Trennungen mit Bindestrich, dann die, bei denen er beim
    # Auslesen verloren ging und nur ein Leerzeichen blieb.
    return leertrennung_reparieren(
        trennung_reparieren(roh_text(pfad), WORTSCHATZ), HAEUFIGKEITEN)


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
    # Einmal an der Quelle schwaerzen, damit keine der Rueckgaben daran vorbeigeht.
    roh = schwaerzen(re.sub(r"\s+", " ", roh).strip())
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
            # Nicht „Planverfahren": ABSCHLUSS misst den Satzungsbeschluss, und
            # den fasst auch eine Sanierungssatzung. Die Bezeichnung muss
            # nennen, was gezaehlt wurde.
            "text": "Das Verfahren endet damit, dass das Ergebnis als Satzung "
                    "beschlossen wird — meist ein Bebauungsplan. Über die "
                    "Qualität des Ergebnisses sagt das nichts.",
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
            "text": "Diese Beschlüsse betreffen Haushaltsjahre, die länger zurückliegen. "
                    "Die Fristen dazu nennt § 95b GemO; der Abstand steht bei jedem Posten.",
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

def protokolltext(sitzung: dict, protokolle: dict) -> str:
    """Den Text des Beschlussprotokolls einer Sitzung, falls vorhanden.

    Dieselbe Zuordnung wie beim Auslesen der Beschluesse: Der Dateiname traegt
    Datum und Gremium. Mehrere Dateien zu einer Sitzung werden aneinander
    gehaengt — welche den gesuchten Punkt enthaelt, ist nicht vorhersehbar.
    """
    if not sitzung.get("protokolle"):
        return ""
    tag = sitzung["start"][:10]
    erwartet = f"{tag}_{dateiname(sitzung['titel'])}"
    teile = [pdf_text(pfad) for pfad in protokolle.get(tag, [])
             if pfad.stem == erwartet or pfad.stem.startswith(erwartet + "_")]
    return "\n".join(teile)


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

    # Was an einem Tagesordnungspunkt haengt, auch wenn zu ihm nichts
    # beschlossen wurde: die Vorlagennummer und die Unterlagen. Gerade dort
    # steckt der Inhalt — „Information ueber die Fortschreibung der
    # Elternbeitraege" hat eine Sitzungsvorlage, aber keinen Beschluss.
    punkt_infos: dict[tuple[str, str], dict] = {}
    for p in punkte:
        if p.get("titel"):
            punkt_infos[(p["datum"], p["titel"].strip())] = {
                "vorlage": p.get("vorlage") or "",
                "dokumente": p.get("dokumente") or [],
            }

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
        # Nach ISO-Jahr einsortieren, nicht nach Kalenderjahr. Der 01.01.2027
        # liegt im Kalenderjahr 2027, gehoert aber zur ISO-Woche 2026-W53:
        # Nach Kalenderjahr gefiltert landete er als „KW 53 des Jahrgangs
        # 2027" in der Ablage — ein Datum, das es nicht gibt. Der Aufbau des
        # Berichtszeitraums waere mit ValueError abgebrochen und mit ihm der
        # ganze Lauf. Derzeit ist keine Sitzung des Bestands betroffen; der
        # naechste Jahreswechsel kann eine bringen.
        if tag.isocalendar()[0] != jahr or s["start"][:10] > bis:
            continue
        kw = tag.isocalendar()[1]
        w = wochen[kw]
        name = gremium(s["titel"])
        tag_iso = s["start"][:10]
        ptext = protokolltext(s, protokolle)
        w["sitzungen"].append({"datum": tag, "gremium": name, "kuerzel": kuerzel(name),
                               "protokoll": bool(s["protokolle"]),
                               # Die vollstaendige Tagesordnung mitfuehren: Die
                               # Ausgabe zeigte bisher nur, was beschlossen wurde.
                               # Die Gemeinderatssitzung vom 20.07.2026 hatte 14
                               # Punkte und acht Beschluesse — worueber sonst noch
                               # beraten wurde, etwa die Elternbeitraege in den
                               # Kindertagesstaetten, war nirgends zu sehen.
                               "tops": [str(x) for x in (s.get("tops") or [])],
                               "url": s.get("url") or "",
                               # Der Protokolltext wird fuer die Vermerke zu
                               # Punkten ohne Beschluss gebraucht.
                               "protokolltext": ptext,
                               # Zu jedem Punkt, was ueber ihn bekannt ist:
                               # Vorlagennummer und Unterlagen aus der
                               # Tagesordnung, Vermerk aus dem Protokoll.
                               # Gerade bei Punkten ohne Beschluss ist das
                               # alles, was es gibt — und es ist mehr als
                               # nichts.
                               "punkte": [
                                   {"titel": str(x).strip(),
                                    **punkt_infos.get((tag_iso, str(x).strip()),
                                                      {"vorlage": "", "dokumente": []}),
                                    "vermerk": vermerk_lesen(ptext, str(x)),
                                    # Worum es ging, steht in der
                                    # Sitzungsvorlage — geladen wird sie nur
                                    # fuer Punkte ohne Beschluss, denn nur
                                    # dort fehlt die Auskunft.
                                    "sachverhalt": sachverhalt_lesen(
                                        VORLAGEN / (re.sub(
                                            r"[^A-Za-z0-9-]+", "-",
                                            punkt_infos.get(
                                                (tag_iso, str(x).strip()), {}
                                            ).get("vorlage", "")) + ".pdf"),
                                        WORTSCHATZ, HAEUFIGKEITEN)
                                    if punkt_infos.get(
                                        (tag_iso, str(x).strip()), {}
                                    ).get("vorlage") else ""}
                                   for x in (s.get("tops") or [])]})
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
                b["titel"] = titel_je_vorlage.get(b["vorlage"])
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
    # Nach ISO-Jahr vergleichen, nicht nach Kalenderjahr — sonst legt der
    # 01.01.2027 (Kalenderjahr 2027, ISO-Woche 2026-W53) eine Woche 53 im
    # Jahrgang 2027 an, den es nicht gibt, und `fromisocalendar` bricht den
    # ganzen Lauf ab. Umgekehrt bekaeme die echte Woche 2026-W53 gar keine
    # Ausgabe. Dieselbe Verwechslung wie beim Einsortieren der Sitzungen.
    if stichtag.isocalendar()[0] == jahr:
        wochen[stichtag.isocalendar()[1]]  # legt bei Bedarf eine leere Woche an

    # Und jede Woche, zu der bereits eine Ausgabe erschienen ist, wird wieder
    # mitgebaut — auch wenn in ihr nicht getagt wurde.
    #
    # Sonst entsteht eine verwaiste Seite: KW 37/2026 wurde als laufende Woche
    # erzeugt, blieb ohne Sitzung und wurde nie wieder angefasst. Verlinkt war
    # sie weiterhin, aus Archiv und Startseite. Als sich der Seitenfuss
    # aenderte, trug sie als einzige Ausgabe des Jahrgangs noch den alten —
    # und niemandem waere das aufgefallen, weil die Seite einwandfrei aussieht.
    for kw in (erschienen or {}):
        # Nur bis zum Stichtag. Ohne diese Schranke legte ein Lauf mit einem
        # zurueckdatierten --bis auch alle spaeteren Wochen an und berechnete
        # ihre Zeitraeume neu — mit einem Ende vor dem Anfang
        # („Berichtszeitraum 02.03.–01.03.2026") und leerer Sitzungsliste.
        # Geschrieben wurde das ins Register, wo es stehen blieb.
        try:
            if dt.date.fromisocalendar(jahr, int(kw), 1) <= stichtag:
                wochen[int(kw)]
        except ValueError:                # KW 53 in einem Jahr mit 52 Wochen
            continue

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
        # Genau eine Woche kann noch laufen: die, in der der Stichtag liegt —
        # und auch die nur, solange der Stichtag vor ihrem Sonntag liegt.
        #
        # Die Definition muss so eng sein. „Endet nach dem Stichtag" waere
        # falsch: Ein Lauf mit zurueckdatiertem --bis erklaerte damit jede
        # spaetere Woche fuer laufend. Und „endet am Stichtag oder spaeter"
        # ebenfalls: Ein Montagslauf, dessen Stichtag wegen einer abends noch
        # ausstehenden Sitzung auf den Sonntag zurueckfaellt, erklaerte die
        # gerade abgeschlossene Vorwoche wieder fuer laufend — und verwuerfe
        # ihren veroeffentlichten Zeitraum.
        j_iso, kw_iso, _ = stichtag.isocalendar()
        laeuft_noch = ((jahr, kw) == (j_iso, kw_iso)
                       and stichtag < dt.date.fromisocalendar(jahr, kw, 7))

        # Ein einmal veroeffentlichter Berichtszeitraum bleibt stehen. Er ist
        # eine Zusage an den Leser: Wuerde ein spaeterer Lauf ihn verschieben,
        # aenderte sich rueckwirkend, worueber eine bereits gelesene Ausgabe
        # berichtet hat. Nur die laufende Woche ist keine solche Zusage — sie
        # waechst noch, und ihr Zeitraum wird bei jedem Lauf neu bestimmt.
        gemeldet = {} if laeuft_noch else (erschienen or {}).get(f"{kw:02d}", {})
        if gemeldet.get("von_iso") and gemeldet.get("bis_iso"):
            beginn = dt.date.fromisoformat(gemeldet["von_iso"])
            ende = dt.date.fromisoformat(gemeldet["bis_iso"])
            # Der veroeffentlichte Zeitraum wird gehalten — aber er darf nicht
            # kleiner sein als das, was die Ausgabe tatsaechlich enthaelt.
            #
            # Sitzungen werden nach ihrer Kalenderwoche einsortiert, nicht nach
            # diesem Zeitraum. Faellt ein Tageslauf aus, friert die Woche am
            # Stand des letzten Laufs ein, waehrend eine Sitzung von Mittwoch
            # weiterhin in ihr landet: Die Ausgabe listet dann einen Beschluss
            # von einem Datum, das ihr eigener Berichtszeitraum nicht abdeckt —
            # und die Folgeausgabe fuehrt dieselben Tage noch einmal.
            #
            # **Erweitern** ist dabei unbedenklich: Es entsteht keine Luecke
            # und keine Doppelung, der Zeitraum deckt nur wieder ab, was in der
            # Ausgabe steht. Nur Schrumpfen waere ein Wortbruch.
            spaeteste = max((x["datum"] for x in w["sitzungen"]), default=None)
            if spaeteste and spaeteste > ende:
                ende = min(spaeteste, stichtag)
        else:
            beginn = (anker + dt.timedelta(days=1) if anker
                      else dt.date.fromisocalendar(jahr, kw, 1))
            ende = min(dt.date.fromisocalendar(jahr, kw, 7), stichtag)
        letztes_ende = ende
        w["von"], w["bis"] = beginn, ende
        # Sitzungen ohne Protokoll aus dem gesamten Berichtszeitraum aufnehmen,
        # nicht nur aus der Kalenderwoche selbst.
        # Die Tagesordnung wird mitgefuehrt: Sie steht im
        # Ratsinformationssystem, sobald die Sitzung einberufen ist — also
        # lange bevor das Protokoll erscheint. Fuer eine Ausgabe, in der noch
        # kein Beschluss nachlesbar ist, ist sie das einzige, was ueberhaupt
        # etwas ueber die Sitzung sagt.
        ohne = [
            {"datum": dt.date.fromisoformat(x["start"][:10]),
             "gremium": gremium(x["titel"]),
             "tops": x.get("tops") or [],
             "url": x.get("url") or ""}
            for x in alle
            if not x["protokolle"]
            and beginn <= dt.date.fromisoformat(x["start"][:10]) <= ende
        ]
        # Frische Sitzungen gehoeren nicht unter „Blinder Fleck". Zu ihnen
        # *kann* noch kein Protokoll vorliegen, und die Rubrik rahmt ein
        # Fehlen als Auffaelligkeit. Sie werden getrennt als „steht noch aus"
        # gefuehrt — gezaehlt werden sie weiterhin, nur nicht beanstandet.
        grenze = stichtag - dt.timedelta(days=KARENZ_TAGE)
        w["blind"] = [b for b in ohne if b["datum"] <= grenze]
        w["ausstehend"] = [b for b in ohne if b["datum"] > grenze]
        # Laeuft die Woche noch? Dann ist die Ausgabe ein Zwischenstand und
        # sagt das auch. Ohne den Hinweis liest sich eine Ausgabe, die am
        # Mittwoch gebaut wurde, wie die fertige Bilanz der Woche — und „keine
        # Beschluesse" wie ein Befund statt wie ein Zwischenstand.
        #
        # Entscheidend ist der Stichtag, nicht das Ende des Berichtszeitraums:
        # KW 37/2026 endet am 11.09., weil dort der damalige Stichtag lag — die
        # Woche selbst ist laengst vorbei. Am Zeitraumende gemessen haette sich
        # jede solche Ausgabe dauerhaft „laufend" genannt.
        w["laufend"] = laeuft_noch
        spaeter = [x for x in alle if dt.date.fromisoformat(x["start"][:10]) > ende]
        w["naechste"] = spaeter[0] if spaeter else None
        w["kuenftig"] = kuenftig
    return dict(sorted(wochen.items()))


# ------------------------------------------------------------------ Rendern

def e(t: str) -> str:
    return html.escape(t, quote=False)




DISCLAIMER = """
  <div class="kasten">
    <p class="lab">Privates Lernprojekt &middot; maschinell erzeugt &middot; ohne Gew&auml;hr</p>
    <p>F&uuml;r Richtigkeit, Vollst&auml;ndigkeit und Aktualit&auml;t wird keine
    Gew&auml;hr &uuml;bernommen. <b>Verbindlich ist ausschlie&szlig;lich das
    Originaldokument der Stadt Bad Waldsee.</b></p>
    <details class="mehr">
      <summary>Ausf&uuml;hrlicher Hinweis</summary>
      <p>Diese Auswertung beschreibt, was in den Unterlagen steht. Sie sucht nicht nach
      Missst&auml;nden und bewertet weder die Arbeit der Verwaltung noch die einzelner
      Personen; rechtswidriges oder schuldhaftes Verhalten wird niemandem unterstellt.</p>
      <p>Die Publikation ist ein privates Lern- und Technologieprojekt, kein
      journalistisches Erzeugnis, kein Pr&uuml;fbericht und keine rechtliche oder fachliche
      Bewertung. Alle Angaben beruhen auf maschineller Verarbeitung von PDF-Dokumenten;
      Fehler bei Texterkennung und Zuordnung sind m&ouml;glich. Einordnungen und Wertungen sind als
      <b>KI-Deutung</b> gekennzeichnet: maschinell erzeugt und nicht redaktionell
      gepr&uuml;ft. Namen von Privatpersonen werden nicht wiedergegeben. Korrekturen sind
      erw&uuml;nscht und werden zeitnah eingearbeitet. Es besteht keine Verbindung zur
      Stadt Bad Waldsee.</p>
    </details>
  </div>
"""


def artikel(gremium: str) -> str:
    """Bestimmter Artikel zu einem Gremiumsnamen, im Nominativ.

    Alle zwoelf Gremien der Stadt sind maennlich — Gemeinderat, Ortschaftsrat,
    Ausschuss, Beirat, Arbeitskreis — bis auf die Baumkommission. Die Regel
    haengt deshalb an der Endung und nicht an einer Liste, die beim naechsten
    neuen Gremium veraltet.
    """
    name = gremium.lower()
    return "die" if name.endswith(("kommission", "gruppe", "runde")) else "der"


def beschlossene_punkte(w: dict, datum, gremium: str) -> set[str]:
    """Titel der Tagesordnungspunkte einer Sitzung, zu denen ein Beschluss steht.

    Verglichen wird ueber die **Vorlagennummer**, nicht ueber den Titel: Der
    Beschlusstitel stammt aus der Tagesordnung des Ratsinformationssystems,
    der Punkttitel aus der Sitzungsseite — sie sind meist, aber nicht immer
    zeichengleich. Wo sie auseinanderfielen, galt derselbe Punkt einmal als
    beschlossen und einmal als offen und wurde doppelt gezaehlt: „8 Themen"
    und daneben „6 mit Beschluss, 4 ohne".

    Punkte ohne Vorlagennummer — Formalia meist — werden weiterhin ueber den
    Titel verglichen; etwas anderes gibt es dort nicht.
    """
    nummern = {b["vorlage"] for b in w["beschluesse"]
               if b["datum"] == datum and b["gremium"] == gremium and b.get("vorlage")}
    titel = {(b.get("titel") or "").strip() for b in w["beschluesse"]
             if b["datum"] == datum and b["gremium"] == gremium}
    sitzung = next((x for x in w["sitzungen"]
                    if x["datum"] == datum and x["gremium"] == gremium), None)
    getroffen = set()
    for d in (sitzung or {}).get("punkte", []):
        if (d.get("vorlage") and d["vorlage"] in nummern) or d["titel"].strip() in titel:
            getroffen.add(d["titel"].strip())
    return getroffen


def ausgabe_bauen(jahr: int, kw: int, w: dict, einordnung: dict | None) -> str:
    mo, so = w["von"], w["bis"]
    n_besch = len(w["beschluesse"])
    mit_prot = sum(1 for s in w["sitzungen"] if s["protokoll"])
    # Alle Tagesordnungspunkte des Zeitraums. Die Zeile nannte Sitzungen und
    # Beschluesse — aber nicht, wie viele Themen dazwischen lagen. Bei elf
    # Beschluessen waren es achtzehn; die Differenz ist genau das, was sonst
    # unsichtbar bleibt.
    n_themen = sum(len(x.get("tops") or []) for x in w["sitzungen"])
    # Null waere hier eine Behauptung: Wo keine Tagesordnung veroeffentlicht
    # ist, gab es sehr wohl Themen — sie sind nur nicht bekannt. Der
    # Gedankenstrich sagt das, die Null saehe aus wie ein Messwert.

    # Der Untertitel stand auf jeder der 90 Ausgaben Wort fuer Wort gleich:
    # „Was der Gemeinderat und seine Ausschuesse entschieden haben." Er
    # beschrieb die Reihe, nicht diese Ausgabe — und der Platz direkt unter
    # der Ueberschrift ist der, den jeder liest. Dort steht jetzt, was in
    # diesem Zeitraum tatsaechlich los war.
    gremien_kurz = sorted({x["gremium"] for x in w["sitzungen"]})
    n_s, n_b = len(w["sitzungen"]), len(w["beschluesse"])
    strittig_n = sum(1 for b in w["beschluesse"] if b["strittig"])

    if not n_s:
        lede = (f"Zwischen {mo.strftime('%d.%m.')} und {so.strftime('%d.%m.%Y')} "
                "hat kein Gremium der Stadt öffentlich getagt.")
    else:
        wer = (f"tagte {artikel(gremien_kurz[0])} {e(gremien_kurz[0])}"
               if len(gremien_kurz) == 1 else
               f"tagten {len(gremien_kurz)} Gremien in {n_s} Sitzungen")
        if n_s == 1:
            # Ein genaues Datum ist mehr wert als eine Zeitspanne, und der
            # Berichtszeitraum steht ohnehin eine Zeile tiefer. `capitalize()`
            # taugt dafuer nicht: Es macht aus „der Verwaltungsausschuss" ein
            # „Der verwaltungsausschuss".
            wer = (f"{artikel(gremien_kurz[0]).capitalize()} <b>{e(gremien_kurz[0])}</b> "
                   f"tagte am {w['sitzungen'][0]['datum'].strftime('%d.%m.%Y')}")
        if n_b:
            bilanz = (f"{n_b} {'Beschluss' if n_b == 1 else 'Beschlüsse'} "
                      "sind daraus nachlesbar")
            if strittig_n:
                bilanz += (f", {strittig_n} davon "
                           f"{'fiel' if strittig_n == 1 else 'fielen'} nicht einstimmig")
        else:
            bilanz = "nachlesbare Beschlüsse liegen daraus noch nicht vor"
        lede = (f"{wer} — {bilanz}." if n_s == 1 else
                f"Zwischen {mo.strftime('%d.%m.')} und {so.strftime('%d.%m.%Y')} "
                f"{wer} — {bilanz}.")

    if w.get("laufend"):
        sonntag = dt.date.fromisocalendar(jahr, kw, 7)
        laufend_hinweis = (
            f'\n  <p class="zwischenstand"><b>Diese Woche läuft noch.</b> '
            f'Die Ausgabe zeigt den Datenstand vom {so.strftime("%d.%m.%Y")} und wächst bis '
            f'Sonntag, {sonntag.strftime("%d.%m.%Y")}. Was danach noch protokolliert '
            f'wird, erscheint hier, sobald es abrufbar ist.</p>')
    else:
        laufend_hinweis = ""

    t = [kopf(f"Ratswoche KW {kw}/{jahr} · Ratsakten Bad Waldsee", hoch="../../",
          beschreibung=f"Was der Gemeinderat und seine Ausschüsse in der "
                       f"Kalenderwoche {kw}/{jahr} entschieden haben.",
          koerper=""),
     '<div class="wrap">']
    # Die Lage wird vor dem Kopf bestimmt: Der Untertitel nennt sie, und
    # eine spaetere Aenderung an `lede` waere wirkungslos — der Kopf ist
    # dann laengst gebaut.
    lage_zeigt_sitzungen = False
    # Jeder Begriff wird in einer Ausgabe nur einmal aufgemacht — beim
    # ersten Vorkommen. Beim zweiten stoert die Erklaerung mehr, als sie
    # hilft.
    erklaert: set[str] = set()
    # Bloecke, die direkt nach dem Kopf stehen sollen.
    nach_kopf: list[str] = []
    # Bei genau einer Sitzung steht die Auskunft schon im Untertitel. Ein
    # Block, der sie wiederholt, ist kein Gewinn — nur die Fussnote zur
    # Protokollfrist wird noch gebraucht.
    # An der Zahl der **ausstehenden** Sitzungen entscheiden, nicht an der der
    # Kalenderwoche: `sitzungen` zaehlt die ISO-Woche, `ausstehend` den
    # Berichtszeitraum, der frueher beginnen kann. Fielen sie auseinander,
    # verschwand die zweite Sitzung von der Seite.
    if (len(w.get("ausstehend", [])) == 1 and len(w["sitzungen"]) == 1
            and not w["beschluesse"] and not einordnung):
        lage_zeigt_sitzungen = True
        lede = lede.replace(
            "nachlesbare Beschlüsse liegen daraus noch nicht vor.",
            "das Beschlussprotokoll steht noch aus.*")
        # Solange kein Beschluss nachlesbar ist, ist die Tagesordnung das
        # Einzige, was ueber die Sitzung bekannt ist — und bekannt ist sie,
        # denn ohne sie waere nicht eingeladen worden. Ohne sie bleibt eine
        # Ausgabe uebrig, die nichts erzaehlt.
        offen = w["ausstehend"][0]
        # Dieselbe Sitzung bekommt weiter unten einen eigenen Block — mit
        # denselben Punkten, dazu Vorlagennummer, Unterlagen und Sachverhalt.
        # Der Block hier stand aus der Zeit, als es den unteren noch nicht gab;
        # seither stand die Tagesordnung in der aktuellen Ausgabe zweimal auf
        # der Seite, die zweite Fassung reicher als die erste. Bleibt nur die
        # Fussnote zur Protokollfrist, auf die der Stern im Untertitel zeigt.
        eigener_block = any(
            x["datum"] == offen["datum"] and x["gremium"] == offen["gremium"]
            and any(d["titel"] for d in (x.get("punkte") or []))
            for x in w["sitzungen"])
        punkte = "".join(
            f"      <li>{e(str(x))}</li>\n" for x in offen["tops"])
        quelle = (f'    <p class="note"><a class="doc" href="{e(offen["url"])}" '
                  f'target="_blank" rel="noopener noreferrer">Sitzung im '
                  f'Ratsinformationssystem</a></p>\n' if offen["url"] else "")
        if offen["tops"] and not eigener_block:
            nach_kopf.append(
                '<article class="voll">\n'
                '  <div class="body-col">\n'
                '    <p class="rubrik">Tagesordnung</p>\n'
                # Kein erklaerender Satz: Die Ueberschrift sagt bereits, was
                # folgt, und „worueber beraten wurde, steht in der
                # Tagesordnung" sagt dasselbe noch einmal. Der Vorbehalt ist
                # wichtig, aber er gehoert zur Fussnote, die ohnehin dasteht.
                f'    <p class="wann"><b>{e(offen["gremium"])}</b> &middot; '
                f'{offen["datum"].strftime("%d.%m.%Y")}</p>\n'
                f'    <ol class="agenda">\n{punkte}    </ol>\n'
                f'{quelle}'
                f'    <p class="fussnote">* Wie entschieden wurde, sagt erst das '
                f'Protokoll — meist zwei bis {KARENZ_TAGE} Tage nach der Sitzung.</p>\n'
                '  </div>\n'
                '</article>')
        else:
            laufend_hinweis += (
                f'\n  <p class="fussnote">* Beschlussprotokolle sind meist zwei bis '
                f'{KARENZ_TAGE} Tage nach der Sitzung abrufbar.</p>')
    elif (not w["beschluesse"] and not einordnung
            and len(w["sitzungen"]) <= 1):
        # Bei mehreren Sitzungen entfaellt dieser Block: Der Untertitel nennt
        # ihre Zahl, und „Sitzungen in diesem Zeitraum" fuehrt jede einzeln
        # mit Datum und Stand auf. Eine Aufzaehlung derselben Gremien
        # dazwischen war die dritte Nennung derselben Sache.
        n_sitz = len(w["sitzungen"])
        # „Ein Gremium tagte" ist eine Leerformel — welches, ist die Auskunft,
        # auf die es ankommt. Bei einer einzelnen Sitzung steht der Name
        # deshalb im Satz und nicht klein darunter.
        if n_sitz == 1:
            einzige = w["sitzungen"][0]
            satz = (f"{artikel(einzige['gremium']).capitalize()} "
                    f"<b>{e(einzige['gremium'])}</b> tagte am "
                    f"{einzige['datum'].strftime('%d.%m.%Y')} öffentlich. "
                    "Nachlesbare Beschlüsse liegen daraus noch nicht vor.")
        elif n_sitz:
            namen = sorted({x["gremium"] for x in w["sitzungen"]})
            benannt = [f"{artikel(x)} <b>{e(x)}</b>" for x in namen]
            aufzaehlung = (", ".join(benannt[:-1]) + f" und {benannt[-1]}"
                           if len(benannt) > 1 else benannt[0])
            satz = (f"Öffentlich getagt haben {aufzaehlung} — "
                    f"{n_sitz} Sitzungen insgesamt. Nachlesbare Beschlüsse liegen "
                    "daraus noch nicht vor.")
        else:
            satz = "In diesem Zeitraum hat kein Gremium öffentlich getagt."

        # Die ausstehenden Sitzungen gehoeren hierher, nicht in einen zweiten
        # Block darunter — sonst steht dieselbe Sitzung zweimal auf der Seite.
        liste = ""
        if w.get("ausstehend"):
            lage_zeigt_sitzungen = True
        if w.get("ausstehend") and n_sitz == 1:
            # Der Satz nennt Gremium und Datum bereits; eine Liste mit einer
            # Zeile daneben waere dieselbe Angabe ein zweites Mal.
            liste = (f'    <p class="fussnote">* Beschlussprotokolle sind meist zwei bis '
                     f'{KARENZ_TAGE} Tage nach der Sitzung abrufbar.</p>')
            satz = satz.replace("Nachlesbare Beschlüsse liegen daraus noch nicht vor.",
                                "Das Beschlussprotokoll steht noch aus.*")
        elif w.get("ausstehend"):
            zeilen_aus = "".join(
                f'      <li><span class="sache">{e(b["gremium"])}'
                f'<span class="sv">Sitzung vom {b["datum"].strftime("%d.%m.%Y")}</span></span>'
                f'<span class="erg">Protokoll steht aus*</span></li>\n'
                for b in sorted(w["ausstehend"], key=lambda x: x["datum"]))
            liste = (f'    <ul class="beschluesse">\n{zeilen_aus}    </ul>\n'
                     f'    <p class="fussnote">* Beschlussprotokolle sind meist zwei bis '
                     f'{KARENZ_TAGE} Tage nach der Sitzung abrufbar.</p>')

        t.append(f"""
<article class="voll">
  <div class="body-col">
    <p class="rubrik">Zur Lage</p>
    <p class="lage">{satz}</p>
{liste}
  </div>
</article>""")


    t.append(f"""
<header>
  <p class="eyebrow">{'Wochenausgabe &middot; Zwischenstand' if w.get('laufend') else 'Wochenausgabe'}</p>
  <h1>Waldseer Ratswoche <span class="nummer">KW {kw} / {jahr}</span></h1>
  <p class="lede">{lede}</p>
  <div class="issueline">
    <span><b>Berichtszeitraum</b> {mo.strftime('%d.%m.')}–{so.strftime('%d.%m.%Y')}</span>
    <span><b>Sitzungen</b> {len(w['sitzungen'])} · {mit_prot} protokolliert</span>
    <span><b>Themen</b> {n_themen or '—'}</span>
    <span><b>Beschlüsse</b> {n_besch}</span>
  </div>{laufend_hinweis}
</header>""")

    # Was direkt nach dem Kopf steht — derzeit die Tagesordnung einer Sitzung,
    # deren Protokoll noch aussteht. Sie gehoert nach vorn: In einer Ausgabe
    # ohne Beschluesse ist sie das Einzige mit Inhalt.
    t.extend(nach_kopf)

    # Reihenfolge: erst die Sache, dann die Sprache, dann die Deutung.
    #
    # Frueher stand die Einordnung ganz oben — ausgerechnet der Abschnitt,
    # der als KI-Deutung gekennzeichnet und ausdruecklich nicht
    # redaktionell geprueft ist. Das Erste, was ein Leser sah, war damit
    # das Unsicherste der Seite, und die Beschluesse kamen an vierter
    # Stelle. Fuer ein Projekt, dessen Kern die Aktenlage ist, war das eine
    # Schieflage — nicht im Wort, sondern in der Anordnung.

    # --- Welche Sitzungen es gab
    #
    # Der Ueberblick fehlte: Die Ausgabe sprang direkt zu den Beschluessen und
    # liess offen, welche Gremien ueberhaupt getagt haben und wie umfangreich.
    # Wer wissen wollte, ob seine Ortschaft dabei war, musste die ganze Seite
    # lesen. Hier steht es in einer Zeile je Sitzung — mit dem Weg zu den
    # Beschluessen, sofern es welche gibt.
    if len(w["sitzungen"]) > 1 or (w["sitzungen"] and w["beschluesse"]):
        zeilen_s = []
        for x in sorted(w["sitzungen"], key=lambda y: (y["datum"], y["gremium"])):
            marke = f"s-{x['datum']:%Y%m%d}-{x['kuerzel']}"
            # Beides verlinken, was es zu sehen gibt: die Beschluesse und
            # die uebrigen Punkte derselben Sitzung. Wer nach einem Thema
            # sucht, das nicht beschlossen wurde, kommt sonst nicht hin.
            # Nur sachliche Punkte zaehlen — dieselbe Auswahl wie im Block
            # darunter. Sonst versprach die Uebersicht "6 weitere Themen" und
            # der Sprung fuehrte zu zweien.
            beschlossen_hier = beschlossene_punkte(w, x["datum"], x["gremium"])
            weitere = sum(1 for top in x["tops"]
                          if top.strip() and top.strip() not in beschlossen_hier)
            # Durchgehend Themen zaehlen, nicht Beschluesse.
            #
            # Vorher stand hier „7 Beschluesse · 4 weitere Themen" neben „8
            # Themen" — zwei verschiedene Einheiten in einer Zeile, und die
            # Summe ging nicht auf. Ein Tagesordnungspunkt kann mehrere
            # Beschluesse tragen: „Wirtschaftsplaene mit Finanzplanung" sind
            # vier Beschluesse zu einem Thema. Wie viele Beschluesse es sind,
            # sagt die Ueberschrift des Blocks.
            mit_beschluss = len(beschlossen_hier)
            teile = []
            if mit_beschluss:
                teile.append(f'<a href="#{marke}">{mit_beschluss} '
                             f"{'Thema' if mit_beschluss == 1 else 'Themen'} "
                             f"mit Beschluss</a>")
            # „ohne" ist die Ellipse zu „mit Beschluss" davor — steht das
            # erste Stueck nicht da, bleibt ein angefangener Satz uebrig:
            # „4 Themen ohne". Dann wird ausgeschrieben.
            #
            # Und: „ohne Beschluss" setzt ein Protokoll voraus. Nur dort
            # steht, worueber nicht entschieden wurde. Fehlt es, ist ueber
            # die Punkte gar nichts bekannt — der Arbeitskreis vom
            # 31.03.2025 hat vier Themen und kein Protokoll, und die Zeile
            # behauptete, zu allen vieren sei nichts beschlossen worden.
            if weitere and x["protokoll"]:
                teile.append(f'<a href="#{marke}-tops">{weitere} '
                             f"{'Thema' if weitere == 1 else 'Themen'} ohne"
                             f"{'' if mit_beschluss else ' Beschluss'}</a>")
            # Die Zeile geht von selbst auf, seit jedes Thema in der Liste
            # steht: Beschluesse plus weitere Themen ergeben die Themenzahl.
            # Solange Formalpunkte gesondert behandelt wurden, fehlte hier
            # ein Rest, der eigens benannt werden musste.

            if not teile:
                # „Steht noch aus" gilt nur, solange die Frist laeuft. Bei einer
                # Sitzung von 2024 steht nichts mehr aus — dort ist schlicht
                # keines abrufbar, und das ist eine andere Aussage.
                if not x["protokoll"]:
                    # `ausstehend` fuehrt genau die Sitzungen innerhalb der
                    # Karenzfrist — dieselbe Quelle, aus der sich auch
                    # entscheidet, was unter „Blinder Fleck" steht.
                    frisch = any(a["datum"] == x["datum"]
                                 and a["gremium"] == x["gremium"]
                                 for a in w.get("ausstehend", []))
                    stand = ("Protokoll steht noch aus" if frisch
                             else "kein Protokoll abrufbar")
                    # Der Weg zur Tagesordnung bleibt: Sie ist bei diesen
                    # Sitzungen das Einzige, was ueberhaupt vorliegt.
                    teile.append(f'<a href="#{marke}-tops">{stand}</a>'
                                 if x["tops"] else stand)
                else:
                    teile.append("kein Beschluss protokolliert")
            was = " &middot; ".join(teile)
            punkte = (f"{len(x['tops'])} "
                      f"{'Thema' if len(x['tops']) == 1 else 'Themen'}"
                      if x["tops"] else "Tagesordnung nicht veröffentlicht")
            zeilen_s.append(
                f'      <li><span class="sache">'
                f'{markieren(e(x["gremium"]), erklaert)}'
                f'<span class="sv">{x["datum"]:%d.%m.%Y} &middot; {punkte}</span>'
                f'</span><span class="erg">{was}</span></li>')
        t.append(
            '<article class="voll">\n'
            '  <div class="body-col">\n'
            '    <p class="rubrik">Sitzungen in diesem Zeitraum</p>\n'
            '    <ul class="beschluesse">\n'
            + "\n".join(zeilen_s) + "\n"
            '    </ul>\n'
            '  </div>\n'
            '</article>')

    # --- Wenn nichts entschieden wurde, das ausdrücklich sagen
    #
    # Der Block sagt die Lage in einem Satz und zeigt danach, was war. Vorher
    # nannte die Seitenspalte hier nur „Beschluesse 0" — ausgerechnet dort,
    # wo die Null steht, fehlte die Zahl, die zeigt, dass trotzdem getagt
    # wurde. Die Ausgaben mit redaktioneller Einordnung nannten die Sitzungen
    # laengst; das war eine Inkonsistenz, keine Gestaltung.
    # --- Beschlüsse
    if w["beschluesse"]:
        je_gremium: dict[tuple, list] = collections.defaultdict(list)
        for b in w["beschluesse"]:
            je_gremium[(b["datum"], b["gremium"], b["kuerzel"])].append(b)
        for (tag, name, kz), liste in sorted(je_gremium.items()):
            marke = f"s-{tag:%Y%m%d}-{kz}"
            sitzung = next((x for x in w["sitzungen"]
                            if x["datum"] == tag and x["gremium"] == name), None)
            n_tops = len((sitzung or {}).get("tops", []))
            # Die Ueberschrift nannte nur die Beschluesse und verschwieg,
            # dass die Sitzung mehr Punkte hatte. „8 Beschluesse" klang nach
            # der ganzen Sitzung; es waren 8 von 14.
            # Beschluesse und Themen sind nicht dasselbe: Zu einem Thema
            # koennen mehrere Beschluesse gefasst werden. Die Ueberschrift
            # nennt deshalb beides, wenn es auseinanderfaellt.
            themen_hier = len(beschlossene_punkte(w, tag, name)) or len(liste)
            ueberschrift = (
                f"{len(liste)} {'Beschluss' if len(liste) == 1 else 'Beschlüsse'} "
                f"zu {themen_hier} {'Thema' if themen_hier == 1 else 'Themen'} "
                f"am {datum_lang(tag)}"
                if themen_hier != len(liste) else
                f"{len(liste)} {'Beschluss' if len(liste) == 1 else 'Beschlüsse'} "
                f"am {datum_lang(tag)}")
            t.append(f"""
<article id="{marke}">
  <div class="rail">
    <div class="field"><span class="lab">Sitzung</span><span class="val">{e(name)}</span></div>
    <div class="field"><span class="lab">Datum</span><span class="val">{tag.strftime('%d.%m.%Y')}</span></div>
    <div class="field"><span class="lab">Themen</span><span class="val">{n_tops or '—'}</span></div>
    <div class="field"><span class="lab">Beschlüsse</span><span class="val">{len(liste)}</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Beschlossen · {e(rubrikname(name))}</p>
    <h2 class="headline">{ueberschrift}</h2>
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
                # Erst maskieren, dann markieren: `markieren` erwartet
                # Text ohne eigenes Markup und setzt selbst welches.
                wortlaut = (f"""<span class="wortlaut">"""
                            f"""{markieren(e(b['wortlaut']), erklaert)}</span>"""
                            if b.get("wortlaut") else "")
                # Worum es ging, aus der Sitzungsvorlage. Der Beschluss sagt,
                # **was** entschieden wurde; der Sachverhalt, **warum** es zur
                # Entscheidung kam. „Fuer das Kindergartenjahr 2026/2027
                # empfehlen die Kirchen eine Erhoehung um 4,5 %" steht in
                # keinem Protokoll.
                sachlage = ""
                if b.get("vorlage"):
                    txt = sachverhalt_lesen(
                        VORLAGEN / (re.sub(r"[^A-Za-z0-9-]+", "-", b["vorlage"]) + ".pdf"),
                        WORTSCHATZ, HAEUFIGKEITEN)
                    if txt:
                        sachlage = (f'<span class="sachlage">'
                                    f'{markieren(e(txt), erklaert)}</span>')
                unterlagen = ""
                if b.get("dokumente"):
                    verweise = "".join(
                        f'<a href="{d["url"]}" target="_blank" rel="noopener noreferrer">'
                        f'{e(d["titel"])}</a>' for d in b["dokumente"])
                    unterlagen = f'<span class="unterlagen">{verweise}</span>' 
                t.append(f"""      <li><span class="sache">"""
                         f"""{markieren(e(b['titel']), erklaert)}"""
                         f"""<span class="sv">{e(b['vorlage'] or '—')}{geld}</span>"""
                         f"""{sachlage}{wortlaut}{unterlagen}</span>"""
                         f"""<span class="erg{klasse}">{e(b['ergebnis'])}</span></li>""")
            t.append("    </ul>")
            if any(b["strittig"] for b in liste):
                st = [b for b in liste if b["strittig"]]
                t.append(f"""    <div class="kasten">
      <p class="lab">Nicht einstimmig</p>
      <p>{len(st)} von {len(liste)} Beschlüssen fielen nicht einstimmig:
      {', '.join(f"<b>{e(b['vorlage'] or '—')}</b> ({e(b['ergebnis'])})" for b in st)}.
      Die Schreibweise steht für Ja : Nein : Enthaltungen.</p>
    </div>""")
            # --- Punkte derselben Sitzung, zu denen kein Beschluss vorliegt
            #
            # Die Ausgabe zeigte bisher nur, was beschlossen wurde. Eine
            # Sitzung hat aber mehr Punkte: Berichte, Kenntnisnahmen,
            # Informationen. Die Gemeinderatssitzung vom 20.07.2026 hatte 14
            # Punkte und acht Beschluesse — worueber sonst beraten wurde,
            # stand nirgends. Genau dort steckt oft, was Buerger interessiert:
            # „Information ueber die Fortschreibung der Elternbeitraege in
            # Kindertagesstaetten" war unsichtbar.
            #
            # Verglichen wird ueber den Titel: Ein Punkt gilt als behandelt,
            # wenn ein Beschluss dieser Sitzung denselben Titel traegt.
            beschlossen = beschlossene_punkte(w, tag, name)
            offen_tops = [x for x in (sitzung or {}).get("tops", [])
                          if x.strip() and x.strip() not in beschlossen]
            sachlich = offen_tops
            if sachlich:
                # Container ist die Beschlussliste, nicht die Tagesordnung:
                # Deren Stile gelten fuer `.sache`, `.sv`, `.unterlagen` und
                # `.erg` — unter `ol.agenda` griffen sie nicht, die
                # Vorlagennummer klebte am Titel und „Ohne Beschlussfassung"
                # brach in einer zu schmalen Spalte buchstabenweise um. Und
                # eine Nummerierung waere hier irrefuehrend: Die Liste zeigt
                # „1, 2", gemeint sind die Tagesordnungspunkte 3 und 11.
                #
                # Zu jedem Punkt zeigen, was daran haengt: der Vermerk aus dem
                # Protokoll, die Vorlagennummer und die Unterlagen. Ein blosser
                # Titel sagt, dass etwas Thema war; erst das Uebrige sagt, wo
                # man nachlesen kann, worum es ging.
                infos = {x["titel"]: x for x in (sitzung or {}).get("punkte", [])}
                zeilen_tops = ""
                for x in sachlich:
                    d = infos.get(x.strip(), {})
                    zusatz = []
                    if d.get("vorlage"):
                        zusatz.append(f'<span class="sv">{e(d["vorlage"])}</span>')
                    if d.get("dokumente"):
                        zusatz.append("".join(
                            f'<span class="unterlagen"><a href="{k["url"]}" '
                            f'target="_blank" rel="noopener noreferrer">'
                            f'{e(k["titel"])}</a></span>' for k in d["dokumente"]))
                    vermerk = (f'<span class="erg">{e(d["vermerk"])}</span>'
                               if d.get("vermerk") else "")
                    # Worum es ging — woertlich aus der Sitzungsvorlage.
                    if d.get("sachverhalt"):
                        zusatz.insert(0, f'<span class="wortlaut">'
                                         f'{markieren(e(d["sachverhalt"]), erklaert)}</span>')
                    zeilen_tops += (
                        f'      <li><span class="sache">{markieren(e(x), erklaert)}'
                        f'{"".join(zusatz)}</span>{vermerk}</li>\n')
                nachsatz = ""
                t.append(f"""    <details class="mehr" id="{marke}-tops" open>
      <summary>{len(sachlich)} {'weiteres Thema' if len(sachlich) == 1 else 'weitere Themen'} ohne Beschluss</summary>
      <ul class="beschluesse">
{zeilen_tops}      </ul>
{nachsatz}
    </details>""")
            t.append("  </div>\n</article>")

    # --- Protokollierte Sitzungen, aus denen kein Beschluss stammt
    #
    # Sie hatten bisher keinen Block: Die Themenliste haengt am Beschlussblock,
    # und den gibt es nur, wo etwas beschlossen wurde. Der Verwaltungsausschuss
    # vom 14.05.2024 hat ein Protokoll und sechs Punkte — sichtbar war davon
    # nichts, und die Sitzungsuebersicht verwies ins Leere.
    for x in sorted(w["sitzungen"], key=lambda y: (y["datum"], y["gremium"])):
        # Auch ohne Protokoll: Die Tagesordnung steht im
        # Ratsinformationssystem, sobald eingeladen wurde. Der Arbeitskreis
        # Kinder, Jugend und Bildung vom 31.03.2025 hat kein Protokoll, aber
        # drei Themen — sichtbar war davon nichts.
        if not x.get("punkte"):
            continue
        if any(b["datum"] == x["datum"] and b["gremium"] == x["gremium"]
               for b in w["beschluesse"]):
            continue                      # hat einen eigenen Beschlussblock
        sach = [d for d in x["punkte"]
                if d["titel"]]
        if not sach:
            continue
        zeilen_o = ""
        for d in sach:
            zusatz = ""
            if d.get("vorlage"):
                zusatz += f'<span class="sv">{e(d["vorlage"])}</span>'
            for k in d.get("dokumente", []):
                zusatz += (f'<span class="unterlagen"><a href="{k["url"]}" '
                           f'target="_blank" rel="noopener noreferrer">'
                           f'{e(k["titel"])}</a></span>')
            if d.get("sachverhalt"):
                zusatz = (f'<span class="wortlaut">'
                          f'{markieren(e(d["sachverhalt"]), erklaert)}</span>') + zusatz
            verm = (f'<span class="erg">{e(d["vermerk"])}</span>'
                    if d.get("vermerk") else "")
            zeilen_o += (f'      <li><span class="sache">'
                         f'{markieren(e(d["titel"]), erklaert)}{zusatz}</span>'
                         f'{verm}</li>\n')
        marke_o = f"s-{x['datum']:%Y%m%d}-{x['kuerzel']}"
        # Der Weg zur Quelle. Er stand bisher nur im Tagesordnungsblock der
        # aktuellen Ausgabe; in den uebrigen Ausgaben fuehrte von diesen
        # Themen aus kein Verweis zur Sitzung im Ratsinformationssystem.
        quelle_o = (f'    <p class="note"><a class="doc" href="{e(x["url"])}" '
                    f'target="_blank" rel="noopener noreferrer">Sitzung im '
                    f'Ratsinformationssystem</a></p>\n' if x.get("url") else "")
        # „Kein Protokoll abrufbar" liest sich wie ein Mangel. Bei einer
        # Sitzung von vorgestern ist es der Normalfall — das Protokoll kann
        # noch gar nicht da sein. `ausstehend` fuehrt genau diese frischen
        # Sitzungen; was aelter als die Karenzfrist ist, steht unter `blind`
        # und wird auch weiterhin als Fehlen benannt.
        if x["protokoll"]:
            fussnote_o = ('Das Protokoll dieser Sitzung weist keinen Beschluss aus. '
                    'Was es zu den einzelnen Punkten vermerkt, steht jeweils '
                    'dahinter.')
        elif any(b["datum"] == x["datum"] and b["gremium"] == x["gremium"]
                 for b in w.get("ausstehend", [])):
            # Die Frist selbst steht schon in der Fussnote zum Stern unter
            # dem Untertitel. Hier nur, was sie fuer diesen Block bedeutet —
            # sonst steht dieselbe Auskunft zweimal auf der Seite.
            fussnote_o = ('Das Beschlussprotokoll steht noch aus; bis dahin ist die '
                    'Tagesordnung alles, was öffentlich vorliegt.')
        else:
            fussnote_o = ('Zu dieser Sitzung ist kein Beschlussprotokoll abrufbar. '
                    'Die Themen stehen in der Tagesordnung; wie entschieden '
                    'wurde, sagt erst das Protokoll.')
        t.append(f"""
<article id="{marke_o}">
  <div class="rail">
    <div class="field"><span class="lab">Sitzung</span><span class="val">{e(rubrikname(x['gremium']))}</span></div>
    <div class="field"><span class="lab">Datum</span><span class="val">{x['datum']:%d.%m.%Y}</span></div>
    <div class="field"><span class="lab">Themen</span><span class="val">{len(x['punkte'])}</span></div>
    <div class="field"><span class="lab">Beschlüsse</span><span class="val">0</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">{'Beraten' if x['protokoll'] else 'Auf der Tagesordnung'} · {e(rubrikname(x['gremium']))}</p>
    <h2 class="headline">{len(sach)} {'Thema' if len(sach) == 1 else 'Themen'} am {datum_lang(x['datum'])}{', kein Beschluss' if x['protokoll'] else ''}</h2>
    <ul class="beschluesse" id="{marke_o}-tops">
{zeilen_o}    </ul>
{quelle_o}    <p class="fussnote">{fussnote_o}</p>
  </div>
</article>""")

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

    # --- Redaktionelle Einordnung, falls hinterlegt
    if einordnung:
        # Auch hier Amtsdeutsch — und diese Absaetze stehen weiter oben als
        # manche Beschlussliste, in der derselbe Begriff sonst zuerst
        # aufgemacht wuerde.
        absaetze = "\n".join(f"    <p>{markieren(e(a), erklaert)}</p>"
                             for a in einordnung.get("absaetze", []))
        geprueft = einordnung.get("status") == "geprueft"
        marke = ('<p class="herkunft geprueft">Redaktionell geprüft</p>' if geprueft else
                 '<p class="herkunft ki">KI-Deutung · am Beleg nachprüfbar</p>')
        fussnote = ("" if geprueft else
                    '\n    <p class="note">Dieser Abschnitt ist eine maschinell erzeugte '
                    'Einordnung. Die genannten Zahlen und Beschlüsse stammen aus den '
                    'Protokollen und sind dort nachprüfbar; die Verknüpfung und Gewichtung '
                    'wurde nicht von einem Menschen geprüft.</p>')
        # Ohne Seitenspalte: Berichtszeitraum und Sitzungszahl stehen schon
        # im Seitenkopf, keine zwei Zentimeter darueber. Dieselbe Doppelung
        # wie beim Lage-Block, nur an der Einordnung.
        t.append(f"""
<article class="voll">
  <div class="body-col">
    <p class="rubrik">{e(einordnung.get('rubrik', 'Zur Lage'))}</p>
    {marke}
    <h2 class="headline">{e(einordnung.get('titel', ''))}</h2>
{absaetze}{fussnote}
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
            # Keine farbliche Unterscheidung mehr: Das Alarmrot liess eine
            # nicht einstimmige Abstimmung wie einen Fehler aussehen. Was ein
            # Punkt ist, sagt seine Ueberschrift — das genuegt und wertet nicht.
            klasse = "kasten"
            bloecke.append(f"""    <div class="{klasse}">
      <p class="lab">{e(h['art'])}</p>
      <p>{markieren(e(h['text']), erklaert)}</p>
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
    Was ein Punkt ist, steht in seiner Überschrift.</p>
{chr(10).join(bloecke)}
  </div>
</article>""")

    # Die Begriffe standen bis hierher als eigener Abschnitt am Ende der
    # Ausgabe. Wer beim Lesen ueber ein Wort stolperte, fand die Antwort
    # erst, wenn er ohnehin schon weiter war — und musste dafuer die
    # Stelle verlassen, an der die Frage aufkam. Die Erklaerungen stehen
    # jetzt im Text, beim ersten Vorkommen des Begriffs: siehe
    # `begriffe.markieren`.

    # --- Sitzungen im Berichtszeitraum, Protokoll noch nicht abrufbar
    # Bewusst vor dem „Blinden Fleck", bewusst wertungsfrei — und bewusst
    # **ohne grosse Ueberschrift**: In der Schlagzeilengroesse der Befunde
    # gesetzt, bekam ein Nicht-Ereignis dasselbe Gewicht wie ein Befund. Die
    # Schieflage steckte nicht im Wort, sondern in der Typografie.
    #
    # Der Block sagt jetzt, was **war** („In diesem Zeitraum tagte ein
    # Gremium oeffentlich"), nicht was fehlt. Die Protokollfrage steht als
    # Nachsatz darunter, wo sie hingehoert.
    if w.get("ausstehend") and not lage_zeigt_sitzungen:
        aus = sorted(w["ausstehend"], key=lambda x: x["datum"])
        zeilen = "".join(
            f"      <li><span class=\"sache\">{markieren(e(b['gremium']), erklaert)}"
            f"<span class=\"sv\">Sitzung vom {b['datum'].strftime('%d.%m.%Y')}</span></span>"
            f"<span class=\"erg\">Protokoll steht aus*</span></li>\n"
            for b in aus)
        t.append(f"""
<article>
  <div class="rail">
    <div class="field"><span class="lab">Sitzungen</span><span class="val">{len(aus)}</span></div>
  </div>
  <div class="body-col">
    <p class="rubrik">Sitzungen im Berichtszeitraum</p>
    <p>In diesem Zeitraum {'tagte ein Gremium' if len(aus) == 1 else 'tagten Gremien'}
    öffentlich:</p>
    <ul class="beschluesse">
{zeilen}    </ul>
    <p class="fussnote">* Beschlussprotokolle sind meist zwei bis {KARENZ_TAGE} Tage
    nach der Sitzung abrufbar.</p>
  </div>
</article>""")

    # --- Blinder Fleck
    if w["blind"]:
        zeilen = "".join(
            f"      <li><span class=\"sache\">{markieren(e(b['gremium']), erklaert)}"
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
    <div class="kasten">
      <p class="lab">Wiederkehrende Rubrik</p>
      <p>Seit Januar 2024 tagten die vier Ortschaftsräte <b>85 Mal öffentlich</b> — rund die
      Hälfte aller öffentlichen Sitzungen der Stadt. Zu keiner dieser Sitzungen ist im
      Ratsinformationssystem eine Niederschrift abrufbar; die Sitzungsseiten enthalten
      Datum und Ort.</p>
      <p>Über den Bestand der Niederschriften sagt das nichts: § 38 Abs. 1 GemO verlangt
      sie, § 38 Abs. 2 Satz 4 GemO gibt Einwohnern ein Einsichtsrecht, eine Pflicht zur
      Veröffentlichung im Internet besteht nicht. Es geht um Zugänglichkeit.</p>
      <p>Nach § 16 Abs. 4 der Hauptsatzung entscheiden die Ortschaftsräte auch
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
    <p>Als Nächstes tagt {artikel(name)} <b>{e(name)}</b> am {datum_lang(tag)} um {uhr} Uhr.</p>
{liste}
  </div>
</article>""")

    # --- Kolophon
    # Der Absatz sprach auch dann von „den Beschluessen dieser Ausgabe", wenn
    # die Ausgabe keinen einzigen enthielt — in einer beschlussfreien Woche
    # las er sich ueber etwas hinweg, das gar nicht da war. Die Haltung ist in
    # beiden Faellen dieselbe; sie muss nur den richtigen Gegenstand nennen.
    if w["beschluesse"]:
        wertschaetzung = """<h3>Zu den Menschen hinter den Beschlüssen</h3>
  <p>Die Beschlüsse dieser Ausgabe stammen aus Sitzungen, die fast ausnahmslos abends
  nach der Arbeit stattfinden. Die Mitglieder der Räte und Ausschüsse tun das
  ehrenamtlich, unter ihrem Namen und in öffentlicher Sitzung — und ihre
  Entscheidungen werden anschließend öffentlich diskutiert. Diese Auswertung misst
  Unterlagen, nicht Personen: Sie zeigt, was in den Akten steht, und sagt nichts
  darüber, mit welcher Sorgfalt oder Absicht jemand entschieden hat.</p>"""
    else:
        wertschaetzung = """<h3>Zu den Menschen hinter den Sitzungen</h3>
  <p>In diesem Berichtszeitraum ist kein Beschluss nachlesbar — das heißt nicht, dass
  nicht gearbeitet wurde. Die Sitzungen der Räte und Ausschüsse finden fast ausnahmslos
  abends nach der Arbeit statt, ehrenamtlich, unter dem eigenen Namen und in
  öffentlicher Sitzung; Vorbereitung, Fraktionssitzungen und Ortstermine kommen hinzu
  und tauchen in keiner Akte auf. Diese Auswertung misst Unterlagen, nicht Personen:
  Sie zeigt, was abrufbar ist, und sagt nichts darüber, was geleistet wurde.</p>"""

    t.append(f"""
<section class="kolophon">
  <p class="rubrik">Zur Ausgabe</p>
  {wertschaetzung}

  <h3>Wie diese Ausgabe entsteht</h3>
  <p>Maschinell erzeugt aus den Beschlussprotokollen und Tagesordnungen des
  <a class="doc" href="https://ris.bad-waldsee.de/" rel="noopener">Ratsinformationssystems
  der Stadt Bad Waldsee</a>.</p>
  <dl class="legende">
    <dt><span class="mono">25 : 0 : 1</span></dt>
    <dd>Ja&nbsp;: Nein&nbsp;: Enthaltungen — <i>Beispiel</i>; in den Beschlüssen
    oben stehen die tatsächlichen Verhältnisse</dd>
    <dt><span class="mono">SV-000/JJJJ</span></dt>
    <dd>Vorlagennummer — damit findet man den Vorgang im Ratsinformationssystem
    unter „Vorlagen“</dd>
  </dl>
  <details class="mehr">
    <summary>Was dabei zu beachten ist</summary>
    <p>Beschlusstitel stammen aus der Tagesordnung, Abstimmungsergebnisse wörtlich aus
    der Zeile „Ergebnis der Beschlussfassung“ des Protokolls. Wo eine Sitzungsvorlage
    oder Anlage vorliegt, ist sie direkt verlinkt; diese Adressen waren im Test über
    Tage hinweg abrufbar, zugesichert ist ihre Haltbarkeit aber nirgends. Die
    Vorlagennummer bleibt der verlässlichere Weg.</p>
    <p>Beschlussprotokolle halten keine Aussprache fest: <em>wie</em> abgestimmt wurde,
    ist nachlesbar, <em>warum</em> nicht. Nichtöffentliche Sitzungsteile sind
    vollständig unsichtbar.</p>
  </details>
{DISCLAIMER}
  <p class="note"><a class="doc" href="../index.html">Alle Ausgaben im Archiv</a></p>
</section>
</div>""")
    t.append(fuss(hoch="../../", meta=f"Ausgabe KW {kw}/{jahr}"))
    return "\n".join(t)


def archiv_bauen(register: dict) -> str:
    """Archiv über alle Jahrgänge, gespeist aus data/ausgaben.json."""
    jahre = sorted(register, reverse=True)
    ges_a = sum(len(register[j]) for j in jahre)
    ges_b = sum(a["beschluesse"] for j in jahre for a in register[j].values())
    ges_s = sum(a["sitzungen"] for j in jahre for a in register[j].values())
    ges_t = sum(a.get("themen", 0) for j in jahre for a in register[j].values())

    t = [kopf("Archiv · Ratsakten Bad Waldsee", hoch="../", hier="archiv",
          beschreibung="Alle bisher erschienenen Wochenausgaben der "
                       "Waldseer Ratswoche."),
     '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Ratswoche &middot; alle Jahrgänge</p>
  <h1>Archiv</h1>
  <p class="lede">Alle bisher erschienenen Ausgaben der Waldseer Ratswoche —
  eine für jede Kalenderwoche, in der getagt wurde.</p>
  <div class="issueline">
    <span><b>Jahrgänge</b> {', '.join(jahre)}</span>
    <span><b>Ausgaben</b> {ges_a}</span>
    <span><b>Sitzungen</b> {ges_s}</span>
    <span><b>Themen</b> {ges_t}</span>
    <span><b>Beschlüsse</b> {ges_b}</span>
  </div>
</header>""")

    for jahr in jahre:
        ausgaben = register[jahr]
        t.append(f"""
<section class="kolophon">
  <p class="rubrik">Jahrgang {jahr}</p>
  <h3>{len(ausgaben)} Ausgaben</h3>
  <ul class="beschluesse">""")
        for kw in sorted(ausgaben, key=int, reverse=True):
            a = ausgaben[kw]
            # Was die Woche umfasst, in einer Zeile: wie viele Gremien getagt
            # haben, worueber, und was davon beschlossen wurde. Bisher stand
            # hier nur die Zahl der Beschluesse; Wochen ohne Beschluss trugen
            # das blosse „ohne Beschluss" und sahen leer aus, obwohl in KW
            # 38/2026 fuenf Themen beraten wurden.
            teile = []
            if a["sitzungen"]:
                teile.append(f"{a['sitzungen']} "
                             f"{'Sitzung' if a['sitzungen'] == 1 else 'Sitzungen'}")
            if a.get("themen"):
                teile.append(f"{a['themen']} "
                             f"{'Thema' if a['themen'] == 1 else 'Themen'}")
            if a["beschluesse"]:
                teile.append(f"{a['beschluesse']} "
                             f"{'Beschluss' if a['beschluesse'] == 1 else 'Beschlüsse'}")
            elif a["sitzungen"]:
                teile.append("ohne Beschluss")
            if a["ohne_protokoll"]:
                teile.append(f"{a['ohne_protokoll']} ohne Protokoll")
            gremien = " · ".join(a["gremien"]) if a["gremien"] else "keine Sitzung"
            t.append(f"""    <li><span class="sache">
      <a class="doc" href="./{jahr}/kw{int(kw):02d}.html">KW {int(kw)} / {jahr}</a>
      <span class="sv">{e(a['zeitraum'])} &middot; {e(gremien)}</span></span>
      <span class="erg weit">{e(' · '.join(teile)) or 'ohne Beschluss'}</span></li>""")
        t.append("  </ul>\n</section>")

    # Die Erscheinungsweise erklaert eine Luecke in der Nummerierung — eine
    # Frage, die erst aufkommt, wenn man die Liste gesehen hat. Ueber der Liste
    # stand sie einem Leser im Weg, der nur zu seiner Ausgabe wollte.
    t.append(f"""
<section class="kolophon">
  <p class="rubrik">Übersicht</p>
  <h3>Erscheinungsweise</h3>
  <p>Es erscheint eine Ausgabe für jede Kalenderwoche, in der mindestens eine Sitzung
  stattgefunden hat, sowie stets eine Ausgabe für die laufende Woche. Dazwischenliegende
  sitzungsfreie Wochen bekommen keine Ausgabe — deshalb ist die Nummerierung
  lückenhaft.</p>
</section>
<section class="kolophon" style="border-bottom:none">
{DISCLAIMER}
  <p class="note"><a class="doc" href="../index.html">Zur Startseite</a></p>
</section>
</div>""")
    t.append(fuss(hoch="../"))
    return "\n".join(t)


def register_lesen() -> dict:
    pfad = DATEN / "ausgaben.json"
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}


def main() -> None:
    p = argparse.ArgumentParser()
    # Ohne --jahr werden alle Jahrgaenge neu gebaut. Frueher war das laufende
    # Jahr die Voreinstellung; dabei blieben 2024 und 2025 auf dem Stand
    # zurueck, den die Skripte zum Zeitpunkt ihres letzten Laufs hatten. Das
    # faellt nicht auf — die Seiten sind da, sie sind nur alt. Genau so standen
    # 51 Ausgaben monatelang mit einem Hinweis auf eine Farbe im Netz, die es
    # nicht mehr gab, und 27 mit einem abgeschnittenen Gremiumsnamen.
    p.add_argument("--jahr", type=int, default=None,
                   help="nur diesen Jahrgang bauen (Vorgabe: alle)")
    p.add_argument("--bis", default=stichtag_vorgabe(),
                   help="Redaktionsschluss; spätere Sitzungen bleiben unberücksichtigt")
    args = p.parse_args()

    einordnungen = einordnungen_laden()
    register = register_lesen()

    # Welche Jahrgaenge? Entweder der genannte oder alle, die es gibt — das
    # laufende Jahr immer, damit eine neue Woche auch ohne Registereintrag
    # entsteht.
    jahre = ([args.jahr] if args.jahr
             else sorted({int(j) for j in register} | {dt.date.today().year}))

    # Erst sammeln, dann rendern. Der Menuepunkt „Aktuelle Ausgabe" braucht
    # sein Ziel, bevor die erste Seite geschrieben wird — das Register auf der
    # Platte ist zu diesem Zeitpunkt noch das des letzten Laufs.
    je_jahr: dict[int, dict] = {}
    for jahr in jahre:
        (AUSGABEN / str(jahr)).mkdir(parents=True, exist_ok=True)
        register.setdefault(str(jahr), {})
        je_jahr[jahr] = wochen_sammeln(jahr, args.bis, register[str(jahr)])

    if any(je_jahr.values()):
        j_neu = max(j for j, w in je_jahr.items() if w)
        aktuelle_ausgabe_setzen(
            f"ausgaben/{j_neu}/kw{max(je_jahr[j_neu]):02d}.html")

    neueste_kw = neuestes_jahr = None
    for jahr in jahre:
        ordner = AUSGABEN / str(jahr)
        wochen = je_jahr[jahr]

        for kw, w in wochen.items():
            schluessel = f"{jahr}-kw{kw:02d}"
            text = ausgabe_bauen(jahr, kw, w, einordnungen.get(schluessel))
            (ordner / f"kw{kw:02d}.html").write_text(text, encoding="utf-8")
            register[str(jahr)][f"{kw:02d}"] = {
                "zeitraum": f"{w['von'].strftime('%d.%m.')}–{w['bis'].strftime('%d.%m.%Y')}",
                "von_iso": w["von"].isoformat(),
                "bis_iso": w["bis"].isoformat(),
                "sitzungen": len(w["sitzungen"]),
                # Die Tagesordnungspunkte der Woche. Im Archiv stand bisher
                # nur die Zahl der Beschluesse — eine Ausgabe ohne Beschluss
                # sah dort leer aus, obwohl beraten wurde. Themen gibt es auch
                # ohne Protokoll, Beschluesse nur mit.
                "themen": sum(len(s["tops"]) for s in w["sitzungen"]),
                "beschluesse": len(w["beschluesse"]),
                "ohne_protokoll": len(w["blind"]),
                # Getrennt gefuehrt, damit Startseite und Archiv eine frische
                # Sitzung nicht als fehlende Unterlage ausweisen.
                "ausstehend": len(w.get("ausstehend", [])),
                "gremien": sorted({s["kuerzel"] for s in w["sitzungen"]}),
                "einordnung": schluessel in einordnungen,
                # Auch ins Register, nicht nur in die Ausgabe: Startseite und
                # Archiv verweisen auf die laufende Woche und stellten sie als
                # fertig dar („zuletzt entschieden"). Genau dort — auf der
                # meistgelesenen Seite — las sich „keine Beschluesse" wieder
                # wie ein Befund statt wie ein Zwischenstand.
                "laufend": bool(w.get("laufend")),
                # Die Abschluss-Regeln dieser Woche mitschreiben. Schritt 09
                # sammelt sie fuer den Abschnitt „Der Regelfall" — so zeigt die
                # Erkenntnisseite genau das, was auch in den Ausgaben steht,
                # statt eine zweite Zaehlung mit eigenem Ergebnis aufzumachen.
                "abschluesse": {h["art"]: h["posten"]
                                for h in auffaelligkeiten(w)
                                if h.get("ton") == "neutral"},
            }
            marke = " ←" if schluessel in einordnungen else ""
            print(f"  KW {kw:2d}/{jahr}  {len(w['sitzungen'])} Sitzung(en), "
                  f"{len(w['beschluesse'])} Beschlüsse, {len(w['blind'])} ohne Protokoll{marke}")

        if wochen:
            neueste_kw, neuestes_jahr = max(wochen), jahr
        print(f"  {len(wochen)} Ausgaben in docs/ausgaben/{jahr}/")

    # Sortiert schreiben, damit die Datei nicht davon abhängt, in welcher
    # Reihenfolge die Jahrgänge erzeugt wurden — sonst entstehen bei jedem Lauf
    # Änderungen, die keine sind.
    (DATEN / "ausgaben.json").write_text(
        json.dumps(register, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    (AUSGABEN / "index.html").write_text(archiv_bauen(register), encoding="utf-8")

    print(f"\nArchiv über {len(register)} Jahrgang/Jahrgänge aktualisiert.")
    if neueste_kw:
        print(f"Neueste Ausgabe: KW {neueste_kw}/{neuestes_jahr}")


if __name__ == "__main__":
    main()
