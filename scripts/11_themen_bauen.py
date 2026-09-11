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

from seite import fuss, kopf
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
ol.chronik{list-style:none;margin:26px 0 0;padding:0;counter-reset:station}
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


def station_html(st: dict) -> str:
    dok = "".join(
        f'<a class="doc" href="{e(d["url"])}" target="_blank" '
        f'rel="noopener noreferrer">{e(d["titel"])}</a>'
        for d in st.get("dok", []))
    unterlagen = f'<div class="unterlagen">{dok}</div>' if dok else ""
    wortlaut = f'<p class="wortlaut">{e(st["w"])}</p>' if st.get("w") else ""
    ergebnis = (f'<span class="erg">{e(st["e"])}</span>'
                if st.get("e") else '<span class="erg">ohne Abstimmung</span>')
    ausgabe = st.get("a") or ""
    if ausgabe.startswith("./"):
        ausgabe = "../" + ausgabe[2:]
    verweis = (f'<p class="quelle"><a href="{e(ausgabe)}">In der Wochenausgabe nachlesen</a></p>'
               if ausgabe else "")
    return f"""  <li>
    <p class="wann">{datum_lang(st['d'])} &middot; {e(st['gl'])}
      {f'<span class="sv">{e(st["v"])}</span>' if st.get("v") else ""}</p>
    <p class="sache">{e(st['t'])}</p>
    {wortlaut}
    {ergebnis}
    {unterlagen}
    {verweis}
  </li>"""


def seite_bauen(vg: dict) -> str:
    stationen = sorted(vg["s"], key=lambda s: s["d"])
    von, bis = stationen[0]["d"], stationen[-1]["d"]
    gremien = sorted({s["gl"] for s in stationen})
    nummern = [n for n in vg["v"].split(" · ") if n]
    # Der amtliche Titel ist oft ein ganzer Absatz und taugt nicht als Vorspann.
    # Er gehoert trotzdem auf die Seite — wer im Ratsinformationssystem sucht,
    # findet den Vorgang nur unter diesem Wortlaut.
    lang_titel = (vg.get("u") or "").strip()
    amtstitel = (f'<p class="amtstitel"><b>Amtlicher Titel</b> {e(lang_titel)}</p>'
                 if lang_titel and lang_titel != vg["t"] else "")

    t = [kopf(f"{vg['t']} · Chronik eines Vorhabens", hoch="../", hier="themen",
              beschreibung=f"Alle Stationen des Vorhabens „{vg['t']}\u201c in den "
                           f"Gremien der Stadt Bad Waldsee.",
              eigen=EIGEN),
         '<div class="wrap">']
    t.append(f"""
<header>
  <p class="eyebrow">Vorhaben</p>
  <h1>{e(vg['t'])}</h1>
  <p class="lede">Der Weg dieses Vorhabens durch die Gremien — in der Reihenfolge,
  in der es behandelt wurde, mit dem beschlossenen Wortlaut und dem
  Abstimmungsergebnis jeder Station.</p>
  <div class="issueline">
    <span><b>Stationen</b> {len(stationen)}</span>
    <span><b>Zeitraum</b> {datum_lang(von)} bis {datum_lang(bis)}</span>
    <span><b>Vorlagen</b> {len(nummern)}</span>
    <span><b>Herkunft</b> regelbasiert gezählt</span>
  </div>
</header>

<p class="gremienzeile">{e(', '.join(gremien))}</p>
{amtstitel}

<p>Der Wortlaut stammt aus den Beschlussprotokollen, die Abstimmungsergebnisse
aus der Zeile „Ergebnis der Beschlussfassung“. Nichtöffentliche Beratungen sind
nicht enthalten.</p>

<ol class="chronik">
{chr(10).join(station_html(s) for s in stationen)}
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
