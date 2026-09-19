"""Schritt 11 — je Vorhaben eine Chronik.

Die Wochenausgaben ordnen nach Kalenderwochen. Ein Buerger denkt aber nicht in
Kalenderwochen, sondern in Themen: „Drei Eichen", „Agri-Solarpark",
„Feuerwehrgeraetehaus". Ein Vorhaben durchlaeuft ueber Jahre mehrere Gremien
und Vorlagennummern; aus den Einzelausgaben laesst sich dieser Verlauf nicht
zusammensetzen.

Diese Seiten stellen ihn dar: alle Stationen eines Vorhabens in zeitlicher
Folge, mit Gremium, Vorlagennummer, Beschlusswortlaut, Abstimmungsergebnis und
den verlinkten Unterlagen.

Die Gruppierung stammt unveraendert aus Schritt 08 (data/vorgaenge.json).
Zwei Fassungen derselben Logik wuerden auseinanderlaufen.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from begriffe import markieren
from seite import fuss, kopf, zahlwort
from verfahrensweg import lohnt, schritte
from vorhaben import MINDEST_STATIONEN, zusammenfuehren

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
ZIEL = WURZEL / "docs" / "themen"



def e(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))




def datum_lang(iso: str) -> str:
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
              "August", "September", "Oktober", "November", "Dezember"]
    d = dt.date.fromisoformat(iso)
    return f"{d.day}. {monate[d.month - 1]} {d.year}"


EIGEN = """
/* Nur die Themenseiten brauchen diese Stile: die Chronik eines Vorhabens und
   die Kartenliste aller Vorhaben. */
.quelle{margin:8px 0 0;font-family:var(--mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase}
/* Die Chronik ist zu lang fuer einen Kasten, soll aber denselben Aufbau
   tragen wie „Worum es geht" und „Der Weg durch das Verfahren": Ueberschrift,
   Herkunftsmarke, Hinweis. Vorher stand ihre Herkunftsangabe als loser Absatz
   zwischen zwei beschrifteten Kaesten und gehoerte sichtbar zu nichts. */
h2.abschnitt{margin:34px 0 0;font-size:17px;letter-spacing:-.01em}
p.woherfrei{margin:6px 0 0;font-family:var(--mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
p.hinweisfrei{margin:10px 0 0;font-size:13.5px;line-height:1.6;
  color:var(--muted);max-width:62ch}
ol.chronik{list-style:none;margin:18px 0 0;padding:0;counter-reset:station}
ol.chronik > li{
  position:relative;margin:0;padding:18px 0 22px 22px;border-top:1px solid var(--rule);
}
ol.chronik > li::before{
  counter-increment:station;content:counter(station);position:absolute;left:0;top:20px;
  font-family:var(--mono);font-size:11px;color:var(--muted);
}
ol.chronik .wann{
  margin:0 0 6px;font-family:var(--mono);font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
}
ol.chronik .sache{margin:0 0 8px;font-weight:600;font-size:16px;max-width:62ch}
ol.chronik .wortlaut{margin:0 0 10px;max-width:62ch;font-size:14.5px;line-height:1.6;color:var(--muted)}
/* Kurzfassung des Verfahrensverlaufs, ueber der Chronik. Sie muss auf dem
   Handy in einem Blick lesbar sein — deshalb drei kurze Zeilen je Schritt
   statt einer breiten Tabellenzeile. */
/* „Worum es geht" — der Sachverhalt der ersten Sitzungsvorlage. Ohne ihn
   erklaert die Seite den Verfahrensweg eines Wohnbaugebiets, ohne je zu
   sagen, dass es ein Wohnbaugebiet ist. */
section.worum{margin:26px 0 0;padding:18px 16px 14px;border:1px solid var(--rule)}
section.worum h2{margin:0;font-size:17px;letter-spacing:-.01em}
section.worum .woher{margin:6px 0 0;font-family:var(--mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
section.worum p.text{margin:10px 0 0;font-size:15px;line-height:1.65;max-width:62ch}
section.worum .quelle{margin:10px 0 0;font-size:13px;line-height:1.6;
  color:var(--muted);max-width:62ch;font-family:inherit;letter-spacing:0;
  text-transform:none}
section.weg{margin:26px 0 0;padding:18px 16px 10px;background:var(--surface);
  border:1px solid var(--rule)}
section.weg h2{margin:0;font-size:17px;letter-spacing:-.01em}
section.weg .woher{margin:6px 0 0;font-family:var(--mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
section.weg .hinweis{margin:10px 0 0;font-size:13.5px;line-height:1.6;
  color:var(--muted);max-width:62ch}
ol.wegliste{list-style:none;margin:14px 0 0;padding:0;counter-reset:wegschritt}
ol.wegliste > li{position:relative;border-top:1px solid var(--rule)}
ol.wegliste > li:first-child{border-top:0}
ol.wegliste a{display:block;position:relative;padding:12px 0 12px 26px;
  text-decoration:none;color:inherit;min-height:44px}
ol.wegliste a:hover .wasname{text-decoration:underline}
ol.wegliste > li::before{
  counter-increment:wegschritt;content:counter(wegschritt);position:absolute;
  left:0;top:14px;font-family:var(--mono);font-size:11px;color:var(--muted)}
ol.wegliste .wann{display:block;font-family:var(--mono);font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
ol.wegliste .wasname{display:block;font-weight:600;font-size:15px;margin:3px 0 2px}
ol.wegliste .wo{display:block;font-size:13px;line-height:1.5;color:var(--muted)}
ol.wegliste .sv{font-family:var(--mono);font-size:11px;letter-spacing:.04em}
.karten{display:grid;gap:10px;margin:24px 0}
a.karte{
  display:block;padding:14px 16px;background:var(--surface);border:1px solid var(--rule);
  text-decoration:none;color:inherit;
}
a.karte:hover{border-color:var(--s1)}
a.karte .wort{display:block;font-weight:600;font-size:16px;margin-bottom:4px}
a.karte .meta{
  display:block;font-family:var(--mono);font-size:11px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
}
"""


def station_html(st: dict, erklaert: set[str]) -> str:
    dok = "".join(
        f'<a class="doc" href="{e(d["url"])}" target="_blank" '
        f'rel="noopener noreferrer">{e(d["titel"])}</a>'
        for d in st.get("dok", []))
    unterlagen = f'<div class="unterlagen">{dok}</div>' if dok else ""
    # Reihenfolge ist hier inhaltlich: Ein Begriff wird je Seite einmal
    # aufgemacht, und zwar an seiner **ersten sichtbaren** Stelle. Der Titel
    # steht ueber dem Beschlusswortlaut — wird er spaeter markiert, klebt die
    # Erklaerung weiter unten als dort, wo der Leser ueber das Wort stolpert.
    sache = markieren(e(st["t"]), erklaert)
    wortlaut = (f'<p class="wortlaut">{markieren(e(st["w"]), erklaert)}</p>'
                if st.get("w") else "")
    ergebnis = (f'<span class="erg">{e(st["e"])}</span>'
                if st.get("e") else '<span class="erg">ohne Abstimmung</span>')
    ausgabe = st.get("a") or ""
    if ausgabe.startswith("./"):
        ausgabe = "../" + ausgabe[2:]
    verweis = (f'<p class="quelle"><a href="{e(ausgabe)}">In der Wochenausgabe nachlesen</a></p>'
               if ausgabe else "")
    return f"""  <li id="station-{st['_nr']}">
    <p class="wann">{datum_lang(st['d'])} &middot; {e(st['gl'])}
      {f'<span class="sv">{e(st["v"])}</span>' if st.get("v") else ""}</p>
    <p class="sache">{sache}</p>
    {wortlaut}
    {ergebnis}
    {unterlagen}
    {verweis}
  </li>"""


def und_liste(teile: list[str]) -> str:
    """„a, b und c" — fuer Aufzaehlungen im Fliesstext."""
    if len(teile) <= 1:
        return teile[0] if teile else ""
    return ", ".join(teile[:-1]) + " und " + teile[-1]


def worum_html(stationen: list[dict], erklaert: set[str]) -> str:
    """Der Sachverhaltsabschnitt der ersten Sitzungsvorlage, woertlich.

    Beschluesse benennen den Verwaltungsvorgang, nicht die Sache; der Abschnitt
    „Zum Sachverhalt" der ersten Vorlage nennt sie. Schritt 08 legt ihn an die
    Station.

    **Der Kasten hiess zuerst „Worum es geht" — und hielt das nicht.** Ueber den
    ganzen Bestand ausgezaehlt beginnen **13 der 26 Sachverhalte** mit der
    Vorgeschichte des Verfahrens („Der Ausschuss hat am … den
    Aufstellungsbeschluss gefasst", „Nach Schaffung der Heilungsmoeglichkeit in
    § 215a BauGB …"), nicht mit dem Vorhaben. Eine Ueberschrift, die eine
    Zusammenfassung verspricht, ueber einem woertlichen Zitat aus dem
    Amtsdeutsch ist ein Versprechen, das die Haelfte der Seiten bricht.

    Die Ueberschrift sagt jetzt, was der Kasten ist: ein Zitat aus der ersten
    Sitzungsvorlage. Die Zahl 13 steht **nicht** im Seitentext — sie waechst mit
    dem Bestand, und eine ungeprueft mitgeschleppte Zahl ist die Fehlerklasse
    dieses Projekts.
    """
    mit = [s for s in sorted(stationen, key=lambda x: x["d"]) if s.get("sv")]
    if not mit:
        return ""
    st = mit[0]

    # Die Vorlage nennen und nicht verlinken hiesse, den Leser mit einer
    # Kennung allein zu lassen. Verlinkt wird **nur** das Dokument, das die
    # Vorlagennummer im Titel traegt — im ganzen Bestand ist das eindeutig
    # (26 von 26). Gibt es keinen solchen Treffer, bleibt die Nummer Text:
    # lieber kein Verweis als ein falscher.
    ziel = next((d for d in st.get("dok", [])
                 if st.get("v") and st["v"] in d.get("titel", "")), None)
    if not st.get("v"):
        nummer = ""
    elif ziel:
        nummer = (f' <a class="doc" href="{e(ziel["url"])}" target="_blank" '
                  f'rel="noopener noreferrer">{e(st["v"])}</a>')
    else:
        nummer = f' {e(st["v"])}'
    # Die Station steht weiter unten mit Beschlusswortlaut, Abstimmung und
    # allen Unterlagen — dorthin fuehrt das Datum.
    wann = (f'<a href="#station-{st["_nr"]}">{datum_lang(st["d"])}</a>'
            if st.get("_nr") else datum_lang(st["d"]))
    return f"""
<section class="worum" aria-labelledby="worumtitel">
  <h2 id="worumtitel">Aus der ersten Sitzungsvorlage</h2>
  <p class="woher">Beleg &middot; Abschnitt „Zum Sachverhalt“</p>
  <p class="text">{markieren(e(st['sv']), erklaert)}</p>
  <p class="quelle">Sitzungsvorlage{nummer}, behandelt am {wann}; gekürzt.
  Die Verwaltung beginnt dort oft mit der Vorgeschichte des Verfahrens.</p>
</section>
"""


def weg_html(weg: list[dict], stationen: list[dict],
             erklaert: set[str]) -> str:
    """Die Kurzfassung des Verfahrensverlaufs als Sprungliste in die Chronik.

    **Hier wird bewusst nicht erklaert.** Jede Zeile ist ein Sprunglink, und
    `markieren` setzt ein `tabindex`-Element in den Text. Innerhalb eines Links
    ist das zweifach schaedlich: Ein Tippen auf das erklaerte Wort loest den
    Sprung aus, statt die Erklaerung zu zeigen — auf dem Handy waere sie
    unerreichbar —, und ein fokussierbares Element im Link ergibt zwei
    Tabstopps fuer eine Sache.

    Die Begriffe dieser Liste stehen samt Titel noch einmal in der Chronik
    darunter; dort wird erklaert, und `erklaert` wird durchgereicht, damit es
    genau einmal geschieht.
    """
    # Den Strang nur nennen, wo er unterscheidet. Laeuft ein Vorhaben nur als
    # Flaechennutzungsplanaenderung, stuende in jeder Zeile dasselbe Wort.
    namen = {s["strang"] for s in weg if s["strang"]}
    mehrere = len({s["strang"] for s in weg}) > 1

    # Ohne diesen Satz liest sich die Liste falsch: Bei „Drei Eichen VI" steht
    # der Satzungsbeschluss — das Ende eines Verfahrens — vor dem
    # Aufstellungsbeschluss, seinem Anfang. Untereinander sieht das aus, als sei
    # ein fertiger Plan wieder aufgeschnuert worden. Tatsaechlich sind es zwei
    # Verfahren, eines fuer Teilbereich A und eines fuer B.
    #
    # **Fruehere Fassung war falsch.** Sie sagte „Die Daten steigen deshalb
    # nicht durchgehend an". Das stimmt nicht: `schritte()` geht die Stationen
    # nach Datum durch und haengt in dieser Reihenfolge an — ueber alle 15
    # Bloecke nachgerechnet, keiner faellt zurueck. Nicht die Datumsfolge ist
    # gestoert, sondern die Reihenfolge der Verfahrensschritte.
    #
    # Planart und Teilbereich werden getrennt aufgezaehlt. Zusammengesetzt lautet
    # der
    # Satz „… nebeneinander: Bebauungsplan, Bebauungsplan, Teilbereich A,
    # Bebauungsplan, Teilbereich B, …" — die Kommas der Namen und die der
    # Aufzaehlung sind dann nicht mehr auseinanderzuhalten.
    arten = sorted({n.split(", Teilbereich")[0] for n in namen})
    bereiche = sorted({n.split(", Teilbereich ")[1] for n in namen
                       if ", Teilbereich " in n})
    # Jeder Zweig muss einen Satz ergeben, der auch stimmt. „Mehrere Straenge"
    # heisst nicht zwingend „mehrere Planarten": Traegt ein Teil der Schritte
    # gar keinen Strang, bleibt eine einzige Art uebrig — und ohne Teilbereiche
    # stuende dann „laeuft in getrennten Teilbereichen" ueber einem Vorhaben,
    # das keine hat. Im heutigen Bestand tritt der Fall nicht auf; er waere
    # eine falsche Tatsachenbehauptung, sobald er auftritt.
    teilsatz = (f", teils getrennt nach Teilbereich {e(und_liste(bereiche))}"
                if bereiche else "")
    satz = ""
    if len(arten) > 1:
        satz = (f"Zu diesem Vorhaben laufen mehrere Verfahren nebeneinander: "
                f"{e(und_liste(arten))}{teilsatz}.")
    elif bereiche:
        wo = f"Das Verfahren zum {e(arten[0])}" if arten else "Dieses Vorhaben"
        satz = (f"{wo} läuft getrennt nach Teilbereich "
                f"{e(und_liste(bereiche))}.")

    straenge = ""
    if satz:
        straenge = (f'\n  <p class="hinweis">{satz} Geordnet ist nach Datum — '
                    f'ein Satzungsbeschluss kann deshalb vor einem '
                    f'Aufstellungsbeschluss stehen.</p>')

    zeilen = []
    for sch in weg:
        teile = []
        if mehrere and sch["strang"]:
            teile.append(e(sch["strang"]))
        if sch["bis"] != sch["von"]:
            teile.append(f'zuletzt {e(sch["gremien"][-1])}, '
                         f'{datum_lang(sch["bis"])}')
        else:
            teile.append(e(sch["gremien"][0]))
        # Die Vorlagennummer trennt gleichlautende Schritte voneinander — das
        # Sanierungsgebiet „Altstadt III" hat zwei Vorlagen mit demselben
        # Titel — und ist zugleich die Kennung, unter der sich ein Schritt im
        # Ratsinformationssystem wiederfinden laesst.
        if sch["vorlage"]:
            teile.append(f'<span class="sv">{e(sch["vorlage"])}</span>')
        zeilen.append(f"""    <li><a href="#station-{sch['nr']}">
      <span class="wann">{datum_lang(sch['von'])}</span>
      <span class="wasname">{e(sch['name'])}</span>
      <span class="wo">{' &middot; '.join(teile)}</span>
    </a></li>""")

    # Was die Kurzfassung nicht zeigt, muss sie selbst sagen — sonst liest sie
    # sich als vollstaendiger Verlauf. Der Satz steht **vor** der Liste, im
    # Einleitungsabsatz: Als abgesetzter Nachsatz unter einer Trennlinie ueber
    # die volle Breite las sich diese Linie wie die Unterkante des Kastens, und
    # der Satz wirkte herausgefallen. Ausserdem kam er zu spaet — wer die Liste
    # gelesen hat, haelt sie da schon fuer den ganzen Verlauf.
    uebrig = len(stationen) - sum(s["stationen"] for s in weg)
    rest = ""
    if uebrig == 1:
        rest = (" Eine Station nennt keinen Schritt und steht nur in der "
                "Chronik.")
    elif uebrig:
        rest = (f" {zahlwort(uebrig)} Stationen nennen keinen Schritt und "
                f"stehen nur in der Chronik.")

    return f"""
<section class="weg" aria-labelledby="wegtitel">
  <h2 id="wegtitel">Der Weg durch das Verfahren</h2>
  <p class="woher">Regelbasiert &middot; aus den amtlichen Titeln</p>
  <p class="hinweis">Eine Vorlage durch mehrere Gremien zählt einmal.{rest}</p>{straenge}
  <ol class="wegliste">
{chr(10).join(zeilen)}
  </ol>
</section>
"""


def seite_bauen(vg: dict) -> str:
    stationen = sorted(vg["s"], key=lambda s: s["d"])
    for nr, st in enumerate(stationen, 1):
        st["_nr"] = nr
    weg = schritte(stationen)
    # Ein Begriff wird je Seite einmal aufgemacht. Die Reihenfolge der Ausgabe
    # bestimmt, wo: zuerst „Worum es geht", dann der Verfahrensweg, dann die
    # Chronik — der f-String unten wird von oben nach unten ausgewertet.
    erklaert: set[str] = set()
    von, bis = stationen[0]["d"], stationen[-1]["d"]
    # Vorher eine alphabetische Namensliste. Die sagte nichts — und sie zaehlte
    # eine Umbenennung als zwei Gremien: „Ausschuss fuer Umwelt und Technik"
    # tagte bis zum 17.06.2024, „Ausschuss fuer Umwelt, Technik und
    # Nachhaltigkeit" ab dem 16.09.2024, nie beide am selben Tag.
    #
    # Jetzt nach dem ersten Auftreten geordnet und gezaehlt: Das zeigt, wer den
    # Vorgang wie oft behandelt hat, und stellt die Abfolge richtig dar.
    haeufig: dict[str, int] = {}
    for st in stationen:
        haeufig[st["gl"]] = haeufig.get(st["gl"], 0) + 1
    gremienzeile = " &middot; ".join(
        f'{e(name)} <b>{anzahl}&times;</b>' for name, anzahl in haeufig.items())
    nummern = [n for n in vg["v"].split(" · ") if n]
    # Der amtliche Titel stand hier frueher als eigener Block. Er sagte dem
    # Leser nichts: Es ist einer von zwoelf, er nennt nur ein Teilverfahren,
    # und **jede Station zeigt ihren eigenen Titel samt Vorlagennummer** in der
    # Chronik. Sein Zweck — den Vorgang im Ratsinformationssystem
    # wiederfinden — ist seit der Verlinkung der Sitzungsvorlage erfuellt.

    t = [kopf(f"{vg['t']} · Chronik eines Vorhabens", hoch="../", hier="themen",
              beschreibung=f"Alle Stationen des Vorhabens „{vg['t']}\u201c in den "
                           f"Gremien der Stadt Bad Waldsee.",
              eigen=EIGEN),
         '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Vorhaben</p>
  <h1>{e(vg['t'])}</h1>
  <p class="lede">Alle Stationen in den Gremien, in zeitlicher Reihenfolge.</p>
  <div class="issueline">
    <span><b>Stationen</b> {len(stationen)}</span>
    <span><b>Zeitraum</b> {datum_lang(von)} bis {datum_lang(bis)}</span>
    <span><b>Vorlagen</b> {len(nummern)}</span>
    <span><b>Herkunft</b> regelbasiert gezählt</span>
  </div>
</header>

<p class="gremienzeile">{gremienzeile}</p>
{worum_html(stationen, erklaert)}
{weg_html(weg, stationen, erklaert) if lohnt(weg, stationen) else ""}

<h2 class="abschnitt">Alle Stationen im Wortlaut</h2>
<p class="woherfrei">Beleg &middot; aus den Beschlussprotokollen</p>
<p class="hinweisfrei">Abstimmungsergebnisse aus der Zeile „Ergebnis der
Beschlussfassung“. Nichtöffentliche Beratungen sind nicht enthalten.</p>

<ol class="chronik">
{chr(10).join(station_html(s, erklaert) for s in stationen)}
</ol>
""")
    t.append("</div>")
    t.append(fuss(hoch="../"))
    return "\n".join(t)


def index_bauen(auswahl: list[dict]) -> str:
    zeilen = []
    for vg in auswahl:
        stationen = sorted(vg["s"], key=lambda s: s["d"])
        zeilen.append(f"""    <a class="karte" href="./{vg["_slug"]}.html">
      <span class="wort">{e(vg['t'])}</span>
      <span class="meta">{len(stationen)} Stationen &middot;
        {datum_lang(stationen[0]['d'])} bis {datum_lang(stationen[-1]['d'])}</span>
    </a>""")
    t = [kopf("Themen · Ratsakten Bad Waldsee", hoch="../", hier="themen",
              beschreibung="Vorhaben der Stadt Bad Waldsee über Jahre hinweg — "
                           "jedes mit allen Stationen in den Gremien.",
              eigen=EIGEN),
         '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Vorhaben im Zeitverlauf</p>
  <h1>Themen</h1>
  <p class="lede">Ein Bauleitplan, ein Gerätehaus, ein Solarpark — solche Vorhaben
  ziehen sich über Jahre und durch mehrere Gremien. Die Wochenausgaben zeigen
  jeweils nur einen Ausschnitt davon. Hier steht der ganze Verlauf.</p>
  <div class="issueline">
    <span><b>Vorhaben</b> {len(auswahl)}</span>
    <span><b>Stationen</b> {sum(len(v["s"]) for v in auswahl)}</span>
    <span><b>Herkunft</b> regelbasiert gezählt</span>
  </div>
</header>

<p>Aufgenommen ist jedes Vorhaben, das im ausgewerteten Zeitraum
mindestens {MINDEST_STATIONEN} Mal auf einer Tagesordnung stand. Zugeordnet wird
über den in Anführungszeichen genannten Namen des Vorhabens; wo die Verwaltung
einen Vorgang anders benennt, kann eine Station fehlen. Einzelne Beschlüsse
finden Sie über die <a href="../suche.html">Suche</a>.</p>

<div class="karten">
{chr(10).join(zeilen)}
</div>
""")
    t.append("</div>")
    t.append(fuss(hoch="../"))
    return "\n".join(t)


def main() -> None:
    quelle = DATEN / "vorgaenge.json"
    if not quelle.exists():
        raise SystemExit(
            "data/vorgaenge.json fehlt — bitte zuerst Schritt 08 ausführen.")
    vorgaenge = json.loads(quelle.read_text(encoding="utf-8"))

    auswahl = zusammenfuehren(vorgaenge)

    ZIEL.mkdir(parents=True, exist_ok=True)
    for alt in ZIEL.glob("*.html"):
        alt.unlink()

    for vg in auswahl:
        (ZIEL / f"{vg['_slug']}.html").write_text(seite_bauen(vg), encoding="utf-8")

    (ZIEL / "index.html").write_text(index_bauen(auswahl), encoding="utf-8")
    print(f"  docs/themen/  —  {len(auswahl)} Vorhaben, "
          f"{sum(len(v['s']) for v in auswahl)} Stationen")


if __name__ == "__main__":
    main()
