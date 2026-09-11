# Ratsakten Bad Waldsee

**Ein Lernprojekt: Was passiert, wenn man öffentliche Gemeinderatsunterlagen maschinell auswertet?**

Kommunalpolitik ist öffentlich — aber sie ist nicht zugänglich. In Bad Waldsee liegen
Sitzungsvorlagen, Tagesordnungen und Beschlussprotokolle vollständig im Netz. Sie zu lesen
bedeutet trotzdem: sich durch ein Ratsinformationssystem klicken, PDFs einzeln öffnen,
Verwaltungsdeutsch entziffern und wissen, wonach man überhaupt sucht.

Dieses Repository probiert aus, ob sich daraus etwas Lesbares machen lässt: ein Report, der
zusammenfasst, was in drei Jahren Gremienarbeit tatsächlich entschieden wurde — mit Zahlen,
Quellenangabe und ohne Interpretation dessen, was nicht in den Akten steht.

> [!IMPORTANT]
> **Dies ist ein privates Lern- und Technologieprojekt. Für die Richtigkeit, Vollständigkeit und
> Aktualität der Informationen wird keine Gewähr übernommen.** Verbindlich ist ausschließlich
> das jeweilige Originaldokument der Stadt Bad Waldsee. Details im Abschnitt
> [Haftungsausschluss](#haftungsausschluss).

---

## Warum das Projekt existiert

Lokaljournalismus ist vielerorts zurückgegangen. Gleichzeitig sind kommunale Unterlagen
so vollständig online wie nie. Zwischen beidem klafft eine Lücke: Die Information ist
öffentlich, aber praktisch ungelesen — nicht weil sie geheim wäre, sondern weil niemand die
Zeit hat, Bebauungsplanverfahren und Gebührenkalkulationen durchzuarbeiten.

Was mich daran interessiert, ist die technische Frage:

- Wie gut lassen sich kommunale Ratsinformationssysteme maschinell erschließen?
- Wie viel Substanz steckt tatsächlich in den Dokumenten — und wie viel ist Formalie?
- Wo endet das, was aus Akten allein erkennbar ist?

Der erste Report beantwortet diese Fragen für **Bad Waldsee, Januar 2024 bis September 2026**.

## Was ausgewertet wurde

| Kennzahl | Wert |
|---|---|
| Erfasste Sitzungen | 166 |
| Tagesordnungspunkte | 616 |
| Sitzungsvorlagen | 300 |
| Dokumente | 625 |
| Ausgewertete Beschlussprotokolle | 72 |
| Ausgezählte Abstimmungen | 337 |
| Gremien | 12 |

**Zeitraum:** 01.01.2024 – 09.09.2026 (Stichtag). Bereits terminierte Sitzungen nach dem
Stichtag wurden ausgeschlossen, damit die Protokollquote nicht verzerrt wird.

## Der Report

➡️ **[Ratsanalyse 2024–2026](./docs/report/2026-09-09.html)** — die große Vollauswertung
➡️ **[Aktuelle Ausgabe, KW 37/2026](./docs/ausgaben/2026/kw37.html)** — die wöchentliche Aktenlage
➡️ **[Archiv](./docs/ausgaben/index.html)** — alle 89 Ausgaben der Jahrgänge 2024 bis 2026
➡️ **[Wer entscheidet was](./docs/gremien.html)** — wer in der Stadt wofür zuständig ist, mit Fundstellen
➡️ **[Themen](./docs/themen/index.html)** — 26 Vorhaben mit ihrem vollständigen Verlauf
➡️ **[Termine](./docs/termine.html#heute)** — alle Sitzungen, vergangene wie angekündigte
➡️ **[Vorgänge durchsuchen](./docs/suche.html)** — 506 Vorgänge mit ihrem Weg durch die Gremien
➡️ **[Erkenntnisse](./docs/befunde.html)** — alle 25 Erkenntnisse an einem Ort, eingehaltene wie kritische

Alle Dokumente unter `docs/` sind eigenständige HTML-Dateien ohne externe
Abhängigkeiten und **funktionieren ohne JavaScript** — auch in der iOS-Dateivorschau,
in GitHub-Vorschauen und im Ausdruck.

Inhalt:

| Kapitel | Thema |
|---|---|
| 00 | Datengrundlage und Methode |
| 01 | Transparenz — wo Beschlüsse nachlesbar sind, und wo nicht |
| 02 | Themen — womit sich die Gremien tatsächlich befassen |
| 03 | Entscheidungsverhalten — wie oft einstimmig entschieden wird |
| 04 | Finanzen — Haushaltsentwicklung und Jahresabschlüsse |
| 05 | Die 50 auffälligsten Tagesordnungspunkte |
| 06 | Zehn Punkte, die Fragen aufwerfen |
| 07 | Was der Report nicht kann |
| 08 | Quellen |

## Die Seiten im Browser ansehen

Wer hier auf eine `.html`-Datei klickt, sieht **Quelltext statt Seite**. Das ist
kein Fehler: GitHub liefert HTML absichtlich als reinen Text aus, damit niemand
fremden Programmcode auf github.com ausführen lassen kann.

Um die Seiten fertig gestaltet zu sehen, gibt es einen kostenlosen Umweg. Der
Dienst **githack** holt die Datei aus dem Repository und liefert sie so aus, dass
der Browser sie als Seite darstellt. Man muss dafür nichts installieren und sich
nirgends anmelden — Link anklicken genügt:

* **[Startseite](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/index.html)**
* **[Ratsanalyse 2024–2026](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/report/2026-09-09.html)**
* **[Archiv aller Ausgaben](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/ausgaben/index.html)**
* **[Wer entscheidet was](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/gremien.html)**
* **[Themen](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/themen/index.html)**
* **[Termine](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/termine.html)**
* **[Vorgänge durchsuchen](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/suche.html)**
* **[Erkenntnisse](https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/befunde.html)**

Von der Startseite aus funktioniert alles Weitere ganz normal durch Anklicken.

<details>
<summary>Wie man sich so einen Link selbst baut</summary>

Man nimmt die normale GitHub-Adresse einer Datei und ersetzt den Anfang:

```
aus   https://github.com/dominikamann/ratsakten-bad-waldsee/blob/main/docs/index.html
wird  https://raw.githack.com/dominikamann/ratsakten-bad-waldsee/main/docs/index.html
```

Also `github.com` durch `raw.githack.com` ersetzen und das `/blob` herausnehmen.

</details>

**Was man dazu wissen sollte:** githack ist ein fremder Dienst. Er ist seit Jahren
verfügbar und kostenlos, aber niemand garantiert das. Für einen dauerhaften
Auftritt wäre GitHub Pages der richtige Weg — dann hätten die Seiten eine feste
Adresse. Zum Anschauen und Weitergeben reicht githack vollkommen.


## Datenquellen

Ausschließlich öffentlich zugängliche Dokumente. Es wurden **keine Zugangsbeschränkungen
umgangen**, keine Anmeldung verwendet und keine nichtöffentlichen Unterlagen ausgewertet.

- [Ratsinformationssystem der Stadt Bad Waldsee](https://ris.bad-waldsee.de/) — Sitzungen,
  Vorlagen, Anlagen, Beschlussprotokolle
- [Öffentliche Bekanntmachungen der Stadt Bad Waldsee](https://www.bad-waldsee.de/buerger/de/rathaus-service/aktuelles-bekanntmachungen/oeffentliche-bekanntmachungen)

Amtliche Werke sind nach § 5 UrhG gemeinfrei. Die Rechte an den zugrunde liegenden
Dokumenten liegen bei der Stadt Bad Waldsee.

## Wie die Auswertung funktioniert

1. **Sitzungstermine** über die Kalender-Schnittstelle des Ratsinformationssystems abrufen
2. **Sitzungsseiten** parsen: Tagesordnungspunkte, Vorlagennummern, verlinkte Dokumente
3. **PDFs laden** und den Text extrahieren
4. **Auswerten**: Abstimmungsergebnisse aus der Zeile „Ergebnis der Beschlussfassung“,
   Geldbeträge und Jahresabschlusszahlen aus den Beschlusstexten
5. **Report erzeugen** als statische HTML-Seite

Die Abfragen sind bewusst langsam gehalten (Pause zwischen den Aufrufen), um die Server
der Stadt nicht zu belasten.

## Vorgänge nachverfolgen

Ein Bauleitplanverfahren erscheint nicht einmal auf einer Tagesordnung, sondern
über Jahre hinweg immer wieder — mit jeweils eigener Vorlagennummer für
Aufstellung, Entwurf, Abwägung und Satzung. Aus den Unterlagen allein ist dieser
Zusammenhang nicht zu sehen.

Die [Vorgangssuche](./docs/suche.html) führt zusammen, was unter demselben
benannten Vorhaben verhandelt wurde, und zeigt die Kette:

> **Drei Eichen VI** — 13 Vorlagen, 19 Stationen
> 26.02.2024 GR *18 : 1 : 5* → … → 03.02.2026 GA *einstimmig*

Gesucht wird über Stichwort oder Vorlagennummer; filtern lässt sich nach
Vorgängen mit Beschluss, nicht einstimmigen Entscheidungen und mehrstufigen
Verfahren. Zusätzlich lässt sich nach der Höhe des im Beschluss genannten Betrags
filtern — 21 Vorgänge nennen eine Million Euro oder mehr. Jeder Treffer und jede
Station führt zur Ausgabe der jeweiligen Woche.

Wo Unterlagen am Tagesordnungspunkt hängen — Sitzungsvorlage, Planteil,
Umweltbericht —, sind sie **verlinkt und öffnen in einem neuen Tab**. Die
Sitzungsvorlage enthält den Abschnitt „Zum Sachverhalt": dort steht, warum die
Verwaltung etwas vorschlägt, und das ist oft aufschlussreicher als der Beschluss.
Diese Begründung wird **nicht wiedergegeben** — wer sie lesen will, liest sie im
Original. 625 Dokumente sind so erreichbar.

Unter jeder Station steht der **beschlossene Wortlaut** — was das Gremium
tatsächlich gefasst hat. Die Überschrift nennt nur den Verwaltungsvorgang; erst
der Beschlusstext sagt, worum es geht. Aus „Sanierungsgebiet Altstadt III –
3. Änderungssatzung" wird so: *„Die Durchführungsfrist für das Erweiterungsgebiet
wird bis zum 30.04.2028 festgelegt."* Angezeigt werden rund 340 Zeichen,
durchsucht wird der vollständige Beschluss.

Mitdurchsucht werden auch die redaktionellen **Einordnungen**. Sie verbinden
mehrere Vorgänge über die Zeit — etwa den Befund, dass Bad Waldsee binnen elf
Monaten dreimal in Folge das Einvernehmen für Windkraft versagt hat. Aus den
Einzelpunkten geht das nicht hervor. Solche Treffer sind als **KI-Deutung**
gekennzeichnet. Der Suchindex steht in der Seite selbst — sie funktioniert also auch
lokal geöffnet und ruft nichts nach.

## Erkenntnisse

Die Zahlen sind auszählbar. Was darüber hinausgeht — dass eine Enthaltung
ausgerechnet bei dem Verfahren fiel, gegen das eine Fachbehörde Bedenken hatte,
oder dass dreimal in Folge dasselbe abgelehnt wurde — entsteht erst durch
Vergleich über die Zeit.

Solche Aussagen lagen verstreut in einzelnen Wochenausgaben und Kapiteln. Die
Seite [Erkenntnisse](./docs/befunde.html) sammelt sie — sortiert nicht nach gut
und schlecht, sondern danach, woher die Erkenntnis stammt: fünf regelbasiert
ausgezählte Einträge zum Regelfall, von dem sich alles Weitere abhebt,
acht Beobachtungen, vier Erkenntnisse aus der Gesamtauswertung und acht
Einordnungen aus den Wochenausgaben. Der erste Abschnitt ist **regelbasiert**,
alles Weitere **KI-Deutung** — jeder Eintrag mit Weg zur Quelle.

## Selbst nachrechnen

Unter `data/csv/` liegen drei Tabellen, die sich direkt in Excel, LibreOffice
oder Numbers öffnen lassen — Semikolon als Trennzeichen, damit kein Importdialog
nötig ist:

| Datei | Zeilen | Inhalt |
|---|---|---|
| [`sitzungen.csv`](./data/csv/sitzungen.csv) | 166 | Datum, Gremium, Kalenderwoche, Zahl der Tagesordnungspunkte, ob ein Protokoll vorliegt |
| [`tagesordnungspunkte.csv`](./data/csv/tagesordnungspunkte.csv) | 616 | jeder Punkt mit Datum, Gremium, Nummer, Titel und Vorlagennummer |
| [`beschluesse.csv`](./data/csv/beschluesse.csv) | 337 | jede Abstimmung mit Vorlagennummer, Titel, Stimmenverhältnis und Betrag |

Damit lässt sich jede Zahl des Reports ohne Programmierkenntnisse überprüfen.
Beispiel: In `beschluesse.csv` nach der Spalte `einstimmig` filtern — es bleiben
63 Zeilen übrig, genau die im Report genannten nicht einstimmigen Beschlüsse. Oder
nach `betrag_euro` sortieren: 36 Beschlüsse nennen eine Summe ab 250.000 Euro.

**Beträge sind Fundstellen, keine Kostenangaben.** Die Spalte enthält den größten
im Beschlusstext genannten Betrag. Das kann der Preis eines Vorhabens sein, aber
ebenso ein Haushaltsansatz — bei der Haushaltssatzung 2025 stehen dort 63,6 Mio.
Euro, der Ertrag der gesamten Stadt. Maßgeblich ist der Beschlusstext.

Die Tabellen enthalten bewusst keine Dokument-Links: Die URLs des
Ratsinformationssystems sind nicht dauerhaft gültig. Stabile Kennung ist die
Vorlagennummer.

## Am Telefon lesbar

Alle Seiten tragen Doctype, Sprachangabe und Viewport und sind für schmale
Bildschirme eingerichtet: Die Zeitachse eines Vorgangs läuft am Rechner waagerecht
mit Pfeilen, auf dem Telefon senkrecht mit Zeitstrahl. Beschlussergebnisse rücken
unter die Sache statt daneben, Suchfeld und Filter stehen untereinander mit
größeren Tippzielen.

Die Prüfung kontrolliert den Seitenkopf bei jedem Push — ohne Viewport-Angabe
rendert ein Telefon auf rund 980 Pixel Breite und skaliert herunter.

## Woher eine Aussage stammt

Jede Aussage ist einer von drei Arten zugeordnet:

| Marke | Bedeutung | Belastbarkeit |
|---|---|---|
| **Beleg** | wörtlich aus einem Dokument | am Original nachprüfbar |
| **Regelbasiert** | maschinell gezählt, ohne Bewertung | durch erneutes Ausführen reproduzierbar |
| **KI-Deutung** | maschinell erzeugte Einordnung — Auswahl, Verknüpfung, Gewichtung | **nicht redaktionell geprüft** |

Die Kapitel 01 bis 04 des Reports, die Rubrik „Auffälligkeiten“ der Ausgaben und
der Abschnitt „Der Regelfall“ sind
regelbasiert. Die Erkenntnisse aus der Gesamtauswertung, die 50 Fundstücke, die acht
Beobachtungen und die wöchentlichen Einordnungen sind **KI-Deutungen**: Ihre
Zahlen sind belegt, die daraus gezogene Schlussfolgerung ist es nicht.

## Belegbarkeit

Jede Aussage im Report ist auf ein Originaldokument zurückführbar:

- Die 50 Fundstücke nennen **Datum, Gremium und Vorlagennummer** (`SV-000/JJJJ`).
  Damit ist jeder Vorgang im Ratsinformationssystem unter „Vorlagen“ eindeutig auffindbar.
- Die Beobachtungen nennen zusätzlich Seitenzahl beziehungsweise Beschlussdatum.
- Auf feste Direktlinks zu PDFs wurde verzichtet: Die Dokument-URLs enthalten
  sitzungsgebundene Token und sind nicht dauerhaft gültig. Die Vorlagennummer bleibt stabil.

## Aufbau des Repositories

```
├── docs/                 GitHub Pages zeigt diesen Ordner
│   ├── index.html        Startseite: Report, neueste Ausgabe, Archiv
│   ├── suche.html        durchsuchbare Vorgänge mit Zeitachse
│   ├── termine.html      Sitzungskalender, vergangen und angekündigt
│   ├── gremien.html      wer in der Stadt wofür zuständig ist
│   ├── befunde.html      alle Erkenntnisse und Einordnungen gesammelt
│   ├── themen/           je ein Vorhaben mit allen Stationen
│   ├── report/           die datierten Gesamtreports
│   └── ausgaben/
│       ├── index.html    Archiv über alle Jahrgänge
│       ├── 2024/         33 Ausgaben
│       ├── 2025/         35 Ausgaben
│       └── 2026/         21 Ausgaben
├── src/        Vorlage des Reports (baut Diagramme und Listen per JavaScript auf)
├── scripts/    die Verarbeitungskette, Schritt 01 bis 12
│   ├── wochenlauf.sh   ein Befehl für den ganzen Wochenlauf
│   ├── seite.py        Seitenrahmen und Navigation — für alle Seiten dieselben
│   ├── basis.css       Farben, Schrift, Seitenkopf und Fuß — für alle Seiten dieselben
│   ├── pruefen.py      Kontrolle vor der Veröffentlichung
│   └── launchd/        Vorlage für den automatischen Montagslauf
└── data/       Kennzahlen, Ausgabenregister und die 74 Beschlussprotokolle
```

## Auswertung selbst nachvollziehen

```bash
# Daten holen und auswerten
uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py
uv run --with requests                       python scripts/02_protokolle_laden.py
uv run --with pypdf                          python scripts/03_auswerten.py

# Seiten bauen
uv run --with pypdf                          python scripts/05_ausgaben_bauen.py
uv run --with pypdf                          python scripts/07_tabellen_bauen.py
uv run --with pypdf                          python scripts/08_suche_bauen.py
uv run                                       python scripts/11_themen_bauen.py
uv run                                       python scripts/12_termine_bauen.py
uv run --with lxml                           python scripts/09_befunde_bauen.py
uv run                                       python scripts/10_gremien_bauen.py
uv run                                       python scripts/06_startseite_bauen.py
npm install jsdom && node scripts/04_vorrendern.js

# kontrollieren
uv run --with lxml                           python scripts/pruefen.py
```

Die Reihenfolge ist nicht beliebig: Schritt 6 (Startseite) liest Kennzahlen aus
dem, was die vorigen Schritte geschrieben haben, und Schritt 9 liest den
vorgerenderten Report — deshalb steht Schritt 4 am Ende und wird beim nächsten
Lauf gelesen. `scripts/wochenlauf.sh` führt genau diese Kette aus.

Schritt 5 erzeugt eine Ausgabe je Kalenderwoche mit Sitzung, dazu stets eine für
die laufende Woche. Gebaut werden **alle Jahrgänge**, nicht nur der laufende —
sonst bleiben ältere Ausgaben stillschweigend auf dem Stand stehen, den die
Skripte bei ihrem letzten Lauf hatten. Mit `--jahr 2025` lässt sich ein einzelner
Jahrgang bauen. Redaktionelle Einordnungen — das, was eine Maschine nicht
erfinden kann — stehen optional in `data/einordnungen.json` und werden nach
Schlüssel `JJJJ-kwNN` eingefügt.

Schritt 3 gibt sämtliche Kennzahlen des Reports auf der Konsole aus und schreibt
sie nach `data/kennzahlen.json`. Wer eine Angabe im Report nachrechnen will,
findet die Rechenregel in `scripts/03_auswerten.py` — jede Zahl entsteht dort
und nur dort.

## Eine neue Woche hinzufügen

```bash
./scripts/wochenlauf.sh
```

Das Skript prüft zuerst, ob das Ratsinformationssystem erreichbar ist, führt dann
die gesamte Kette aus, kontrolliert das Ergebnis und committet nur, wenn sich
etwas geändert hat. Mit `--trocken` läuft alles ohne Commit.

**Der Lauf muss lokal stattfinden.** Das Ratsinformationssystem beantwortet
Anfragen aus Rechenzentrumsnetzen mit `HTTP 503` — aus GitHub Actions heraus ist
es nicht erreichbar. Von einem normalen Anschluss antwortet es einwandfrei. Diese
Beschränkung wird nicht umgangen.

Automatisch montags früh laufen lassen:

```bash
cp scripts/launchd/eu.amannlabs.ratsakten.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/eu.amannlabs.ratsakten.plist
```

War der Rechner zum Termin aus, holt `launchd` den Lauf beim nächsten Start nach.
Das Protokoll landet in `~/Library/Logs/ratsakten.log`.

> [!WARNING]
> **Liegt das Projekt unter `~/Documents`, `~/Desktop` oder `~/Downloads`,
> scheitert der geplante Lauf** mit `Operation not permitted`. macOS verwehrt von
> `launchd` gestarteten Prozessen den Zugriff auf diese Ordner. Von Hand
> ausgeführt funktioniert dasselbe Skript einwandfrei — der Schutz greift nur bei
> Hintergrunddiensten.
>
> Zwei Wege: entweder in *Systemeinstellungen → Datenschutz & Sicherheit →
> Festplattenvollzugriff* `/bin/bash` freigeben, oder auf die Zeitsteuerung
> verzichten und den Wochenlauf von Hand starten. Das ist ein Befehl.

### Was auf GitHub läuft

Bei jedem Push prüft [`.github/workflows/pruefung.yml`](./.github/workflows/pruefung.yml)
das Ergebnis: tote Verweise, fehlende Schriften, Abrufe bei fremden Servern,
Lücken in den Berichtszeiträumen und ob die Tabellen zu den Kennzahlen passen.
Diese Prüfung hat beim ersten Einsatz neun fehlende Abstimmungen aufgedeckt.

* Schritt 1 muss immer zuerst laufen: `data/sitzungen.json` und `data/topmap.json`
  sind Zwischenergebnisse und werden nicht versioniert. Sie enthalten
  sitzungsgebundene Dokument-Token des Ratsinformationssystems — keine
  Zugangsdaten, aber nicht dauerhaft gültig und unnötig zu veröffentlichen.
* Schritt 2 lädt nur, was fehlt. Protokolle erscheinen typischerweise drei bis vier
  Tage nach der Sitzung; ältere Ausgaben füllen sich also nachträglich.
* Schritt 5 erzeugt die neue Ausgabe und aktualisiert das Archiv. Der Berichtszeitraum
  schließt lückenlos an die vorige Ausgabe an, auch wenn Wochen ohne Sitzung
  dazwischenliegen.
* Schritt 6 zieht Kennzahlen und den Link auf die neueste Ausgabe nach.
* Schritt 4 wird nur gebraucht, wenn der Report neu gebaut werden soll.
* Schritt 9 sammelt die Erkenntnisse; Schritt 7 schreibt die Tabellen unter `data/csv/` neu und rechnet zum Schluss
  gegen `data/kennzahlen.json` gegen. Weichen die Zahlen ab, stimmt etwas nicht.

Die Abfragen sind bewusst mit Pausen versehen, um die Server der Stadt nicht zu
belasten.

## Geplant

- [x] Wöchentliche Ausgaben, Jahrgänge 2024 bis 2026 nachgeholt (89 Stück)
- [x] Wöchentlicher Lauf als ein Befehl (`scripts/wochenlauf.sh`, `launchd`-Vorlage)
- [x] Prüfung bei jedem Push (`.github/workflows/pruefung.yml`)
- [x] Vorgangssuche mit Zeitachse (`docs/suche.html`)
- [x] Herkunft jeder Aussage gekennzeichnet (Beleg · Regelbasiert · KI-Deutung)
- [x] Archiv der bisherigen Ausgaben
- [x] Rohdaten zum Nachrechnen (`data/csv/`, siehe unten)
- [x] Seite „Wer entscheidet was" mit Fundstellen aus Gemeindeordnung und Hauptsatzung
- [x] Themenseiten: 26 Vorhaben mit allen Stationen (`docs/themen/`)
- [x] Sitzungskalender, vergangen und angekündigt (`docs/termine.html`)
- [x] Ein gemeinsames Fundament für alle Seiten (`scripts/basis.css`, `scripts/seite.py`)

## Haftungsausschluss

**Lernprojekt.** Dieses Repository ist ein privates Lern- und Technologieprojekt zur
automatisierten Auswertung öffentlich zugänglicher Verwaltungsdokumente. Es ist kein
journalistisches Erzeugnis, kein Prüfbericht und keine rechtliche oder fachliche Bewertung.

**Keine Gewähr.** Für die Richtigkeit, Vollständigkeit und Aktualität der dargestellten
Informationen wird keine Gewähr übernommen. Sämtliche Auswertungen beruhen auf maschineller
Verarbeitung von PDF-Dokumenten. Fehler bei der Texterkennung, bei der Zuordnung von
Tagesordnungspunkten und bei der maschinellen Klassifikation sind möglich und nicht
auszuschließen. **Verbindlich ist ausschließlich das jeweilige Originaldokument der Stadt
Bad Waldsee.**

**Keine Vorwürfe.** Der Report unterstellt weder der Stadtverwaltung noch einzelnen Personen
ein rechtswidriges oder schuldhaftes Verhalten. Er benennt ausschließlich, was sich aus den
öffentlich vorliegenden Unterlagen ergibt und was daraus offenbleibt.

**Einordnungen sind maschinell erzeugt.** Alle Aussagen, die über das Auszählen hinausgehen,
sind als **KI-Deutung** gekennzeichnet: Auswahl, Verknüpfung und Gewichtung von Fakten
entstehen automatisiert und sind **nicht redaktionell geprüft**. Die zugrunde liegenden Zahlen
stammen aus den Protokollen und sind dort nachprüfbar; die daraus gezogene Schlussfolgerung
ist es nicht.

**Personenbezogene Daten.** Namen werden ausschließlich dort genannt, wo Personen in
amtlicher oder mandatsbezogener Funktion öffentlich gehandelt haben und dies in den
öffentlichen Protokollen so dokumentiert ist. Namen von Privatpersonen werden nicht
wiedergegeben. Öffentliche Zustellungen wurden vollständig von der Auswertung ausgenommen.

**Keine Verbindung zur Stadt.** Das Projekt ist weder von der Stadt Bad Waldsee beauftragt
noch von ihr autorisiert oder geprüft.

## Korrekturen

Fehler zu finden ist ausdrücklich erwünscht. Bitte ein
[Issue eröffnen](https://github.com/dominikamann/ratsakten-bad-waldsee/issues/new) mit:

- der betroffenen Stelle im Report,
- dem Originaldokument, das etwas anderes aussagt,
- gegebenenfalls der korrekten Angabe.

Berechtigte Korrekturen werden zeitnah und nachvollziehbar eingearbeitet; Änderungen am
Report werden im Änderungsverlauf dokumentiert. Wer als betroffene Stelle eine Richtigstellung
wünscht, kann das ebenfalls über ein Issue oder per E-Mail tun.

## Lizenz

- **Code:** MIT
- **Report, Texte und Tabellen:** CC BY 4.0 — Weitergabe und Bearbeitung erlaubt,
  **Namensnennung erforderlich**
- **Schriften** (`docs/fonts/`): SIL Open Font License 1.1 — Archivo und IBM Plex,
  unverändert weitergegeben. Lizenztext und Copyright-Vermerke in
  [`docs/fonts/OFL.txt`](./docs/fonts/OFL.txt)

### So ist zu zitieren

Wer Zahlen, Texte oder Tabellen aus diesem Projekt weiterverwendet, gibt an:

> Quelle: Ratsakten Bad Waldsee — AmannLabs.eu
> https://github.com/dominikamann/ratsakten-bad-waldsee · Lizenz: CC BY 4.0

Bei Bearbeitungen ist zusätzlich kenntlich zu machen, dass Änderungen vorgenommen
wurden. Für den Code genügt es, den Copyright-Vermerk und den MIT-Lizenztext
beizulegen.
- **Zugrunde liegende Verwaltungsdokumente:** amtliche Werke, § 5 UrhG, Rechte bei der
  Stadt Bad Waldsee

---

Ein Projekt von [AmannLabs.eu](https://amannlabs.eu) · Alle Angaben und Insights ohne Gewähr
