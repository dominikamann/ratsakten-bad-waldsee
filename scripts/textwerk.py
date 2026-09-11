"""Gemeinsame Textreparatur fuer die Protokolltexte.

Die Protokoll-PDFs trennen Woerter am Zeilenende. Beim Auslesen bleibt davon
ein Bindestrich mit Leerzeichen zurueck — mal ohne Leerzeichen davor
(„Ände- rung"), mal mit („Mi - chelwinnaden"). Beide Formen muessen
zusammengefuehrt werden.

Die Schwierigkeit ist, dass derselbe Bindestrich auch als Gedankenstrich
vorkommt. „Schuetzenstrasse 27 - ausserplanmaessige Ausgaben" ist ein
Tagesordnungstitel und darf nicht zu „27ausserplanmaessige" werden; dieser
Titel steht woertlich in einem der Befunde.

Unterschieden wird deshalb am Wortschatz des Bestands: Eine echte Trennung
ergibt zusammengefuegt ein Wort, das anderswo in den Protokollen vorkommt.
Ein Gedankenstrich verbindet zwei Woerter, die jedes fuer sich bestehen.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

# Linke Haelfte moeglichst kurz fassen, damit „zu be- antragen" an „be"
# ansetzt und nicht an „zu be".
TRENNSTELLE = re.compile(r"(\w+?)\s*-\s+([a-zäöüß]\w*)")
_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")


def wortschatz_aus(text: str, zaehler: collections.Counter) -> None:
    """Woerter eines Textes aufnehmen — ohne die Bruchstuecke selbst.

    Wuerde man sie mitzaehlen, gaelte „chelwinnaden" als bekanntes Wort und
    die Pruefung liefe leer.
    """
    for w in _WORT.findall(TRENNSTELLE.sub(" ", text)):
        zaehler[w.lower()] += 1


def wortschatz_speichern(zaehler: collections.Counter, ziel: Path) -> None:
    ziel.write_text(
        json.dumps(sorted(zaehler), ensure_ascii=False), encoding="utf-8")


def wortschatz_laden(quelle: Path) -> set[str]:
    if not quelle.exists():
        return set()
    return set(json.loads(quelle.read_text(encoding="utf-8")))


def trennung_reparieren(text: str, wortschatz: set[str]) -> str:
    """Silbentrennungen zusammenfuehren, Gedankenstriche stehen lassen.

    Ohne Wortschatz bleibt der Text unveraendert — lieber ein sichtbarer
    Trennstrich als ein verfaelschter Titel.
    """
    if not wortschatz:
        return text

    def entscheiden(m: re.Match[str]) -> str:
        links, rechts = m.group(1), m.group(2)
        if (links + rechts).lower() in wortschatz:
            return links + rechts          # ergibt ein bekanntes Wort
        if not links.isalpha():
            return m.group(0)              # Hausnummern, Betraege: nie
        if rechts.lower() not in wortschatz:
            return links + rechts          # rechte Haelfte ist kein Wort
        return m.group(0)

    return TRENNSTELLE.sub(entscheiden, text)


# --- Auslesen mit Zwischenspeicher ------------------------------------------
# Vier Schritte lesen dieselben Protokolle: Kennzahlen, Ausgaben, Tabellen und
# Suche. Das Auslesen eines PDF kostet ein Vielfaches des Einlesens einer
# Textdatei; ein vollstaendiger Neubau lief deshalb rund zehn Minuten. Der
# Zwischenspeicher haelt den geglaetteten Rohtext — ohne Trennungsreparatur,
# weil der Wortschatz erst in Schritt 03 entsteht.

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"


def _schluessel(pfad: Path) -> str:
    st = pfad.stat()
    roh = f"{pfad.name}|{st.st_size}|{st.st_mtime_ns}"
    return hashlib.sha1(roh.encode("utf-8")).hexdigest()[:20]


def pdf_text(pfad: Path) -> str:
    """Geglaetteter Rohtext eines PDF, ueber Laeufe hinweg zwischengespeichert.

    Der Schluessel enthaelt Groesse und Aenderungszeit: Wird ein Protokoll
    ersetzt, entsteht ein neuer Eintrag, der alte wird nie wieder gelesen.
    """
    ziel = CACHE / f"{_schluessel(pfad)}.txt"
    if ziel.exists():
        return ziel.read_text(encoding="utf-8")
    try:
        roh = "\n".join(s.extract_text() or "" for s in PdfReader(pfad).pages)
    except Exception:  # noqa: BLE001
        return ""
    text = re.sub(r"[­\s]+", " ", roh)
    CACHE.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return text
