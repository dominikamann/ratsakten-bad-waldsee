#!/usr/bin/env python3
"""Schritt 3 — Kennzahlen aus Sitzungen und Protokollen berechnen.

Alle Zahlen des Reports entstehen hier und nur hier. Wer eine Angabe im Report
nachrechnen will, findet die Rechenregel in dieser Datei.

Ergebnis: data/kennzahlen.json (und eine lesbare Zusammenfassung auf stdout)

    uv run --with pypdf python scripts/03_auswerten.py [--stichtag 2026-09-09]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

from pypdf import PdfReader

BASIS = Path(__file__).resolve().parent.parent
DATEN = BASIS / "data"

# Reihenfolge ist bedeutsam: Ein Punkt zählt beim ERSTEN Treffer und nur einmal.
THEMEN = [
    ("Formalia ohne Sachinhalt",
     r"^Bekanntgabe|^Informationen des|^Verschiedenes|^Bekanntgaben|"
     r"Einwohnerfragestunde|^Anfragen|Niederschrift|^Gedenken|Ehrung|"
     r"Verabschiedung|Verpflichtung|Vorstellung des|Vorstellung der"),
    ("Bauleitplanung",
     r"Bebauungsplan|Flächennutzungsplan|Satzungsbeschluss|Aufstellungsbeschluss|"
     r"Entwurfsbeschluss|Veränderungssperre|Vorkaufsrecht|Umlegung|Entwidmung"),
    ("Finanzen & Haushalt",
     r"Haushalt|Wirtschaftsplan|Jahresabschl|Finanzbericht|Kredit|Spende|Steuer|"
     r"Gebühr|Beitrag|Abrechnung|Abschlussprüfer|Beteiligungsbericht|Ergebnis 20"),
    ("Bau & Sanierung",
     r"Sanierung|Neubau|Erweiterung|Umbau|Vergabe|Ausschreibung|"
     r"Durchführungsbeschluss|Planungsbeschluss|Herstellung|Abriss|Beschaffung"),
    ("Energie & Klima",
     r"Energie|Klima|Wald|Photovolt|PV-|Solar|Wärme|Ladesäul|Windenerg|Speicher|"
     r"Biosphär|Umwelt"),
    ("Kinder, Schule, Soziales",
     r"Kinder|Schule|Gymnasium|Kita|Betreuung|Jugend|Sozial|Pflege|Integration|Obdachlos"),
    ("Verkehr & Mobilität",
     r"Verkehr|Straße|Radweg|Rad|ÖPNV|Bus|Bahn|Ringzug|Stellplatz|Geschwindigkeit"),
    ("Kultur, Tourismus, Sport",
     r"Kultur|Touris|Sport|Museum|Freibad|Therme|Kurtaxe|Wanderweg|Fest|Musik|"
     r"Gartenschau|Magazin"),
    ("Gremien & Wahlen",
     r"Wahl|Besetz|Bestell|Berufen|Hauptsatzung|Teilortswahl|Ortsvorsteher|"
     r"Entschädigung|Fraktion|Sitzordnung"),
]

ERGEBNIS = re.compile(r"Ergebnis der Beschlussfassung\s*:?\s*(.{0,90})")
AUSZAEHLUNG = re.compile(
    r"\s*Ja-Stimme?n?\(?e?n?\)?\s*(\d+)\s*Nein-Stimme?n?\(?e?n?\)?\s*(\d+)\s*"
    r"Enthaltung(?:en|\(en\))?\s*(\d+)")


def gremium(titel: str) -> str:
    name = re.sub(r",.*", "", titel)
    return "Ausschuss Umwelt/Technik" if name.startswith("Ausschuss für Umwelt") else name


def pdf_text(pfad: Path) -> str:
    """Text eines PDFs, Trennstriche und Umbrüche geglättet."""
    try:
        roh = "\n".join(seite.extract_text() or "" for seite in PdfReader(pfad).pages)
    except Exception:  # noqa: BLE001 — beschädigte PDFs überspringen
        return ""
    return re.sub(r"[­\s]+", " ", roh)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stichtag", default="2026-09-09",
                   help="Sitzungen nach diesem Datum werden ausgeschlossen")
    args = p.parse_args()

    quelle = DATEN / "sitzungen.json"
    if not quelle.exists():  # HINWEIS_01
        raise SystemExit(
            "data/sitzungen.json fehlt. Die Datei ist ein Zwischenergebnis und wird "
            "nicht versioniert — bitte zuerst Schritt 01 ausführen:\n"
            "  uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py")
    alle = json.loads(quelle.read_text(encoding="utf-8"))
    sitzungen = [s for s in alle if s["start"][:10] <= args.stichtag]

    # --- Gremien -----------------------------------------------------------
    je_gremium: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0])
    for s in sitzungen:
        g = je_gremium[gremium(s["titel"])]
        g[0] += 1
        g[1] += 1 if s["protokolle"] else 0
        g[2] += s["n_tops"]

    # --- Themen ------------------------------------------------------------
    themen = collections.Counter()
    for s in sitzungen:
        for titel in s["tops"]:
            for name, muster in THEMEN:
                if re.search(muster, titel, re.I):
                    themen[name] += 1
                    break
            else:
                themen["Sonstige Sachthemen"] += 1

    # --- Abstimmungen ------------------------------------------------------
    je_jahr: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    gesamt = strittig = mit_nein = mit_enthaltung = 0
    modifiziert: list[str] = []
    for pdf in sorted((DATEN / "protokolle").glob("*.pdf")):
        jahr = pdf.name[:4]
        text = pdf_text(pdf)
        modifiziert += [pdf.name[:10]] * len(re.findall(r"Modifizierter Beschluss", text))
        for treffer in ERGEBNIS.finditer(text):
            wert = treffer.group(1)
            zahlen = AUSZAEHLUNG.match(wert)
            einstimmig = bool(re.match(r"\s*[Ee]instimmig", wert))
            if not (zahlen or einstimmig):
                continue
            gesamt += 1
            uneins = False
            if zahlen:
                _ja, nein, enth = (int(x) for x in zahlen.groups())
                mit_nein += 1 if nein else 0
                mit_enthaltung += 1 if enth else 0
                uneins = bool(nein or enth)
            strittig += uneins
            je_jahr[jahr][0] += 1
            je_jahr[jahr][1] += uneins

    kennzahlen = {
        "stichtag": args.stichtag,
        "sitzungen": len(sitzungen),
        "tagesordnungspunkte": sum(s["n_tops"] for s in sitzungen),
        "vorlagen": len({v for s in sitzungen for v in s["vorlagen"]}),
        "dokumente": len({d for s in sitzungen for d in s["pdfs"]}),
        "protokolle": sum(1 for s in sitzungen if s["protokolle"]),
        "gremien": {k: {"sitzungen": v[0], "protokolle": v[1], "tops": v[2]}
                    for k, v in sorted(je_gremium.items(), key=lambda kv: -kv[1][0])},
        "themen": dict(themen.most_common()),
        "abstimmungen": {
            "gesamt": gesamt,
            "einstimmig": gesamt - strittig,
            "nicht_einstimmig": strittig,
            "mit_nein": mit_nein,
            "mit_enthaltung": mit_enthaltung,
            "je_jahr": {j: {"gesamt": v[0], "strittig": v[1]} for j, v in sorted(je_jahr.items())},
        },
        "modifizierte_beschluesse": sorted(modifiziert),
    }
    (DATEN / "kennzahlen.json").write_text(
        json.dumps(kennzahlen, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Zusammenfassung ---------------------------------------------------
    k = kennzahlen
    print(f"Stichtag {k['stichtag']}")
    print(f"  Sitzungen {k['sitzungen']} | TOPs {k['tagesordnungspunkte']} | "
          f"Vorlagen {k['vorlagen']} | Dokumente {k['dokumente']} | "
          f"Protokolle {k['protokolle']}")
    print("\nGremien (Sitzungen / mit Protokoll / TOPs):")
    for name, w in k["gremien"].items():
        quote = w["protokolle"] / w["sitzungen"] * 100
        print(f"  {w['sitzungen']:3d} | {w['protokolle']:3d} ({quote:3.0f}%) | "
              f"{w['tops']:4d}  {name}")
    print("\nThemen:")
    for name, n in k["themen"].items():
        print(f"  {n:4d}  {n / k['tagesordnungspunkte'] * 100:5.1f}%  {name}")
    a = k["abstimmungen"]
    print(f"\nAbstimmungen: {a['gesamt']} | einstimmig {a['einstimmig']} | "
          f"nicht einstimmig {a['nicht_einstimmig']} "
          f"({a['nicht_einstimmig'] / a['gesamt'] * 100:.1f} %)")
    for jahr, w in a["je_jahr"].items():
        print(f"  {jahr}: {w['strittig']:2d}/{w['gesamt']:3d} = "
              f"{w['strittig'] / w['gesamt'] * 100:.1f} %")
    print(f"\n„Modifizierter Beschluss“: {len(k['modifizierte_beschluesse'])}")


if __name__ == "__main__":
    main()
