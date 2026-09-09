#!/usr/bin/env python3
"""Schritt 5 — die wöchentliche „Waldseer Aktenlage“ erzeugen.

Für jede Kalenderwoche, in der mindestens eine Sitzung stattgefunden hat, entsteht
eine Ausgabe. Wochen ohne Sitzung bekommen keine — eine Zeitung über nichts zu
erfinden wäre unredlich.

Inhalt je Ausgabe:
  * die gefassten Beschlüsse mit Vorlagennummer und Stimmenverhältnis
  * Bekanntgaben aus nichtöffentlicher Sitzung, soweit protokolliert
  * Sitzungen ohne Protokoll („Blinder Fleck“)
  * Vorschau auf die nächste öffentliche Sitzung

Ergebnis: docs/ausgaben/amannlabs-aktenlage-bad-waldsee-JJJJ-kwNN.html
          docs/ausgaben/index.html (Archivübersicht)

    uv run --with pypdf python scripts/05_ausgaben_bauen.py --jahr 2026 --bis 2026-09-09
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
ZIEL = WURZEL / "docs" / "ausgaben"

ERGEBNIS = re.compile(r"Ergebnis der Beschlussfassung\s*:?\s*(.{0,70})")
VORLAGE = re.compile(r"SV-\d+/\d{4}")
AUSZAEHLUNG = re.compile(
    r"\s*Ja-Stimme?n?\(?e?n?\)?\s*(\d+)\s*Nein-Stimme?n?\(?e?n?\)?\s*(\d+)\s*"
    r"Enthaltung(?:en|\(en\))?\s*(\d+)")

KURZ = {
    "Gemeinderat": "GR",
    "Verwaltungsausschuss": "VA",
    "Ausschuss für Umwelt, Technik und Nachhaltigkeit": "AUT",
    "Ausschuss für Umwelt und Technik": "AUT",
    "Gemeinsamer Ausschuss der Vereinbarten Verwaltungsgemeinschaft "
    "Bad Waldsee-Bergatreute": "GA",
}

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


# --------------------------------------------------------------------- Daten

def gremium(titel: str) -> str:
    return re.sub(r",.*", "", titel)


def kuerzel(name: str) -> str:
    return KURZ.get(name, "OR" if name.startswith("Ortschaftsrat") else "—")


def dateiname(titel: str) -> str:
    """Muss exakt der Benennung aus 02_protokolle_laden.py entsprechen."""
    name = re.sub(r",.*", "", titel)
    name = re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", "-", name).strip("-")
    return name[:48]


def pdf_text(pfad: Path) -> str:
    try:
        roh = "\n".join(s.extract_text() or "" for s in PdfReader(pfad).pages)
    except Exception:  # noqa: BLE001
        return ""
    return re.sub(r"[­\s]+", " ", roh)


def ergebnis_lesen(roh: str) -> tuple[str | None, bool]:
    z = AUSZAEHLUNG.match(roh)
    if z:
        ja, nein, enth = z.groups()
        return f"{ja} : {nein} : {enth}", bool(int(nein) or int(enth))
    if re.match(r"\s*[Ee]instimmig", roh):
        return "Einstimmig", False
    return None, False


def beschluesse_lesen(text: str) -> list[dict]:
    """Jede Abstimmung der zuletzt davor genannten Vorlagennummer zuordnen."""
    ergebnisse = []
    for treffer in ERGEBNIS.finditer(text):
        wert, strittig = ergebnis_lesen(treffer.group(1))
        if not wert:
            continue
        vorher = VORLAGE.findall(text[:treffer.start()])
        ergebnisse.append({
            "vorlage": vorher[-1] if vorher else None,
            "ergebnis": wert,
            "strittig": strittig,
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


# ------------------------------------------------------------------ Sammeln

def wochen_sammeln(jahr: int, bis: str) -> dict[int, dict]:
    sitzungen = json.loads((DATEN / "sitzungen.json").read_text(encoding="utf-8"))
    punkte = json.loads((DATEN / "topmap.json").read_text(encoding="utf-8"))
    titel_je_vorlage = {p["vorlage"]: p["titel"] for p in punkte if p["vorlage"]}

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
        erwartet = f"{s['start'][:10]}_{dateiname(s['titel'])}"
        for pfad in protokolle.get(s["start"][:10], []):
            if pfad.stem != erwartet and not pfad.stem.startswith(erwartet + "_"):
                continue
            text = pdf_text(pfad)
            for b in beschluesse_lesen(text):
                b["titel"] = titel_je_vorlage.get(b["vorlage"], None)
                b["gremium"] = name
                b["kuerzel"] = kuerzel(name)
                b["datum"] = tag
                if b["titel"]:
                    w["beschluesse"].append(b)
            bg = bekanntgaben_lesen(text)
            if bg:
                w["bekanntgaben"].append({"datum": tag, "gremium": name, "text": bg})
            break

    # Vorschau: naechste Sitzung nach dem Ende der jeweiligen Woche
    for kw, w in wochen.items():
        ende = dt.date.fromisocalendar(jahr, kw, 7)
        spaeter = [s for s in alle if dt.date.fromisoformat(s["start"][:10]) > ende]
        w["naechste"] = spaeter[0] if spaeter else None
        w["kuenftig"] = kuenftig
    return dict(sorted(wochen.items()))


# ------------------------------------------------------------------ Rendern

def e(t: str) -> str:
    return html.escape(t, quote=False)


def kopf(titel: str) -> str:
    stil = (WURZEL / "scripts" / "ausgabe.css").read_text(encoding="utf-8")
    return f"""<meta charset="utf-8">
<title>{e(titel)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&amp;family=IBM+Plex+Mono:wght@400;500;600&amp;family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;1,400&amp;display=swap">
<style>{stil}</style>
<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <span>Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>
"""


def fuss(zusatz: str = "") -> str:
    return f"""
<footer><div class="wrap">
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
  <p>Alle Angaben und Insights ohne Gew&auml;hr{zusatz}</p>
</div></footer>
"""


DISCLAIMER = """
  <div class="kasten warn">
    <p class="lab">Lernprojekt &middot; keine Gew&auml;hr &middot; keine Vorw&uuml;rfe</p>
    <p><b>Diese Publikation ist ein privates Lern- und Technikprojekt</b> zur automatisierten
    Auswertung &ouml;ffentlich zug&auml;nglicher Verwaltungsdokumente. Sie ist kein
    journalistisches Erzeugnis, kein Pr&uuml;fbericht und keine rechtliche oder fachliche
    Bewertung.</p>
    <p><b>F&uuml;r Richtigkeit, Vollst&auml;ndigkeit und Aktualit&auml;t wird keine Gew&auml;hr
    &uuml;bernommen.</b> Alle Angaben beruhen auf maschineller Verarbeitung von PDF-Dokumenten;
    Fehler bei Texterkennung und Zuordnung sind m&ouml;glich. Verbindlich ist ausschlie&szlig;lich
    das jeweilige Originaldokument der Stadt Bad Waldsee.</p>
    <p><b>Es werden keine Vorw&uuml;rfe erhoben.</b> Weder der Stadtverwaltung noch einzelnen
    Personen wird rechtswidriges oder schuldhaftes Verhalten unterstellt. Namen von
    Privatpersonen werden nicht wiedergegeben. Korrekturen sind erw&uuml;nscht und werden
    zeitnah eingearbeitet. Es besteht keine Verbindung zur Stadt Bad Waldsee.</p>
  </div>
"""


def ausgabe_bauen(jahr: int, kw: int, w: dict) -> str:
    mo = dt.date.fromisocalendar(jahr, kw, 1)
    so = dt.date.fromisocalendar(jahr, kw, 7)
    n_besch = len(w["beschluesse"])
    n_strittig = sum(1 for b in w["beschluesse"] if b["strittig"])
    mit_prot = sum(1 for s in w["sitzungen"] if s["protokoll"])

    t = [kopf(f"Aktenlage KW {kw}/{jahr}"), '<div class="wrap">']
    t.append(f"""
<header class="masthead">
  <h1>Waldseer Aktenlage</h1>
  <p class="claim">Was der Gemeinderat und seine Ausschüsse entschieden haben —
  gelesen aus den Originalunterlagen.</p>
  <div class="issueline">
    <span><b>Ausgabe</b> KW {kw} / {jahr}</span>
    <span><b>Berichtswoche</b> {mo.strftime('%d.%m.')}–{so.strftime('%d.%m.%Y')}</span>
    <span><b>Sitzungen</b> {len(w['sitzungen'])} · {mit_prot} protokolliert</span>
    <span><b>Beschlüsse</b> {n_besch}</span>
  </div>
</header>""")

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
                t.append(f"""      <li><span class="sache">{e(b['titel'])}"""
                         f"""<span class="sv">{e(b['vorlage'] or '—')}</span></span>"""
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
    <h2 class="headline">{len(w['blind'])} öffentliche {'Sitzung' if len(w['blind']) == 1 else 'Sitzungen'} ohne Überlieferung</h2>
    <p>In dieser Woche tagten folgende Gremien öffentlich, ohne dass ein Protokoll
    veröffentlicht wurde:</p>
    <ul class="beschluesse">
{zeilen}    </ul>
    <div class="kasten warn">
      <p class="lab">Wiederkehrende Rubrik</p>
      <p>Im gesamten ausgewerteten Zeitraum seit Januar 2024 haben die vier Ortschaftsräte
      <b>85 Mal öffentlich getagt und kein einziges Protokoll veröffentlicht</b> — rund die
      Hälfte aller öffentlichen Sitzungen der Stadt. Ihre Sitzungsseiten im
      Ratsinformationssystem enthalten nur Datum und Ort.</p>
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
  <h3>Wie diese Ausgabe entsteht</h3>
  <p>Diese Ausgabe wurde maschinell aus den Beschlussprotokollen und Tagesordnungen des
  <a class="doc" href="https://ris.bad-waldsee.de/" rel="noopener">Ratsinformationssystems
  der Stadt Bad Waldsee</a> erzeugt. Beschlusstitel stammen aus der Tagesordnung,
  Abstimmungsergebnisse wörtlich aus der Zeile „Ergebnis der Beschlussfassung“ des
  Protokolls. Die Schreibweise <span class="mono">25 : 0 : 1</span> steht für
  Ja : Nein : Enthaltungen.</p>
  <p>Jeder Beschluss nennt seine Vorlagennummer (<span class="mono">SV-000/JJJJ</span>);
  damit ist der Vorgang im Ratsinformationssystem unter „Vorlagen“ auffindbar. Auf feste
  Direktlinks wird verzichtet, weil die Dokument-URLs sitzungsgebundene Token enthalten
  und nicht dauerhaft gültig bleiben.</p>
  <p class="note">Beschlussprotokolle halten keine Aussprache fest: <em>wie</em> abgestimmt
  wurde, ist nachlesbar, <em>warum</em> nicht. Nichtöffentliche Sitzungsteile sind
  vollständig unsichtbar.</p>
{DISCLAIMER}
  <p class="note"><a class="doc" href="./index.html">Alle Ausgaben im Archiv</a></p>
</section>
</div>""")
    t.append(fuss(f" &middot; Ausgabe KW {kw}/{jahr} &middot; erzeugt am "
                  f"{dt.date.today().strftime('%d.%m.%Y')}"))
    return "\n".join(t)


def archiv_bauen(jahr: int, wochen: dict[int, dict]) -> str:
    t = [kopf(f"Aktenlage — Archiv {jahr}"), '<div class="wrap">']
    ges_b = sum(len(w["beschluesse"]) for w in wochen.values())
    ges_s = sum(len(w["sitzungen"]) for w in wochen.values())
    t.append(f"""
<header class="masthead">
  <h1>Aktenlage &middot; Archiv</h1>
  <p class="claim">Alle bisher erschienenen Ausgaben der Waldseer Aktenlage.</p>
  <div class="issueline">
    <span><b>Jahrgang</b> {jahr}</span>
    <span><b>Ausgaben</b> {len(wochen)}</span>
    <span><b>Sitzungen</b> {ges_s}</span>
    <span><b>Beschlüsse</b> {ges_b}</span>
  </div>
</header>
<section class="kolophon">
  <p class="rubrik">Ausgaben</p>
  <h3>Jahrgang {jahr}</h3>
  <p>Es erscheint eine Ausgabe für jede Kalenderwoche, in der mindestens eine Sitzung
  stattgefunden hat. Wochen ohne Sitzung bekommen keine Ausgabe.</p>
  <ul class="beschluesse">""")
    for kw in sorted(wochen, reverse=True):
        w = wochen[kw]
        mo = dt.date.fromisocalendar(jahr, kw, 1)
        so = dt.date.fromisocalendar(jahr, kw, 7)
        nb, nbl = len(w["beschluesse"]), len(w["blind"])
        teile = []
        if nb:
            teile.append(f"{nb} {'Beschluss' if nb == 1 else 'Beschlüsse'}")
        if nbl:
            teile.append(f"{nbl} ohne Protokoll")
        t.append(f"""    <li><span class="sache"><a class="doc" href="./amannlabs-aktenlage-bad-waldsee-{jahr}-kw{kw:02d}.html">KW {kw} / {jahr}</a>
      <span class="sv">{mo.strftime('%d.%m.')}–{so.strftime('%d.%m.%Y')} &middot; {', '.join(g['kuerzel'] for g in w['sitzungen'])}</span></span>
      <span class="erg">{' · '.join(teile) or 'ohne Beschluss'}</span></li>""")
    t.append(f"""  </ul>
{DISCLAIMER}
</section>
</div>""")
    t.append(fuss(f" &middot; Archiv {jahr}"))
    return "\n".join(t)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jahr", type=int, default=2026)
    p.add_argument("--bis", default="2026-09-09")
    args = p.parse_args()

    ZIEL.mkdir(parents=True, exist_ok=True)
    wochen = wochen_sammeln(args.jahr, args.bis)

    for kw, w in wochen.items():
        datei = ZIEL / f"amannlabs-aktenlage-bad-waldsee-{args.jahr}-kw{kw:02d}.html"
        datei.write_text(ausgabe_bauen(args.jahr, kw, w), encoding="utf-8")
        print(f"  KW {kw:2d}  {len(w['sitzungen'])} Sitzung(en), "
              f"{len(w['beschluesse'])} Beschlüsse, {len(w['blind'])} ohne Protokoll")

    (ZIEL / "index.html").write_text(archiv_bauen(args.jahr, wochen), encoding="utf-8")
    print(f"\n{len(wochen)} Ausgaben und ein Archiv in docs/ausgaben/")


if __name__ == "__main__":
    main()
