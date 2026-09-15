"""Gemeinsame Textreparatur fuer die Protokolltexte.

Die Protokoll-PDFs trennen Woerter am Zeilenende. Beim Auslesen bleibt davon
ein Bindestrich mit Leerzeichen zurueck — mal ohne Leerzeichen davor
(„Ände- rung"), mal mit („Mi - chelwinnaden"). Beide Formen muessen
zusammengefuehrt werden.

Die Schwierigkeit ist, dass derselbe Bindestrich auch als Gedankenstrich
vorkommt. „Schuetzenstrasse 27 - ausserplanmaessige Ausgaben" ist ein
Tagesordnungstitel und darf nicht zu „27ausserplanmaessige" werden; dieser
Titel steht woertlich in einer der Erkenntnisse.

Unterschieden wird deshalb am Wortschatz des Bestands: Eine echte Trennung
ergibt zusammengefuegt ein Wort, das anderswo in den Protokollen vorkommt.
Ein Gedankenstrich verbindet zwei Woerter, die jedes fuer sich bestehen.
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

# Linke Haelfte moeglichst kurz fassen, damit „zu be- antragen" an „be"
# ansetzt und nicht an „zu be".
TRENNSTELLE = re.compile(r"(\w+?)\s*-\s+([a-zäöüß]\w*)")
_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")
_WORT_POS = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def wortschatz_aus(text: str, zaehler: collections.Counter) -> None:
    """Woerter eines Textes aufnehmen — ohne die Bruchstuecke selbst.

    Wuerde man sie mitzaehlen, gaelte „chelwinnaden" als bekanntes Wort und
    die Pruefung liefe leer.
    """
    for w in _WORT.findall(TRENNSTELLE.sub(" ", text)):
        zaehler[w.lower()] += 1


def wortschatz_speichern(zaehler: collections.Counter, ziel: Path) -> None:
    """Woerter mit ihrer Haeufigkeit ablegen.

    Frueher nur die Liste. Damit liess sich nicht unterscheiden, ob ein Wort
    ein echtes Wort ist oder ein Bruchstueck, das oft genug vorkam, um in die
    Liste zu geraten: „bauvorschrif" stand darin wie „bauvorschriften". Fuer
    die Reparatur von Trennungen **ohne** Bindestrich braucht es diesen
    Unterschied — und der steckt in der Haeufigkeit.
    """
    ziel.write_text(
        json.dumps(dict(sorted(zaehler.items())), ensure_ascii=False),
        encoding="utf-8")


def wortschatz_laden(quelle: Path) -> set[str]:
    """Nur die Woerter. Liest beide Formate — Liste wie Haeufigkeitstabelle."""
    return set(haeufigkeiten_laden(quelle))


def haeufigkeiten_laden(quelle: Path) -> dict[str, int]:
    """Wort → Anzahl. Aus einer alten Liste wird jedes Wort einmal gezaehlt."""
    if not quelle.exists():
        return {}
    roh = json.loads(quelle.read_text(encoding="utf-8"))
    return roh if isinstance(roh, dict) else {w: 1 for w in roh}


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


# Trennung ohne Bindestrich: Beim Auslesen mancher PDF geht der Trennstrich
# verloren und zurueck bleibt ein Leerzeichen mitten im Wort —
# „Bauvorschrif ten", „Planunter lagen", „bekanntzuma chen". Der Leser sieht
# ein zerrissenes Wort mitten im Beschlusswortlaut.
#
# Rechts steht dabei immer ein kleingeschriebenes Bruchstueck. Die linke
# Haelfte darf mit einem Grossbuchstaben beginnen.
LEERSTELLE = re.compile(r"\b([A-Za-zÄÖÜäöüß]{4,})\s+([a-zäöüß]{2,10})\b")

# Ab welchem Verhaeltnis ein Wortteil als Bruchstueck gilt: Das
# zusammengesetzte Wort muss mindestens dreimal so haeufig vorkommen wie die
# linke Haelfte allein, und die linke Haelfte darf selbst kaum auftreten.
# „bauvorschrif" steht einmal im Bestand, „bauvorschriften" 101 Mal — das ist
# eindeutig. „Bad Waldsee" bleibt unangetastet: „badwaldsee" gibt es nicht.
# Dass ein Bruchstueck selbst mehrfach vorkommt, ist der Normalfall: Es
# entsteht ja jedes Mal neu, wenn dasselbe Wort am Zeilenende getrennt wird.
# „vereinbar" steht sechsmal im Bestand, „vereinbarten" 111 Mal — Aussagekraft
# hat das Verhaeltnis, nicht die absolute Zahl.
BRUCHSTUECK_HOECHSTENS = 8
VERHAELTNIS = 4


def leertrennung_reparieren(text: str, haeufig: dict[str, int]) -> str:
    """Zerrissene Woerter zusammenfuehren — nur bei klarer Datenlage.

    Ohne Haeufigkeiten bleibt der Text unveraendert. Lieber ein sichtbar
    zerrissenes Wort als ein verfaelschter Beschlusswortlaut: Der Text ist
    Zitat, und ein falsch zusammengezogenes Wort waere eine Aenderung am
    Zitat, die niemand bemerkt.

    Geprueft wird Paar fuer Paar und nicht mit `re.sub`. Das ersetzt ohne
    Ueberlappung und haette in „Wohnbaeflaeche entspre chend" zuerst
    („Wohnbaeflaeche", „entspre") betrachtet, verworfen — und „chend" waere
    damit verbraucht gewesen, ehe das richtige Paar an der Reihe war. Nach
    einem Verzicht rueckt die Suche deshalb nur um ein Wort vor.
    """
    if not haeufig:
        return text

    woerter = list(_WORT_POS.finditer(text))
    teile: list[str] = []
    zuletzt = 0
    i = 0
    while i < len(woerter) - 1:
        links, rechts = woerter[i], woerter[i + 1]
        # Nur ein einzelnes Leerzeichen dazwischen, nichts sonst.
        if text[links.end():rechts.start()] != " ":
            i += 1
            continue
        a, b = links.group(), rechts.group()
        zusammen = (a + b).lower()
        n_zus = haeufig.get(zusammen, 0)
        n_links = haeufig.get(a.lower(), 0)
        passt = (len(a) >= 4 and 2 <= len(b) <= 10 and b[0].islower()
                 and n_zus and n_links <= BRUCHSTUECK_HOECHSTENS
                 and n_zus >= max(VERHAELTNIS, n_links * VERHAELTNIS))
        if passt:
            teile.append(text[zuletzt:links.start()])
            teile.append(a + b)
            zuletzt = rechts.end()
            i += 2                       # beide Haelften sind verbraucht
        else:
            i += 1                       # nur um ein Wort weiter
    teile.append(text[zuletzt:])
    return "".join(teile)


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

# ---------- Schwaerzung ----------

SCHWAERZUNG = Path(__file__).resolve().parent.parent / "data" / "schwaerzung.json"


def _ersetzungen() -> list[tuple[str, str]]:
    if not SCHWAERZUNG.exists():
        return []
    daten = json.loads(SCHWAERZUNG.read_text(encoding="utf-8"))
    return [(a, b) for a, b in daten.get("ersetzungen", [])]


def schwaerzen(text: str) -> str:
    """Namen von Privatpersonen aus einem Beschlusswortlaut entfernen.

    Beschluesse sind oeffentlich, und die Stadt nennt darin gelegentlich
    Privatpersonen — etwa die Spenderin einer Geldspende, deren Annahme der
    Gemeinderat beschliessen muss. Dass eine Angabe oeffentlich ist, heisst
    nicht, dass dieses Projekt sie zusaetzlich verbreiten muss: Hier entstuende
    aus einer Zeile im Protokoll ein durchsuchbarer Eintrag mit Namen und
    Wohnort.

    Amtstraeger sind ausdruecklich nicht gemeint. Abteilungskommandanten der
    Feuerwehr, Ortsvorsteher und Fachbereichsleitungen werden in oeffentlicher
    Sitzung gewaehlt; ihre Namen gehoeren zum Vorgang.

    Die Liste steht in `data/schwaerzung.json` und ist bewusst woertlich statt
    mustergestuetzt — eine Namenserkennung, die raet, wuerde entweder Aemter
    mitschwaerzen oder Privatpersonen uebersehen.
    """
    for alt, neu in _ersetzungen():
        text = text.replace(alt, neu)
    return text


# --- Stichtag ----------------------------------------------------------------

SITZUNGEN = Path(__file__).resolve().parent.parent / "data" / "sitzungen.json"


def stichtag_vorgabe() -> str:
    """Letzter Tag, an dem jede Sitzung dieses Tages bereits begonnen hat.

    Der Vergleich lief frueher nur ueber das Datum. Eine Sitzung, die am
    Lauftag erst am Abend beginnt, galt damit schon nachmittags als
    stattgefunden — und die Wochenausgabe wies sie als „tagte oeffentlich,
    keine Niederschrift abrufbar" aus, bevor sie ueberhaupt getagt hatte.
    Das ist die Fehlerklasse, die dieses Projekt vermeiden muss: eine
    Abwesenheit behaupten, die noch gar nicht eintreten konnte.

    Steht heute noch eine Sitzung aus, endet die Auswertung deshalb am
    Vortag. Ein ausdruecklich gesetzter --stichtag bleibt unberuehrt.
    """
    jetzt = dt.datetime.now()
    heute = jetzt.date()
    try:
        sitzungen = json.loads(SITZUNGEN.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return heute.isoformat()

    noch_offen = any(
        s["start"][:10] == heute.isoformat() and s["start"] > jetzt.isoformat()
        for s in sitzungen
    )
    return (heute - dt.timedelta(days=1)).isoformat() if noch_offen else heute.isoformat()
