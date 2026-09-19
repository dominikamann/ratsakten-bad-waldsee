#!/usr/bin/env python3
"""Schritt 6 — die Startseite aus den Daten erzeugen.

Bis hierher war die Startseite handgepflegt: Kennzahlen, der Link auf die neueste
Ausgabe und die Zahl der Ausgaben standen als fester Text darin. Das veraltet
wöchentlich und fällt niemandem auf, weil die Seite weiter funktioniert — sie
zeigt nur auf die falsche Ausgabe.

Jetzt kommt alles aus den Dateien, die die Verarbeitungskette ohnehin schreibt:
  data/kennzahlen.json   die Kennzahlen (Schritt 3)
  data/ausgaben.json     das Ausgabenregister (Schritt 5)
  docs/report/*.html     der jüngste Report

Ergebnis: docs/index.html

    uv run python scripts/06_startseite_bauen.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

from seite import fuss, kopf, kurz, zahlwort

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


def e(t: str) -> str:
    return html.escape(str(t), quote=False)


def datum_lang(d: dt.date) -> str:
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def juengster_report() -> tuple[str, dt.date] | None:
    """Neueste Datei in docs/report/, benannt nach ihrem Stichtag."""
    kandidaten = sorted((DOCS / "report").glob("*.html")) if (DOCS / "report").exists() else []
    if not kandidaten:
        return None
    neuester = kandidaten[-1]
    try:
        stand = dt.date.fromisoformat(neuester.stem)
    except ValueError:
        stand = dt.date.fromtimestamp(neuester.stat().st_mtime)
    return f"./report/{neuester.name}", stand


def neueste_ausgabe(register: dict) -> tuple[str, int, int, dict] | None:
    if not register:
        return None
    jahr = max(register, key=int)
    if not register[jahr]:
        return None
    kw = max(register[jahr], key=int)
    return f"./ausgaben/{jahr}/kw{int(kw):02d}.html", int(jahr), int(kw), register[jahr][kw]


def bauen() -> str:
    kennzahlen = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))
    register = json.loads((DATEN / "ausgaben.json").read_text(encoding="utf-8"))
    a = kennzahlen["abstimmungen"]
    kacheln = [
        (kennzahlen["sitzungen"], "Sitzungen"),
        (kennzahlen["tagesordnungspunkte"], "Tagesordnungs-<br>punkte"),
        (kennzahlen["vorlagen"], "Vorlagen"),
        (kennzahlen["protokolle"], "Protokolle"),
        (a["gesamt"], "Abstimmungen"),
        (kennzahlen["dokumente"], "Dokumente"),
    ]
    kachel_html = "\n".join(
        f'    <div class="tile"><span class="v">{v}</span><span class="k">{t}</span></div>'
        for v, t in kacheln)

    # (Rang, HTML) — die Reihenfolge folgt dem Leserinteresse, nicht dem Code.
    karten: list[tuple[int, str]] = []

    report = juengster_report()
    if report:
        pfad, stand = report
        karten.append((60, f"""    <a class="karte" href="{pfad}">
      <p class="art">Report &middot; Vollauswertung</p>
      <h3>Ratsanalyse Bad Waldsee</h3>
      <p>Auswertung der gesamten dokumentierten Gremienarbeit: Transparenz, Themen,
      Abstimmungsverhalten, Finanzen — dazu die 50 auff&auml;lligsten Tagesordnungspunkte
      und acht Beobachtungen.</p>
      <p class="meta">Stand {datum_lang(stand)} &middot; 8 Kapitel &middot; 5 Diagramme</p>
    </a>"""))

    # Kennzahlen kommen aus data/suche.json, das Schritt 08 schreibt. Sie aus dem
    # erzeugten HTML zu lesen waere zerbrechlich: Aendert sich dort die Auszeichnung,
    # stuende hier stillschweigend ein Satz ohne Zahlen.
    kennwerte = DATEN / "suche.json"
    if (DOCS / "suche.html").exists() and kennwerte.exists():
        sk = json.loads(kennwerte.read_text(encoding="utf-8"))
        karten.append((40, f"""    <a class="karte" href="./suche.html">
      <p class="art">Vorg&auml;nge &middot; durchsuchbar</p>
      <h3>Was wurde zu einem Thema entschieden?</h3>
      <p>{sk.get('sachvorgaenge', sk['vorgaenge'])} Vorg&auml;nge mit ihrem Weg durch die Gremien — von der ersten
      Beratung bis zum Beschluss, mit Datum, Gremium und Stimmenverh&auml;ltnis.
      {sk['mehrstufig']} davon durchliefen mehrere Stationen.</p>
      <p class="meta">Suche nach Stichwort oder Vorlagennummer</p>
    </a>"""))


    if (DOCS / "gremien.html").exists():
        karten.append((20, """    <a class="karte" href="./gremien.html">
      <p class="art">Grundlagen</p>
      <h3>Wer entscheidet was</h3>
      <p>Gemeinderat, beschlie&szlig;ende Aussch&uuml;sse, Ortschaftsr&auml;te, Gemeinsamer Ausschuss —
      und was die Stadt gar nicht entscheidet. Die Lesehilfe f&uuml;r alles &Uuml;brige.</p>
      <p class="meta">Mit Fundstellen aus Hauptsatzung, Gemeindeordnung und Baugesetzbuch</p>
    </a>"""))

    themenseiten = sorted((DOCS / "themen").glob("*.html")) if (DOCS / "themen").exists() else []
    vorhaben = [p for p in themenseiten if p.name != "index.html"]
    if vorhaben:
        karten.append((30, f"""    <a class="karte" href="./themen/index.html">
      <p class="art">Vorhaben &middot; im Zeitverlauf</p>
      <h3>Was wurde aus …?</h3>
      <p>{len(vorhaben)} Vorhaben mit ihrem vollst&auml;ndigen Verlauf — ein Bauleitplan oder ein
      Ger&auml;tehaus zieht sich &uuml;ber Jahre und durch mehrere Gremien. Die Wochenausgaben
      zeigen davon immer nur einen Ausschnitt.</p>
      <p class="meta">L&auml;ngster Vorgang: 19 Stationen &uuml;ber zwei Jahre</p>
    </a>"""))

    befundseite = DOCS / "befunde.html"
    if befundseite.exists():
        n_bef = befundseite.read_text(encoding="utf-8").count('<article class="befundblock">')
        karten.append((50, f"""    <a class="karte" href="./befunde.html">
      <p class="art">Erkenntnisse &middot; gesammelt</p>
      <h3>Was aufgefallen ist</h3>
      <p>{n_bef} Eintr&auml;ge an einem Ort statt verstreut &uuml;ber Report und Wochenausgaben:
      eingehaltene Fristen und abgeschlossene Verfahren ebenso wie die Stellen,
      an denen die Aktenlage Fragen offenl&auml;sst.</p>
      <p class="meta">Regelbasiert gez&auml;hlt und maschinell gedeutet, jeweils gekennzeichnet</p>
    </a>"""))

    aktuell = neueste_ausgabe(register)
    if aktuell:
        pfad, jahr, kw, meta = aktuell
        n_b = meta["beschluesse"]
        beschreibung = (
            f"{n_b} {'Beschluss' if n_b == 1 else 'Beschl&uuml;sse'} mit Vorlagennummer und "
            f"Stimmenverh&auml;ltnis" if n_b else
            # „abrufbar", nicht „veroeffentlicht": Erhoben ist, was im
            # Ratsinformationssystem steht, nicht was die Stadt getan hat.
            "In diesem Berichtszeitraum ist kein Beschlussprotokoll abrufbar")
        if meta["ohne_protokoll"]:
            beschreibung += (f", dazu {meta['ohne_protokoll']} &ouml;ffentliche "
                             f"{'Sitzung' if meta['ohne_protokoll'] == 1 else 'Sitzungen'} "
                             f"ohne Protokoll")
        # „steht noch aus" ist etwas anderes als „fehlt". Eine Sitzung von
        # vorgestern hat kein Protokoll, weil noch keine Zeit vergangen ist.
        if meta.get("ausstehend"):
            n = meta["ausstehend"]
            beschreibung += (f", dazu {n} {'Sitzung' if n == 1 else 'Sitzungen'}, "
                             f"{'deren Protokoll noch aussteht' if n == 1 else 'deren Protokolle noch ausstehen'}")
        # Die laufende Woche ist ein Zwischenstand. Stand das nur in der
        # Ausgabe selbst, versprach die Startseite mehr, als die Ausgabe haelt:
        # „zuletzt entschieden" klingt abgeschlossen, und „keine Beschluesse"
        # liest sich dann als Befund statt als Stand von Dienstagmittag.
        laufend = meta.get("laufend")
        art = ("Ratswoche &middot; laufende Woche" if laufend
               else "Ratswoche &middot; aktuelle Ausgabe")
        einleitung = ("Was der Gemeinderat und seine Aussch&uuml;sse in dieser Woche "
                      "<b>bisher</b> entschieden haben." if laufend else
                      "Was der Gemeinderat und seine Aussch&uuml;sse zuletzt "
                      "entschieden haben.")
        zeitraum = (f"Berichtszeitraum {e(meta['zeitraum'])} &middot; w&auml;chst noch"
                    if laufend else f"Berichtszeitraum {e(meta['zeitraum'])}")
        karten.append((10, f"""    <a class="karte" href="{pfad}">
      <p class="art">{art}</p>
      <h3>Waldseer Ratswoche, KW {kw}/{jahr}</h3>
      <p>{einleitung}
      {beschreibung}.</p>
      <p class="meta">{zeitraum}</p>
    </a>"""))

    if register:
        ges_a = sum(len(v) for v in register.values())
        ges_b = sum(x["beschluesse"] for v in register.values() for x in v.values())
        jahre = sorted(register, reverse=True)
        spanne = (f"Jahrg&auml;nge {jahre[-1]}–{jahre[0]}" if len(jahre) > 1
                  else f"Jahrgang {jahre[0]}")
        karten.append((70, f"""    <a class="karte" href="./ausgaben/index.html">
      <p class="art">Ratswoche &middot; Archiv</p>
      <h3>Alle bisherigen Ausgaben</h3>
      <p>{zahlwort(ges_a)} Ausgaben mit zusammen {ges_b} Beschl&uuml;ssen, eine f&uuml;r jede
      Kalenderwoche, in der getagt wurde. Jede Ausgabe nennt auch die Sitzungen,
      zu denen online kein Protokoll abrufbar ist.</p>
      <p class="meta">{spanne} &middot; maschinell erzeugt</p>
    </a>"""))

    heute = dt.date.today()
    stichtag = kennzahlen.get("stichtag", heute.isoformat())

    return f"""{kopf("Ratsakten Bad Waldsee", hier="start",
                     beschreibung="Maschinelle Auswertung der öffentlich zugänglichen "
                                  "Sitzungsunterlagen der Stadt Bad Waldsee.",
                     stile=("startseite.css", "termine.css"))}
<div class="wrap">

<header>
  <p class="eyebrow">Lernprojekt &middot; Kommunaldaten</p>
  <h1>Ratsakten Bad Waldsee</h1>
  <p class="lede">Die Sitzungsunterlagen der Stadt Bad Waldsee stehen vollst&auml;ndig
  im Netz — verteilt auf Hunderte von PDF-Dateien. Dieses Projekt wertet sie
  maschinell aus und macht daraus etwas Lesbares.</p>

  <div class="tiles">
{kachel_html}
  </div>
</header>

<section>
  <h2>Einstiege</h2>
  <div class="karten">
{chr(10).join(h for _, h in sorted(karten, key=lambda x: x[0]))}
  </div>
</section>

{zeitleiste(register, stichtag)}{naechste_termine(kennzahlen)}
<section>
  <h2>Worum es geht</h2>
  <p>Lokaljournalismus ist vielerorts zur&uuml;ckgegangen, w&auml;hrend kommunale Unterlagen
  so vollst&auml;ndig online stehen wie nie. Dazwischen klafft eine L&uuml;cke: Die
  Information ist &ouml;ffentlich, aber praktisch ungelesen — nicht weil sie geheim w&auml;re,
  sondern weil niemand die Zeit hat, Bebauungsplanverfahren und Geb&uuml;hrenkalkulationen
  durchzuarbeiten.</p>
  <p>Das Projekt geht drei technischen Fragen nach:</p>
  <ul class="plain">
    <li>Wie gut lassen sich kommunale Ratsinformationssysteme maschinell erschlie&szlig;en?</li>
    <li>Wie viel Substanz steckt tats&auml;chlich in den Dokumenten — und wie viel ist Formalie?</li>
    <li>Wo endet das, was aus Akten allein erkennbar ist?</li>
  </ul>
  <p>Alle Auswertungen beruhen ausschlie&szlig;lich auf &ouml;ffentlich zug&auml;nglichen
  Dokumenten des <a href="https://ris.bad-waldsee.de/" rel="noopener">Ratsinformationssystems</a>
  und der <a href="https://www.bad-waldsee.de/buerger/de/rathaus-service/aktuelles-bekanntmachungen/oeffentliche-bekanntmachungen" rel="noopener">&ouml;ffentlichen
  Bekanntmachungen</a>. Es wurden keine Zugangsbeschr&auml;nkungen umgangen.</p>
</section>

<section style="border-bottom:none">
  <h2>Hinweise</h2>
  <div class="hinweis">
    <p class="lab">Privates Lernprojekt &middot; maschinell erzeugt &middot; ohne Gew&auml;hr</p>
    <p>F&uuml;r Richtigkeit, Vollst&auml;ndigkeit und Aktualit&auml;t wird keine
    Gew&auml;hr &uuml;bernommen. <b>Verbindlich ist ausschlie&szlig;lich das
    Originaldokument der Stadt Bad Waldsee.</b></p>
    <details class="mehr">
      <summary>Ausf&uuml;hrlicher Hinweis</summary>
      <p>Diese Auswertung beschreibt, was in den Unterlagen steht. Sie sucht nicht nach
      Missst&auml;nden und bewertet weder die Arbeit der Verwaltung noch die einzelner
      Personen; rechtswidriges oder schuldhaftes Verhalten wird niemandem unterstellt.</p>
      <p>Die Seite ist ein privates Lern- und Technologieprojekt zur automatisierten
      Auswertung &ouml;ffentlich zug&auml;nglicher Verwaltungsdokumente — kein
      journalistisches Erzeugnis, kein Pr&uuml;fbericht und keine rechtliche oder fachliche
      Bewertung.</p>
      <p>Alle Auswertungen beruhen auf maschineller Verarbeitung von PDF-Dokumenten; Fehler
      bei Texterkennung und Zuordnung sind m&ouml;glich. Einordnungen und Wertungen sind als
      <b>KI-Deutung</b> gekennzeichnet: maschinell erzeugt und nicht redaktionell
      gepr&uuml;ft. Namen von Privatpersonen werden nicht wiedergegeben. Korrekturen sind
      erw&uuml;nscht und werden zeitnah eingearbeitet. Es besteht keine Verbindung zur
      Stadt Bad Waldsee.</p>
    </details>
  </div>
</section>

</div>
{fuss(meta=f"Datenstand {kurz(stichtag)}")}
"""


def zeitleiste(register: dict, stichtag: str) -> str:
    """Eine Zelle je Kalenderwoche, verlinkt in die Ausgabe dieser Woche.

    Die Aufgabe ist zweierlei: zeigen, wann wie dicht getagt wurde, und einen
    Sprung in die jeweilige Wochenausgabe anbieten. Deshalb ein Kalenderraster
    und keine Kurve — es geht um Dichte und Sprungziele, nicht um einen Verlauf.

    Die Faerbung ist sequenziell: ein Farbton, vier Stufen, hell bedeutet viel.
    Alle vier Stufen halten mindestens 3:1 Kontrast zum Seitengrund, damit auch
    eine einzelne Sitzung noch als anklickbare Flaeche erkennbar ist.
    """
    # Auch hier der Kalendertag: Sonst fehlt die Zelle der laufenden Woche an
    # jedem Tag, an dem abends noch eine Sitzung ansteht.
    heute = dt.date.today()
    letzte_kw = heute.isocalendar()[1]
    zeilen = []
    for jahr in sorted(register, reverse=True):
        wochen = register[jahr]
        zellen = []
        for kw in range(1, 54):
            if jahr == str(heute.year) and kw > letzte_kw:
                continue                       # kuenftige Wochen gibt es nicht
            try:
                dt.date.fromisocalendar(int(jahr), kw, 1)
            except ValueError:
                continue                       # KW 53 hat nicht jedes Jahr
            schluessel = f"{kw:02d}"
            a = wochen.get(schluessel)
            if not a:
                zellen.append(
                    f'<span class="w leer" title="KW {kw}/{jahr} &middot; keine Sitzung"></span>')
                continue
            n = a["sitzungen"]
            # Fuer die laufende Woche gibt es stets eine Ausgabe, auch wenn noch
            # nichts getagt hat. Sie bleibt anklickbar, wird aber nicht gefaerbt —
            # sonst zeigte die Skala eine Sitzung an, die es nicht gab.
            stufe = 0 if n == 0 else 1 if n == 1 else 2 if n == 2 else 3 if n == 3 else 4
            wort = "Sitzung" if n == 1 else "Sitzungen"
            klasse = "w leer" if stufe == 0 else f"w s{stufe}"
            titel = (f'KW {kw}/{jahr} &middot; {a["zeitraum"]} &middot; {n} {wort}, '
                     f'{a["beschluesse"]} Beschl&uuml;sse')
            zellen.append(
                f'<a class="{klasse}" href="./ausgaben/{jahr}/kw{schluessel}.html" '
                f'title="{titel}"><span class="sr">KW {kw}/{jahr}, {n} {wort}</span></a>')
        zeilen.append(
            '      <div class="jahrzeile">\n'
            f'        <span class="jahr">{jahr}</span>\n'
            f'        <div class="wochen">{"".join(zellen)}</div>\n'
            '      </div>')

    # Kopfzeile mit den Kalenderwochen. Nicht jede Nummer passt ueber eine
    # 11px breite Spalte — beschriftet wird jede fuenfte, die uebrigen Spalten
    # halten nur den Platz, damit die Beschriftung ueber ihrer Woche steht.
    marken = []
    for kw in range(1, 54):
        try:
            dt.date.fromisocalendar(int(max(register)), kw, 1)
        except ValueError:
            continue
        if kw == 1 or kw % 5 == 0:
            marken.append(f'<span class="kw beschriftet">{kw}</span>')
        else:
            marken.append('<span class="kw"></span>')
    kopfzeile = ('      <div class="jahrzeile kopf">\n'
                 '        <span class="jahr">KW</span>\n'
                 f'        <div class="wochen">{"".join(marken)}</div>\n'
                 '      </div>')
    zeilen.insert(0, kopfzeile)

    inhalt = "\n".join(zeilen)
    return (
        '\n<section>\n'
        '  <h2>Zeitleiste</h2>\n'
        '  <div class="zeitleiste">\n'
        f'{inhalt}\n'
        '  </div>\n'
        '  <p class="skala"><span>weniger</span>'
        '<span class="w s1"></span><span class="w s2"></span>'
        '<span class="w s3"></span><span class="w s4"></span>'
        '<span>mehr Sitzungen</span><span class="trenn">&middot;</span>'
        '<a href="./ausgaben/index.html">alle Ausgaben als Liste</a></p>\n'
        '</section>\n')


def naechste_termine(kennzahlen: dict) -> str:
    """Die naechsten angekuendigten Sitzungen, mit Tagesordnung wo vorhanden.

    Das Ratsinformationssystem fuehrt Termine, die noch bevorstehen. Sie
    beantworten die Frage, die vor jeder Auswertung kommt: Was steht an? Liegt
    die Tagesordnung schon vor, laesst sie sich aufklappen — samt
    Vorlagennummern und den dort verlinkten Unterlagen. Meist erscheint sie
    erst wenige Tage vorher, und auch das ist eine Auskunft.
    """
    kommend = kennzahlen.get("kommende_sitzungen") or []
    if not kommend:
        return ""
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag"]
    monate = ["Januar", "Februar", "M&auml;rz", "April", "Mai", "Juni", "Juli",
              "August", "September", "Oktober", "November", "Dezember"]
    # Der tatsaechliche Tag, nicht der Stichtag der Auswertung. Der faellt auf
    # den Vortag zurueck, solange heute noch eine Sitzung aussteht — und genau
    # diese Sitzung wurde dann als „morgen" angekuendigt, obwohl sie heute
    # Abend stattfindet. Dieselbe Verwechslung wie auf der Terminseite, die
    # sie laengst nicht mehr macht.
    heute = dt.date.today()
    zeilen = []
    for t in kommend:
        d = dt.date.fromisoformat(t["datum"])
        hin = (d - heute).days
        bald = ("morgen" if hin == 1 else f"in {hin} Tagen" if hin <= 14 else "")
        punkte = t.get("punkte") or []
        sitzung = t.get("url") or ""

        if punkte:
            eintraege = []
            for p in punkte:
                dok = "".join(
                    f'<a class="doc" href="{e(x["url"])}" target="_blank" '
                    f'rel="noopener noreferrer">{e(x["titel"])}</a>'
                    for x in p["dokumente"])
                nummer = (f'<span class="sv">{e(p["vorlage"])}</span>'
                          if p["vorlage"] else "")
                unterlagen = f'<span class="unterlagen">{dok}</span>' if dok else ""
                eintraege.append(
                    f'        <li><span class="sache">{e(p["titel"])}{nummer}</span>'
                    f'{unterlagen}</li>')
            wort = "Tagesordnungspunkt" if len(punkte) == 1 else "Tagesordnungspunkte"
            quelle = (f'        <p class="quelle"><a href="{e(sitzung)}" target="_blank" '
                      f'rel="noopener noreferrer">Sitzung im '
                      f'Ratsinformationssystem</a></p>\n' if sitzung else "")
            tops = "\n".join(eintraege)
            agenda = (
                f'      <details class="agenda">\n'
                f'        <summary>{len(punkte)} {wort}</summary>\n'
                f'        <ol class="tops">\n{tops}\n        </ol>\n'
                f'{quelle}'
                f'      </details>')
        else:
            termin_quelle = (f' &middot; <a href="{e(sitzung)}" target="_blank" '
                             f'rel="noopener noreferrer">Termin im '
                             f'Ratsinformationssystem</a>' if sitzung else "")
            agenda = ('      <p class="agenda offen">Tagesordnung noch nicht '
                      f'ver&ouml;ffentlicht{termin_quelle}</p>')

        jahreszahl = "" if d.year == heute.year else " " + str(d.year)
        hinweis = f'<span class="bald">{bald}</span>' if bald else ""
        zeilen.append(
            f'    <li>\n'
            f'      <p class="wann">{tage[d.weekday()]}, {d.day}. '
            f'{monate[d.month - 1]}{jahreszahl}'
            f'<span class="uhr">{t["zeit"]} Uhr</span>{hinweis}</p>\n'
            f'      <p class="gremium">{e(t["gremium"])}</p>\n'
            f'{agenda}\n'
            f'    </li>')

    liste = "\n".join(zeilen)
    return (
        f'\n<section>\n'
        f'  <h2>Was als N&auml;chstes ansteht</h2>\n'
        f'  <ol class="termine">\n{liste}\n  </ol>\n'
        f'  <p class="fussnote">Angek&uuml;ndigte Sitzungen aus dem Ratsinformationssystem. '
        # „ohne Anmeldung" stand hier ohne Fundstelle. Was gilt, ist die
        # Oeffentlichkeit der Sitzung; die Einzelheiten stehen belegt auf
        # „Wer entscheidet was" — hier nur der Verweis dorthin.
        f'Sie sind &ouml;ffentlich, soweit nicht ausdr&uuml;cklich nicht&ouml;ffentlich '
        f'beraten wird (<a href="./gremien.html#gemeinderat">was das hei&szlig;t</a>). '
        f'<a href="./termine.html#heute">Alle Termine, auch vergangene</a>.</p>\n'
        f'</section>\n')


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(bauen(), encoding="utf-8")
    register = json.loads((DATEN / "ausgaben.json").read_text(encoding="utf-8"))
    aktuell = neueste_ausgabe(register)
    print("docs/index.html erzeugt"
          + (f" — verlinkt auf KW {aktuell[2]}/{aktuell[1]}" if aktuell else ""))


if __name__ == "__main__":
    main()
