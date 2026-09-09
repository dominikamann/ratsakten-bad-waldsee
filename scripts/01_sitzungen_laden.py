#!/usr/bin/env python3
"""Schritt 1 — Sitzungen und Tagesordnungen aus dem Ratsinformationssystem laden.

Der Sitzungskalender wird per JavaScript nachgeladen; dahinter liegt ein
JSON-Endpunkt, der ein Sitzungs-Cookie und ein CSRF-Token verlangt. Beides
holen wir uns, indem wir zuerst die Kalenderseite ganz normal aufrufen.

Ergebnis: data/sitzungen.json und data/topmap.json

    uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASIS = "https://ris.bad-waldsee.de"
VON, BIS = "2024-01-01", "2026-12-31"
PAUSE = 0.25  # Sekunden zwischen Abrufen — die Server der Stadt sollen nicht leiden
DATEN = Path(__file__).resolve().parent.parent / "data"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def sitzung_starten() -> tuple[requests.Session, str]:
    """Session aufbauen und das CSRF-Token aus der Kalenderseite ziehen."""
    s = requests.Session()
    s.headers["User-Agent"] = UA
    html = s.get(f"{BASIS}/termine", timeout=30).text
    treffer = (re.search(r"X-CSRF-Token'\s*:\s*'([0-9a-f]{32,})'", html)
               or re.search(r"csrfToken'\s*,\s*'([0-9a-f]{32,})'", html))
    if not treffer:
        sys.exit("CSRF-Token nicht gefunden — hat sich das Ratsinfosystem geändert?")
    return s, treffer.group(1)


def termine_holen(s: requests.Session, token: str) -> list[dict]:
    antwort = s.get(
        f"{BASIS}/termine/json/Sitzungstermine/",
        params={"start": VON, "end": BIS},
        headers={"X-CSRF-Token": token, "X-Requested-With": "XMLHttpRequest"},
        timeout=30,
    )
    antwort.raise_for_status()
    return antwort.json().get("events", [])


def sitzung_auslesen(s: requests.Session, termin: dict) -> tuple[dict, list[dict]]:
    """Eine Sitzungsseite parsen: Tagesordnung, Vorlagen, Dokumente, Protokoll."""
    soup = BeautifulSoup(s.get(termin["url"], timeout=30).text, "html.parser")
    text = soup.get_text(" ", strip=True)

    pdfs = sorted({a["href"] for a in soup.find_all("a", href=True)
                   if "/sdnetrim/" in a["href"]})
    protokolle = [u for u in pdfs if re.search(r"protokoll|niederschrift", u, re.I)]

    tops, punkte = [], []
    for zeile in soup.select("tr"):
        zellen = zeile.find_all(["td", "th"])
        if len(zellen) < 2:
            continue
        nummer = zellen[0].get_text(strip=True)
        if not re.fullmatch(r"\d+", nummer):
            continue
        titel = zellen[1].get_text(" ", strip=True)
        tops.append(titel)
        vorlage = re.search(r"SV-\d+/\d{4}", zeile.get_text(" ", strip=True))
        punkte.append({
            "datum": termin["start"][:10],
            "gremium": re.sub(r",.*", "", termin["title"]),
            "top": nummer,
            "titel": titel,
            "vorlage": vorlage.group(0) if vorlage else None,
            "url": termin["url"],
        })

    sitzung = {
        "titel": termin["title"],
        "start": termin["start"],
        "url": termin["url"],
        "n_tops": len(tops),
        "tops": tops,
        "vorlagen": sorted(set(re.findall(r"SV-\d+/\d{4}", text))),
        "n_pdf": len(pdfs),
        "protokolle": protokolle,
        "pdfs": pdfs,
    }
    return sitzung, punkte


def main() -> None:
    DATEN.mkdir(exist_ok=True)
    s, token = sitzung_starten()
    print(f"CSRF-Token: {token[:12]}…", file=sys.stderr)

    termine = [t for t in termine_holen(s, token) if t.get("url")]
    print(f"{len(termine)} Sitzungstermine mit Detailseite gefunden", file=sys.stderr)

    sitzungen, topmap = [], []
    for i, termin in enumerate(termine, 1):
        try:
            sitzung, punkte = sitzung_auslesen(s, termin)
        except Exception as fehler:  # noqa: BLE001 — einzelne Ausfälle nicht fatal
            print(f"  Fehler bei {termin['title']}: {fehler}", file=sys.stderr)
            continue
        sitzungen.append(sitzung)
        topmap.extend(punkte)
        if i % 25 == 0:
            print(f"  {i}/{len(termine)} …", file=sys.stderr)
        time.sleep(PAUSE)

    (DATEN / "sitzungen.json").write_text(
        json.dumps(sitzungen, ensure_ascii=False, indent=1), encoding="utf-8")
    (DATEN / "topmap.json").write_text(
        json.dumps(topmap, ensure_ascii=False, indent=1), encoding="utf-8")

    mit_vorlage = sum(1 for p in topmap if p["vorlage"])
    print(f"\nGespeichert: {len(sitzungen)} Sitzungen, {len(topmap)} Tagesordnungspunkte "
          f"({mit_vorlage} mit Vorlagennummer)", file=sys.stderr)


if __name__ == "__main__":
    main()
