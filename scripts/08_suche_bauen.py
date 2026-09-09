#!/usr/bin/env python3
"""Schritt 8 — die durchsuchbare Vorgangsübersicht erzeugen.

Bisher musste man wissen, in welcher Woche etwas verhandelt wurde. Diese Seite
dreht das um: Man sucht nach einem Stichwort und bekommt den Vorgang mit seinem
gesamten Weg durch die Gremien.

Denn ein Bauleitplanverfahren erscheint nicht einmal, sondern fünf- bis achtmal —
Aufstellung, Entwurf, Auslegung, Abwägung, Satzung, oft in mehreren Gremien. Erst
diese Abfolge macht sichtbar, wie eine Entscheidung zustande gekommen ist.

Der Suchindex wird in die Seite hineingeschrieben statt nachgeladen: So
funktioniert sie auch, wenn man die Datei lokal öffnet, und es entsteht kein
weiterer Abruf.

Ergebnis: docs/suche.html

    uv run --with pypdf python scripts/08_suche_bauen.py [--stichtag JJJJ-MM-TT]
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
DOCS = WURZEL / "docs"

ERGEBNIS = re.compile(r"Ergebnis der Beschlussfassung\s*:?\s*(.{0,70})")
VORLAGE = re.compile(r"SV-\d+/\d{4}")
AUSZAEHLUNG = re.compile(
    r"\s*Ja-Stimme?n?\(?e?n?\)?\s*(\d+)\s*Nein-Stimme?n?\(?e?n?\)?\s*(\d+)\s*"
    r"Enthaltung(?:en|\(en\))?\s*(\d+)")

KURZ = {
    "Gemeinderat": "GR",
    "Verwaltungsausschuss": "VA",
    "Gemeinsamer Ausschuss der Vereinbarten Verwaltungsgemeinschaft "
    "Bad Waldsee-Bergatreute": "GA",
}

# Die Gremiumsnamen sind beim Einlesen am ersten Komma abgeschnitten. Aus
# "Ausschuss für Umwelt, Technik und Nachhaltigkeit" wird "Ausschuss für Umwelt".
# Deshalb wird ueber den Anfang verglichen, nicht ueber Gleichheit.
PRAEFIXE = (
    ("Ausschuss für Umwelt", "AUT"),
    ("Ausschuss für Technik", "AUT"),
    ("Gemeinsamer Ausschuss", "GA"),
    ("Ortschaftsrat", "OR"),
    ("Arbeitskreis", "AK"),
    ("Kulturbeirat", "KB"),
    ("Baumkommission", "BK"),
)


# Viele Titel nennen das Vorhaben in Anfuehrungszeichen: Bebauungsplan
# "Lohbuehl I - Erweiterung". Ein Verfahren durchlaeuft mehrere Vorlagen —
# Aufstellung, Entwurf, Abwaegung, Satzung — mit jeweils eigener Nummer. Erst
# ueber den Namen laesst es sich als ein Vorgang zusammenfuehren.
VORHABEN = re.compile(r'[„"]([^„""]{4,70})["“]')


def vorhaben(titel: str) -> str | None:
    treffer = VORHABEN.search(titel)
    if not treffer:
        return None
    name = treffer.group(1).strip(' ,.-')
    # Zu allgemein, um als Klammer zu taugen
    if len(name) < 4 or name.lower() in ("feuerwehr", "wohnen", "plex"):
        return None
    return name


def vergleichsform(name: str) -> str:
    """Schreibvarianten zusammenfuehren: „Drei-Eichen VI“ und „Drei Eichen VI“."""
    return re.sub(r"[^a-z0-9]", "", name.lower()
                  .replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                  .replace("ß", "ss"))


def kuerzel(name: str) -> str:
    if name in KURZ:
        return KURZ[name]
    for anfang, kurz in PRAEFIXE:
        if name.startswith(anfang):
            return kurz
    return "—"


def dateiname(titel: str) -> str:
    name = re.sub(r",.*", "", titel)
    name = re.sub(r"[^A-Za-zÄÖÜäöüß0-9]+", "-", name).strip("-")
    return name[:48]


def pdf_text(pfad: Path) -> str:
    try:
        roh = "\n".join(s.extract_text() or "" for s in PdfReader(pfad).pages)
    except Exception:  # noqa: BLE001
        return ""
    return re.sub(r"[­\s]+", " ", roh)


def beschluesse_je_sitzung(text: str) -> dict[str, list[str]]:
    """Vorlagennummer -> alle Abstimmungsergebnisse in ihrer Reihenfolge.

    Eine Vorlage kann in derselben Sitzung mehrfach abgestimmt werden: Erst wird
    ueber einen Aenderungsantrag entschieden, dann ueber den Beschluss. Genau
    diese Faelle sind die aufschlussreichsten — beim Gymnasium fiel die
    Verwaltungsvariante mit 9 : 18 durch, bevor die guenstigere mit 20 : 3 : 4
    angenommen wurde. Wer nur das letzte Ergebnis behaelt, verliert die Ablehnung.
    """
    ergebnisse: dict[str, list[str]] = collections.defaultdict(list)
    for treffer in ERGEBNIS.finditer(text):
        roh = treffer.group(1)
        zahlen = AUSZAEHLUNG.match(roh)
        if zahlen:
            wert = "{} : {} : {}".format(*zahlen.groups())
        elif re.match(r"\s*[Ee]instimmig", roh):
            wert = "einstimmig"
        else:
            continue
        vorher = VORLAGE.findall(text[:treffer.start()])
        if vorher:
            ergebnisse[vorher[-1]].append(wert)
    return dict(ergebnisse)


def vorgaenge_sammeln(stichtag: str) -> list[dict]:
    quelle = DATEN / "sitzungen.json"
    if not quelle.exists():
        raise SystemExit(
            "data/sitzungen.json fehlt — bitte zuerst Schritt 01 ausführen.")
    sitzungen = json.loads(quelle.read_text(encoding="utf-8"))

    karte = DATEN / "topmap.json"
    if not karte.exists():
        raise SystemExit(
            "data/topmap.json fehlt — bitte zuerst Schritt 01 ausführen:\n"
            "  uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py")
    punkte = [p for p in json.loads(karte.read_text(encoding="utf-8"))
              if p["datum"] <= stichtag]

    # Abstimmungsergebnisse einsammeln. Die Protokolle werden der jeweiligen
    # Sitzung ueber den Dateinamen zugeordnet — sonst vermischen sich Ergebnisse
    # zweier Gremien, die am selben Tag tagen.
    protokolle: dict[str, list[Path]] = {}
    for pdf in sorted((DATEN / "protokolle").glob("*.pdf")):
        protokolle.setdefault(pdf.name[:10], []).append(pdf)

    ergebnisse: dict[str, dict[str, list[str]]] = collections.defaultdict(dict)
    for s in sitzungen:
        datum = s["start"][:10]
        if datum > stichtag or not s["protokolle"]:
            continue
        erwartet = f"{datum}_{dateiname(s['titel'])}"
        for pdf in protokolle.get(datum, []):
            if pdf.stem != erwartet and not pdf.stem.startswith(erwartet + "_"):
                continue
            for vorlage, werte in beschluesse_je_sitzung(pdf_text(pdf)).items():
                ergebnisse[datum].setdefault(vorlage, []).extend(werte)

    # Punkte zu Vorgängen bündeln: bevorzugt über den Namen des Vorhabens,
    # sonst über die Vorlagennummer, sonst als Einzelpunkt.
    namen: dict[str, str] = {}          # Vergleichsform -> schönster Name
    for p in punkte:
        name = vorhaben(p["titel"])
        if name:
            v = vergleichsform(name)
            if v not in namen or len(name) > len(namen[v]):
                namen[v] = name

    gebuendelt: dict[str, list[dict]] = collections.defaultdict(list)
    for p in punkte:
        name = vorhaben(p["titel"])
        if name:
            schluessel = "@" + vergleichsform(name)
        elif p["vorlage"]:
            schluessel = p["vorlage"]
        else:
            schluessel = f"__{p['datum']}_{p['top']}"
        gebuendelt[schluessel].append(p)

    vorgaenge = []
    for schluessel, teile in gebuendelt.items():
        teile.sort(key=lambda p: (p["datum"], int(p["top"]) if p["top"].isdigit() else 99))
        stationen = []
        for p in teile:
            werte = ergebnisse.get(p["datum"], {}).get(p["vorlage"] or "", [])
            stationen.append({
                "d": p["datum"],
                "g": kuerzel(p["gremium"]),
                "gl": p["gremium"],
                "v": p["vorlage"] or "",
                "e": " → ".join(werte),
                "t": p["titel"],
            })
        if schluessel.startswith("@"):
            name = namen[schluessel[1:]]
            titel = name
            nummern = sorted({p["vorlage"] for p in teile if p["vorlage"]})
        else:
            titel = max((p["titel"] for p in teile), key=len)
            nummern = sorted({p["vorlage"] for p in teile if p["vorlage"]})
        vorgaenge.append({
            "v": " · ".join(nummern),
            "t": titel,
            "u": max((p["titel"] for p in teile), key=len) if schluessel.startswith("@") else "",
            "s": stationen,
            "letzte": teile[-1]["datum"],
            "strittig": any(st["e"] and st["e"] != "einstimmig" and
                            not st["e"].endswith(": 0 : 0") for st in stationen),
        })

    vorgaenge.sort(key=lambda v: v["letzte"], reverse=True)
    return vorgaenge


def bauen(vorgaenge: list[dict], stichtag: str) -> str:
    stil = (WURZEL / "scripts" / "ausgabe.css").read_text(encoding="utf-8")
    schriften = (WURZEL / "scripts" / "schriften.css").read_text(
        encoding="utf-8").replace("{PFAD}", "./")
    # "</script>" im Titel wuerde das Element vorzeitig beenden und die ganze
    # Seite lahmlegen. Die Titel stammen aus fremdem HTML — also absichern.
    index = (json.dumps(vorgaenge, ensure_ascii=False, separators=(",", ":"))
             .replace("</", "<\\/"))
    mit_beschluss = sum(1 for v in vorgaenge if any(s["e"] for s in v["s"]))
    mehrstufig = sum(1 for v in vorgaenge if len(v["s"]) > 1)

    return f"""<meta charset="utf-8">
<title>Vorgänge durchsuchen</title>
<style>{schriften}</style>
<style>{stil}</style>
<style>
.suchfeld{{
  display:flex;gap:10px;flex-wrap:wrap;margin:28px 0 0;
}}
.suchfeld input{{
  flex:1 1 320px;background:var(--surface);color:var(--ink);
  border:1px solid var(--rule);border-left:3px solid var(--s1);
  padding:15px 18px;font-family:"IBM Plex Serif",Georgia,serif;font-size:18px;
}}
.suchfeld input:focus{{outline:2px solid var(--s1);outline-offset:2px}}
.suchfeld input::placeholder{{color:var(--muted)}}
.filter{{
  display:flex;gap:8px 18px;flex-wrap:wrap;margin:14px 0 0;
  font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-2);
}}
.filter label{{cursor:pointer;display:flex;align-items:center;gap:7px}}
.trefferzahl{{
  font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin:22px 0 0;
}}
.vorgang{{
  padding:20px 0;border-bottom:1px solid var(--rule);
}}
.vorgang h3{{
  font-family:Archivo,sans-serif;font-weight:600;font-size:17.5px;line-height:1.35;
  margin:0 0 4px;color:var(--ink);
}}
.vorgang .nr{{
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.05em;
  color:var(--muted);
}}
.achse{{
  display:flex;flex-wrap:wrap;gap:0;margin:12px 0 0;
}}
.station{{
  display:flex;align-items:baseline;gap:9px;
  padding:6px 14px 6px 0;position:relative;
}}
.station:not(:last-child)::after{{
  content:"→";color:var(--muted);opacity:.5;padding-left:14px;
}}
.station .dat{{
  font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink-2);
  font-variant-numeric:tabular-nums;white-space:nowrap;
}}
.station .grem{{
  font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.08em;
  color:var(--muted);border:1px solid var(--rule);padding:1px 5px;
}}
.station .erg{{
  font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.04em;
  color:var(--s1);white-space:nowrap;
}}
.station .erg.split{{color:var(--flag)}}
.station .svnr{{
  font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);
  opacity:.75;white-space:nowrap;
}}
.vorgang .untertitel{{color:var(--muted);font-family:"IBM Plex Serif",serif;font-size:13px}}
mark{{background:rgba(57,135,229,.25);color:var(--ink);padding:0 2px}}
.leer{{padding:40px 0;color:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:14px}}
.ohnejs{{
  margin:28px 0;padding:20px 22px;background:var(--flag-bg);
  border-left:3px solid var(--flag);
}}
.ohnejs p{{margin:0}}
</style>

<div class="brandbar"><div class="wrap">
  <span>Created by <a href="https://amannlabs.eu" rel="noopener"><b>AmannLabs.eu</b></a></span>
  <nav aria-label="Bereiche">
    <a href="./index.html">Startseite</a>
    <span aria-hidden="true">/</span>
    <a href="./suche.html" aria-current="page">Suche</a>
    <span aria-hidden="true">/</span>
    <a href="./ausgaben/index.html">Archiv</a>
  </nav>
  <span class="disclaimer">Alle Angaben und Insights ohne Gew&auml;hr</span>
</div></div>

<div class="wrap">
<header class="masthead">
  <h1>Vorg&auml;nge</h1>
  <p class="claim">Jeder Vorgang mit seinem Weg durch die Gremien — von der ersten
  Beratung bis zum Beschluss.</p>
  <div class="issueline">
    <span><b>Vorg&auml;nge</b> {len(vorgaenge)}</span>
    <span><b>mit Beschluss</b> {mit_beschluss}</span>
    <span><b>mehrstufig</b> {mehrstufig}</span>
    <span><b>Stand</b> {stichtag[8:10]}.{stichtag[5:7]}.{stichtag[:4]}</span>
  </div>

  <div class="suchfeld">
    <input type="search" id="q" placeholder="Suchen — etwa Kindergarten, Windenergie, Steinstra&szlig;e, SV-104/2026"
           autocomplete="off" aria-label="Vorg&auml;nge durchsuchen">
  </div>
  <div class="filter">
    <label><input type="checkbox" id="f-beschluss"> nur mit Beschluss</label>
    <label><input type="checkbox" id="f-strittig"> nur nicht einstimmig</label>
    <label><input type="checkbox" id="f-mehr"> nur mehrstufige Vorg&auml;nge</label>
  </div>

  <noscript>
    <div class="ohnejs">
      <p><b>Die Suche braucht JavaScript.</b> Ohne JavaScript lassen sich dieselben
      Daten als Tabelle auswerten: <a class="doc" href="https://github.com/dominikamann/ratsakten-bad-waldsee/blob/main/data/csv/tagesordnungspunkte.csv">tagesordnungspunkte.csv</a>
      und <a class="doc" href="https://github.com/dominikamann/ratsakten-bad-waldsee/blob/main/data/csv/beschluesse.csv">beschluesse.csv</a> —
      beide lassen sich in Excel oder LibreOffice &ouml;ffnen und filtern.</p>
    </div>
  </noscript>
</header>

<p class="trefferzahl" id="zahl"></p>
<div id="treffer"></div>

<section class="kolophon">
  <h3>Was hier steht</h3>
  <p>Ein Vorgang ist alles, was unter derselben Vorlagennummer verhandelt wurde.
  Die Kette zeigt jede Station: Datum, Gremium und — wo ein Beschlussprotokoll
  vorliegt — das Abstimmungsergebnis. Die Schreibweise <span class="mono">25 : 0 : 1</span>
  steht f&uuml;r Ja : Nein : Enthaltungen.</p>
  <p>Punkte ohne Vorlagennummer erscheinen als einzelne Station. Gremien ohne
  ver&ouml;ffentlichte Tagesordnung — die Ortschaftsr&auml;te — fehlen hier
  vollst&auml;ndig, weil es von ihnen nichts zu indizieren gibt.</p>
  <p class="note">Mit der Vorlagennummer l&auml;sst sich jeder Vorgang im
  <a class="doc" href="https://ris.bad-waldsee.de/vorlagen" rel="noopener">Ratsinformationssystem</a>
  unter „Vorlagen“ auffinden.</p>
</section>
</div>

<footer><div class="wrap">
  <p class="brand">Created by <a href="https://amannlabs.eu" rel="noopener">AmannLabs.eu</a></p>
  <p>Alle Angaben und Insights ohne Gew&auml;hr &middot; Stand {stichtag}</p>
</div></footer>

<script id="daten" type="application/json">{index}</script>
<script>
(function(){{
  "use strict";
  var daten = JSON.parse(document.getElementById("daten").textContent);
  var feld  = document.getElementById("q");
  var liste = document.getElementById("treffer");
  var zahl  = document.getElementById("zahl");
  var fB = document.getElementById("f-beschluss");
  var fS = document.getElementById("f-strittig");
  var fM = document.getElementById("f-mehr");

  /* Umlaute und Grossschreibung sollen beim Suchen keine Rolle spielen.
     ä→ae verlaengert die Zeichenkette. Fuer die Hervorhebung brauchen wir
     deshalb zusaetzlich eine Zuordnung: welche Stelle im normalisierten Text
     gehoert zu welcher Stelle im Original? Ohne sie verrutschen die Markierungen
     um ein Zeichen je Umlaut davor. */
  var ERSATZ = {{ "ä":"ae", "ö":"oe", "ü":"ue", "ß":"ss",
                 "„":'"', "“":'"', "»":'"', "«":'"' }};

  function normal(t){{
    var aus = "";
    var lower = t.toLowerCase();
    for(var i=0;i<lower.length;i++) aus += (ERSATZ[lower[i]] || lower[i]);
    return aus;
  }}

  /* Wie normal(), liefert zusaetzlich je Zeichen der Ausgabe den Index im Original. */
  function normalMitKarte(t){{
    var aus = "", karte = [];
    var lower = t.toLowerCase();
    for(var i=0;i<lower.length;i++){{
      var e = ERSATZ[lower[i]] || lower[i];
      for(var j=0;j<e.length;j++) karte.push(i);
      aus += e;
    }}
    karte.push(lower.length);   // Endmarke
    return [aus, karte];
  }}
  daten.forEach(function(v){{ v._s = normal(v.t + " " + v.v + " " + (v.u||"") + " " + v.s.map(function(s){{return s.t;}}).join(" ")); }});

  function hervorheben(text, woerter){{
    var e = document.createElement("span");
    if(!woerter.length){{ e.textContent = text; return e; }}
    var rest = text, i = 0;
    var muster = new RegExp("(" + woerter.map(function(w){{
      return w.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
    }}).join("|") + ")", "gi");
    // Auf der normalisierten Fassung suchen, ueber die Karte im Original markieren
    var paar = normalMitKarte(text), norm = paar[0], karte = paar[1], treffer = [], m;
    while((m = muster.exec(norm)) !== null){{
      treffer.push([karte[m.index], karte[m.index + m[0].length]]);
      if(m.index === muster.lastIndex) muster.lastIndex++;
    }}
    treffer.forEach(function(t){{
      if(t[0] > i) e.appendChild(document.createTextNode(text.slice(i, t[0])));
      var mk = document.createElement("mark");
      mk.textContent = text.slice(t[0], t[1]);
      e.appendChild(mk); i = t[1];
    }});
    e.appendChild(document.createTextNode(text.slice(i)));
    return e;
  }}

  function zeichne(){{
    var roh = feld.value.trim();
    var woerter = normal(roh).split(/\\s+/).filter(Boolean);
    var treffer = daten.filter(function(v){{
      if(fB.checked && !v.s.some(function(s){{ return s.e; }})) return false;
      if(fS.checked && !v.strittig) return false;
      if(fM.checked && v.s.length < 2) return false;
      return woerter.every(function(w){{ return v._s.indexOf(w) > -1; }});
    }});

    zahl.textContent = treffer.length === 0 ? "Kein Treffer"
      : treffer.length + (treffer.length === 1 ? " Vorgang" : " Vorgänge")
        + (roh ? " für „" + roh + "“" : "");

    liste.textContent = "";
    if(!treffer.length){{
      var l = document.createElement("p");
      l.className = "leer";
      l.textContent = "Nichts gefunden. Andere Schreibweise versuchen — die Titel "
        + "stammen wörtlich aus den Tagesordnungen.";
      liste.appendChild(l); return;
    }}

    var zeigen = treffer.slice(0, 300);
    zeigen.forEach(function(v){{
      var d = document.createElement("article");
      d.className = "vorgang";
      var h = document.createElement("h3");
      h.appendChild(hervorheben(v.t, woerter));
      d.appendChild(h);
      var teile = v.v ? v.v.split(" · ") : [];
      var nr = document.createElement("p");
      nr.className = "nr";
      if(teile.length > 4){{
        nr.textContent = teile.length + " Vorlagen · " + v.s.length + " Stationen";
      }} else if(teile.length){{
        nr.appendChild(hervorheben(v.v, woerter));
      }}
      if(v.u && v.u !== v.t){{
        var u = document.createElement("span");
        u.className = "untertitel";
        u.textContent = (teile.length ? " — " : "") + v.u;
        nr.appendChild(u);
      }}
      if(nr.textContent) d.appendChild(nr);
      var achse = document.createElement("div");
      achse.className = "achse";
      v.s.forEach(function(s){{
        var st = document.createElement("div");
        st.className = "station";
        var dat = document.createElement("span");
        dat.className = "dat";
        dat.textContent = s.d.slice(8,10) + "." + s.d.slice(5,7) + "." + s.d.slice(0,4);
        st.appendChild(dat);
        var g = document.createElement("span");
        g.className = "grem"; g.textContent = s.g; g.title = s.gl;
        st.appendChild(g);
        if(s.v){{
          var nr = document.createElement("span");
          nr.className = "svnr"; nr.textContent = s.v; nr.title = s.t;
          st.appendChild(nr);
        }}
        if(s.e){{
          var e = document.createElement("span");
          e.className = "erg" + (s.e !== "einstimmig" && !/: 0 : 0$/.test(s.e) ? " split" : "");
          e.textContent = s.e;
          st.appendChild(e);
        }}
        achse.appendChild(st);
      }});
      d.appendChild(achse);
      liste.appendChild(d);
    }});

    if(treffer.length > zeigen.length){{
      var mehr = document.createElement("p");
      mehr.className = "leer";
      mehr.textContent = "… und " + (treffer.length - zeigen.length)
        + " weitere. Suche eingrenzen.";
      liste.appendChild(mehr);
    }}
  }}

  feld.addEventListener("input", zeichne);
  [fB, fS, fM].forEach(function(f){{ f.addEventListener("change", zeichne); }});
  zeichne();
}})();
</script>
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stichtag", default=dt.date.today().isoformat())
    args = p.parse_args()

    vorgaenge = vorgaenge_sammeln(args.stichtag)
    DOCS.mkdir(exist_ok=True)
    ziel = DOCS / "suche.html"
    ziel.write_text(bauen(vorgaenge, args.stichtag), encoding="utf-8")

    mehrstufig = sum(1 for v in vorgaenge if len(v["s"]) > 1)
    print(f"  {ziel.relative_to(WURZEL)}  —  {len(vorgaenge)} Vorgänge, "
          f"{mehrstufig} mehrstufig, {ziel.stat().st_size / 1024:.0f} KB")
    if vorgaenge:
        laengste = max(vorgaenge, key=lambda v: len(v["s"]))
        print(f"  längster Vorgang: {len(laengste['s'])} Stationen — "
              f"{laengste['v']} {laengste['t'][:60]}")
    else:
        print("  Achtung: kein Vorgang bis zum Stichtag — die Seite bleibt leer.")

    # Kennzahlen fuer die Startseite, damit sie nicht aus dem HTML gelesen
    # werden muessen (Befund aus dem Code-Review).
    (DATEN / "suche.json").write_text(json.dumps({
        "vorgaenge": len(vorgaenge),
        "mehrstufig": mehrstufig,
        "stichtag": args.stichtag,
    }, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
