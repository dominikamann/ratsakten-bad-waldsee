#!/usr/bin/env python3
"""Schritt 7 — die Auswertung als Tabellen zum Selbernachrechnen ausgeben.

Die Kennzahlen liegen als JSON vor, damit können Nicht-Programmierer wenig
anfangen. Diese Tabellen lassen sich in Excel, LibreOffice oder Numbers öffnen,
sortieren und filtern — und damit lässt sich jede Zahl des Reports nachprüfen,
ohne ein einziges Skript auszuführen.

Bewusst ohne Dokument-Links: Die URLs des Ratsinformationssystems enthalten
sitzungsgebundene Token und sind nicht dauerhaft gültig. Stabile Kennung ist die
Vorlagennummer — damit findet man jeden Vorgang im System unter „Vorlagen“.

Ergebnis: data/csv/sitzungen.csv
          data/csv/tagesordnungspunkte.csv
          data/csv/beschluesse.csv

    uv run --with pypdf python scripts/07_tabellen_bauen.py [--stichtag 2026-09-09]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path

from pypdf import PdfReader

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
ZIEL = DATEN / "csv"

ERGEBNIS = re.compile(r"Ergebnis der Beschlussfassung\s*:?\s*(.{0,70})")
VORLAGE = re.compile(r"SV-\d+/\d{4}")
AUSZAEHLUNG = re.compile(
    r"\s*Ja-Stimme?n?\(?e?n?\)?\s*(\d+)\s*Nein-Stimme?n?\(?e?n?\)?\s*(\d+)\s*"
    r"Enthaltung(?:en|\(en\))?\s*(\d+)")

# Semikolon als Trennzeichen und BOM: So öffnet Excel im deutschen Sprachraum
# die Datei direkt richtig, ohne Importdialog.
TRENNER = ";"
KODIERUNG = "utf-8-sig"


def gremium(titel: str) -> str:
    return re.sub(r",.*", "", titel)


def dateiname(titel: str) -> str:
    """Muss der Benennung aus 02_protokolle_laden.py entsprechen."""
    name = re.sub(r",.*", "", titel)
    name = re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", "-", name).strip("-")
    return name[:48]


def pdf_text(pfad: Path) -> str:
    try:
        roh = "\n".join(s.extract_text() or "" for s in PdfReader(pfad).pages)
    except Exception:  # noqa: BLE001
        return ""
    return re.sub(r"[­\s]+", " ", roh)


def schreiben(pfad: Path, spalten: list[str], zeilen: list[dict]) -> None:
    with pfad.open("w", encoding=KODIERUNG, newline="") as f:
        schreiber = csv.DictWriter(f, fieldnames=spalten, delimiter=TRENNER)
        schreiber.writeheader()
        schreiber.writerows(zeilen)
    print(f"  {pfad.relative_to(WURZEL)}  —  {len(zeilen)} Zeilen")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stichtag", default="2026-09-09",
                   help="Sitzungen nach diesem Datum bleiben unberücksichtigt")
    args = p.parse_args()

    quelle = DATEN / "sitzungen.json"
    if not quelle.exists():
        raise SystemExit(
            "data/sitzungen.json fehlt. Die Datei ist ein Zwischenergebnis und wird "
            "nicht versioniert — bitte zuerst Schritt 01 ausführen:\n"
            "  uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py")

    ZIEL.mkdir(parents=True, exist_ok=True)
    alle = json.loads(quelle.read_text(encoding="utf-8"))
    sitzungen = sorted((s for s in alle if s["start"][:10] <= args.stichtag),
                       key=lambda s: s["start"])
    punkte = json.loads((DATEN / "topmap.json").read_text(encoding="utf-8"))
    titel_je_vorlage = {p["vorlage"]: p["titel"] for p in punkte if p["vorlage"]}

    # --- Sitzungen ---------------------------------------------------------
    zeilen = [{
        "datum": s["start"][:10],
        "uhrzeit": s["start"][11:16],
        "kalenderwoche": dt.date.fromisoformat(s["start"][:10]).isocalendar()[1],
        "gremium": gremium(s["titel"]),
        "sitzungsnummer": (re.search(r"(\d+)\. Sitzung", s["titel"]) or [None, ""])[1]
                          if re.search(r"(\d+)\. Sitzung", s["titel"]) else "",
        "tagesordnungspunkte": s["n_tops"],
        "protokoll_veroeffentlicht": "ja" if s["protokolle"] else "nein",
        "dokumente": s["n_pdf"],
    } for s in sitzungen]
    schreiben(ZIEL / "sitzungen.csv", list(zeilen[0]), zeilen)

    # --- Tagesordnungspunkte ----------------------------------------------
    bis = args.stichtag
    zeilen = [{
        "datum": p["datum"],
        "gremium": p["gremium"],
        "nummer": p["top"],
        "titel": p["titel"],
        "vorlage": p["vorlage"] or "",
    } for p in sorted((p for p in punkte if p["datum"] <= bis),
                      key=lambda p: (p["datum"], int(p["top"]) if p["top"].isdigit() else 0))]
    schreiben(ZIEL / "tagesordnungspunkte.csv", list(zeilen[0]), zeilen)

    # --- Beschlüsse --------------------------------------------------------
    protokolle: dict[str, list[Path]] = {}
    for pdf in sorted((DATEN / "protokolle").glob("*.pdf")):
        protokolle.setdefault(pdf.name[:10], []).append(pdf)

    zeilen = []
    for s in sitzungen:
        if not s["protokolle"]:
            continue
        # Alle Protokolldateien einer Sitzung auswerten: Gelegentlich liegt der
        # Beschlusstext nicht in der ersten Datei, sondern in einer zweiten.
        erwartet = f"{s['start'][:10]}_{dateiname(s['titel'])}"
        for pfad in protokolle.get(s["start"][:10], []):
            if pfad.stem != erwartet and not pfad.stem.startswith(erwartet + "_"):
                continue
            text = pdf_text(pfad)
            for treffer in ERGEBNIS.finditer(text):
                roh = treffer.group(1)
                zahlen = AUSZAEHLUNG.match(roh)
                einstimmig = bool(re.match(r"\s*[Ee]instimmig", roh))
                if not (zahlen or einstimmig):
                    continue
                vorher = VORLAGE.findall(text[:treffer.start()])
                vorlage = vorher[-1] if vorher else ""
                ja, nein, enth = zahlen.groups() if zahlen else ("", "", "")
                zeilen.append({
                    "datum": s["start"][:10],
                    "gremium": gremium(s["titel"]),
                    "vorlage": vorlage,
                    "titel": titel_je_vorlage.get(vorlage, ""),
                    "ergebnis": "einstimmig" if einstimmig else "ausgezählt",
                    "ja": ja,
                    "nein": nein,
                    "enthaltungen": enth,
                    "einstimmig": "ja" if einstimmig or (zahlen and not int(nein) and not int(enth))
                                  else "nein",
                })
    schreiben(ZIEL / "beschluesse.csv", list(zeilen[0]), zeilen)

    # --- Gegenprobe --------------------------------------------------------
    kennzahlen = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))
    a = kennzahlen["abstimmungen"]
    strittig = sum(1 for z in zeilen if z["einstimmig"] == "nein")
    print("\nGegenprobe gegen data/kennzahlen.json:")
    for was, tabelle, soll in [
        ("Sitzungen", len(sitzungen), kennzahlen["sitzungen"]),
        ("Abstimmungen", len(zeilen), a["gesamt"]),
        ("nicht einstimmig", strittig, a["nicht_einstimmig"]),
    ]:
        print(f"  {was:18s} Tabelle {tabelle:4d}  Kennzahlen {soll:4d}  "
              f"{'stimmt überein' if tabelle == soll else 'ABWEICHUNG'}")


if __name__ == "__main__":
    main()
