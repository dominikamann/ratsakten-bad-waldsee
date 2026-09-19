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
/* Der amtliche Titel eines Vorhabens ist oft ein ganzer Absatz. Als Vorspann
   gelesen erschlug er die Seite; hier steht er als Angabe, wo er hingehoert. */
.amtstitel{
  margin:8px 0 0;font-family:var(--mono);font-size:11px;line-height:1.6;
  color:var(--muted);max-width:78ch;
}
.amtstitel b{color:var(--ink-2);font-weight:600;letter-spacing:.08em;text-transform:uppercase}
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
    """Worum es bei diesem Vorhaben sachlich geht.

    Die Seite erklaerte bisher den Verfahrensweg eines Wohnbaugebiets, ohne je
    zu sagen, dass es ein Wohnbaugebiet ist: Beschluesse benennen den
    Verwaltungsvorgang, nicht die Sache. Der Abschnitt „Zum Sachverhalt" der
    ersten Sitzungsvorlage sagt es — Schritt 08 legt ihn an die Station.

    Es ist die Darstellung der Verwaltung zu **einem** Beschluss, nicht eine
    neutrale Beschreibung des Vorhabens. Genau so ist sie ausgewiesen.
    """
    mit = [s for s in sorted(stationen, key=lambda x: x["d"]) if s.get("sv")]
    if not mit:
        return ""
    st = mit[0]
    nummer = f' {e(st["v"])}' if st.get("v") else ""
    return f"""
<section class="worum" aria-labelledby="worumtitel">
  <h2 id="worumtitel">Worum es geht</h2>
  <p class="woher">Beleg &middot; aus der Sitzungsvorlage</p>
  <p class="text">{markieren(e(st['sv']), erklaert)}</p>
  <p class="quelle">Aus dem Abschnitt „Zum Sachverhalt" der Sitzungsvorlage{nummer},
  behandelt am {datum_lang(st['d'])}. Das ist die Darstellung der Verwaltung zu
  diesem einen Beschluss — nicht eine Beschreibung des ganzen Vorhabens. Gekürzt;
  maßgeblich ist die Vorlage selbst.</p>
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

    # Ohne diesen Satz liest sich die Liste falsch: Bei „Drei Eichen VI" faellt
    # der Satzungsbeschluss fuer Teilbereich A auf den 25.11.2024, der fuer
    # Teilbereich B erst auf den 07.04.2025 — untereinander sieht das aus, als
    # sei ein fertiger Plan wieder aufgeschnuert worden. Tatsaechlich laufen
    # zwei Verfahren nebeneinander.
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
    satz = ""
    if len(arten) > 1:
        satz = (f"Dieses Vorhaben läuft in mehreren Verfahren nebeneinander: "
                f"{e(und_liste(arten))}.")
        if bereiche:
            satz += (f" Einzelne davon sind zusätzlich nach Teilbereichen "
                     f"getrennt ({e(und_liste(bereiche))}).")
    elif bereiche:
        wo = f"Das Verfahren zum {e(arten[0])}" if arten else "Dieses Vorhaben"
        satz = (f"{wo} läuft in getrennten Teilbereichen "
                f"({e(und_liste(bereiche))}).")

    straenge = ""
    if satz:
        straenge = (f'\n  <p class="hinweis">{satz} Hinter jedem Schritt steht, '
                    f'zu welchem Verfahren er gehört. Die Daten steigen deshalb '
                    f'nicht durchgehend an — ein Verfahren kann abgeschlossen '
                    f'sein, während ein anderes erst beginnt.</p>')

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
        rest = (" Eine weitere Station nennt in ihrem Titel keinen "
                "Verfahrensschritt; sie steht nur in der Chronik darunter.")
    elif uebrig:
        rest = (f" {zahlwort(uebrig)} weitere Stationen nennen in ihrem Titel "
                f"keinen Verfahrensschritt; sie stehen nur in der Chronik "
                f"darunter.")

    return f"""
<section class="weg" aria-labelledby="wegtitel">
  <h2 id="wegtitel">Der Weg durch das Verfahren</h2>
  <p class="woher">Regelbasiert &middot; aus den amtlichen Titeln</p>
  <p class="hinweis">Aufgeführt ist jeder Schritt, den der amtliche Titel einer
  Station selbst benennt, in der Reihenfolge seiner ersten Behandlung. Eine
  Vorlage, die mehrere Gremien durchläuft, steht als <i>ein</i> Schritt.{rest}
  Jede Zeile führt zur zugehörigen Station.</p>{straenge}
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
    gremien = sorted({s["gl"] for s in stationen})
    nummern = [n for n in vg["v"].split(" · ") if n]
    # Der amtliche Titel ist oft ein ganzer Absatz und taugt nicht als Vorspann.
    # Er gehoert trotzdem auf die Seite — wer im Ratsinformationssystem sucht,
    # findet den Vorgang nur unter diesem Wortlaut.
    #
    # Er ist aber **einer von mehreren**: „Drei Eichen VI" laeuft unter zwoelf
    # verschiedenen Titeln, und der laengste davon nennt nur die Aenderung des
    # Flaechennutzungsplans in Teilbereich B. Unbeschriftet als „Amtlicher
    # Titel" gelesen, hielte man die ganze Seite dafuer. Also wird gesagt,
    # wie viele es sind.
    lang_titel = (vg.get("u") or "").strip()
    anzahl_titel = len({" ".join((s.get("t") or "").split()) for s in stationen})
    amtstitel = ""
    if lang_titel and lang_titel != vg["t"]:
        vorsatz = ("Amtlicher Titel" if anzahl_titel <= 1 else
                   f"Einer von {zahlwort(anzahl_titel, gross=False)} amtlichen Titeln")
        amtstitel = (f'<p class="amtstitel"><b>{vorsatz}</b> {e(lang_titel)}'
                     + ("" if anzahl_titel <= 1 else
                        " <i>Die Stadt benennt die Stationen dieses Vorhabens "
                        "unterschiedlich; hier steht der ausführlichste "
                        "Wortlaut. Die übrigen stehen in der Chronik.</i>")
                     + "</p>")

    t = [kopf(f"{vg['t']} · Chronik eines Vorhabens", hoch="../", hier="themen",
              beschreibung=f"Alle Stationen des Vorhabens „{vg['t']}\u201c in den "
                           f"Gremien der Stadt Bad Waldsee.",
              eigen=EIGEN),
         '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Vorhaben</p>
  <h1>{e(vg['t'])}</h1>
  <p class="lede">Der Weg dieses Vorhabens durch die Gremien — in der
  Reihenfolge, in der es behandelt wurde.</p>
  <div class="issueline">
    <span><b>Stationen</b> {len(stationen)}</span>
    <span><b>Zeitraum</b> {datum_lang(von)} bis {datum_lang(bis)}</span>
    <span><b>Vorlagen</b> {len(nummern)}</span>
    <span><b>Herkunft</b> regelbasiert gezählt</span>
  </div>
</header>

<p class="gremienzeile">{e(', '.join(gremien))}</p>
{amtstitel}
{worum_html(stationen, erklaert)}
{weg_html(weg, stationen, erklaert) if lohnt(weg, stationen) else ""}

<h2 class="abschnitt">Alle Stationen im Wortlaut</h2>
<p class="woherfrei">Beleg &middot; aus den Beschlussprotokollen</p>
<p class="hinweisfrei">Der Wortlaut stammt aus den Beschlussprotokollen, die
Abstimmungsergebnisse aus der Zeile „Ergebnis der Beschlussfassung“.
Nichtöffentliche Beratungen sind nicht enthalten.</p>

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
