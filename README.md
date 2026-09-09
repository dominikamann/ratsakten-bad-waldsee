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
> **Dies ist ein privates Lern- und Technikprojekt. Für die Richtigkeit, Vollständigkeit und
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
| Verlinkte Dokumente | 625 |
| Ausgewertete Beschlussprotokolle | 72 |
| Ausgezählte Abstimmungen | 333 |
| Gremien | 12 |

**Zeitraum:** 01.01.2024 – 09.09.2026 (Stichtag). Bereits terminierte Sitzungen nach dem
Stichtag wurden ausgeschlossen, damit die Protokollquote nicht verzerrt wird.

## Der Report

➡️ **[Ratsanalyse 2024–2026](./docs/report/2026-09-09.html)** — die große Vollauswertung
➡️ **[Aktuelle Ausgabe, KW 37/2026](./docs/ausgaben/2026/kw37.html)** — die wöchentliche Aktenlage
➡️ **[Archiv](./docs/ausgaben/index.html)** — alle 21 Ausgaben des Jahrgangs 2026

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

## Selbst nachrechnen

Unter `data/csv/` liegen drei Tabellen, die sich direkt in Excel, LibreOffice
oder Numbers öffnen lassen — Semikolon als Trennzeichen, damit kein Importdialog
nötig ist:

| Datei | Zeilen | Inhalt |
|---|---|---|
| [`sitzungen.csv`](./data/csv/sitzungen.csv) | 166 | Datum, Gremium, Kalenderwoche, Zahl der Tagesordnungspunkte, ob ein Protokoll vorliegt |
| [`tagesordnungspunkte.csv`](./data/csv/tagesordnungspunkte.csv) | 616 | jeder Punkt mit Datum, Gremium, Nummer, Titel und Vorlagennummer |
| [`beschluesse.csv`](./data/csv/beschluesse.csv) | 333 | jede Abstimmung mit Vorlagennummer, Titel und Stimmenverhältnis |

Damit lässt sich jede Zahl des Reports ohne Programmierkenntnisse überprüfen.
Beispiel: In `beschluesse.csv` nach der Spalte `einstimmig` filtern — es bleiben
59 Zeilen übrig, genau die im Report genannten nicht einstimmigen Beschlüsse.

Die Tabellen enthalten bewusst keine Dokument-Links: Die URLs des
Ratsinformationssystems sind nicht dauerhaft gültig. Stabile Kennung ist die
Vorlagennummer.

## Belegbarkeit

Jede Aussage im Report ist auf ein Originaldokument zurückführbar:

- Die 50 Fundstücke nennen **Datum, Gremium und Vorlagennummer** (`SV-000/JJJJ`).
  Damit ist jeder Vorgang im Ratsinformationssystem unter „Vorlagen“ eindeutig auffindbar.
- Die kritischen Beobachtungen nennen zusätzlich Seitenzahl beziehungsweise Beschlussdatum.
- Auf feste Direktlinks zu PDFs wurde verzichtet: Die Dokument-URLs enthalten
  sitzungsgebundene Token und sind nicht dauerhaft gültig. Die Vorlagennummer bleibt stabil.

## Aufbau des Repositories

```
├── docs/                 GitHub Pages zeigt diesen Ordner
│   ├── index.html        Startseite: Report, neueste Ausgabe, Archiv
│   ├── report/           die datierten Gesamtreports
│   └── ausgaben/
│       ├── index.html    Archiv über alle Jahrgänge
│       └── 2026/         kw03.html … kw37.html
├── src/        Vorlage des Reports (baut Diagramme und Listen per JavaScript auf)
├── scripts/    die Verarbeitungskette, Schritt 01 bis 06
└── data/       Kennzahlen, Ausgabenregister und die 74 Beschlussprotokolle
```

## Auswertung selbst nachvollziehen

```bash
uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py
uv run --with requests                       python scripts/02_protokolle_laden.py
uv run --with pypdf                          python scripts/03_auswerten.py
uv run --with pypdf                          python scripts/05_ausgaben_bauen.py
uv run                                       python scripts/06_startseite_bauen.py
npm install jsdom && node scripts/04_vorrendern.js
```

Schritt 5 erzeugt eine Ausgabe je Kalenderwoche mit Sitzung, dazu stets eine für
die laufende Woche. Redaktionelle Einordnungen — das, was eine Maschine nicht
erfinden kann — stehen optional in `data/einordnungen.json` und werden nach
Schlüssel `JJJJ-kwNN` eingefügt.

Schritt 3 gibt sämtliche Kennzahlen des Reports auf der Konsole aus und schreibt
sie nach `data/kennzahlen.json`. Wer eine Angabe im Report nachrechnen will,
findet die Rechenregel in `scripts/03_auswerten.py` — jede Zahl entsteht dort
und nur dort.

## Eine neue Woche hinzufügen

```bash
uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py
uv run --with requests                       python scripts/02_protokolle_laden.py
uv run --with pypdf                          python scripts/03_auswerten.py
uv run --with pypdf                          python scripts/05_ausgaben_bauen.py
uv run                                       python scripts/06_startseite_bauen.py
uv run --with pypdf                          python scripts/07_tabellen_bauen.py
```

Mehr ist nicht zu tun — keine Datei wird von Hand angefasst. Jahr und Redaktions-
schluss nehmen die Skripte vom Tagesdatum.

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
* Schritt 7 schreibt die Tabellen unter `data/csv/` neu und rechnet zum Schluss
  gegen `data/kennzahlen.json` gegen. Weichen die Zahlen ab, stimmt etwas nicht.

Die Abfragen sind bewusst mit Pausen versehen, um die Server der Stadt nicht zu
belasten.

## Geplant

- [x] Wöchentliche Ausgaben, Jahrgang 2026 nachgeholt (`scripts/05_ausgaben_bauen.py`)
- [x] Automatischer Lauf per GitHub Action (`.github/workflows/aktenlage.yml`)
- [x] Archiv der bisherigen Ausgaben
- [x] Rohdaten zum Nachrechnen (`data/csv/`, siehe unten)
- [ ] Übertragung auf weitere Kommunen mit demselben Systemhersteller

## Haftungsausschluss

**Lernprojekt.** Dieses Repository ist ein privates Lern- und Technikprojekt zur
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
öffentlich vorliegenden Unterlagen ergibt und was daraus offenbleibt. Wertungen sind als
solche gekennzeichnet und stellen die persönliche Einschätzung des Autors dar
(Meinungsäußerung im Sinne des Art. 5 Abs. 1 GG).

**Personenbezogene Daten.** Namen werden ausschließlich dort genannt, wo Personen in
amtlicher oder mandatsbezogener Funktion öffentlich gehandelt haben und dies in den
öffentlichen Protokollen so dokumentiert ist. Namen von Privatpersonen werden nicht
wiedergegeben. Öffentliche Zustellungen wurden vollständig von der Auswertung ausgenommen.

**Keine Verbindung zur Stadt.** Das Projekt ist weder von der Stadt Bad Waldsee beauftragt
noch von ihr autorisiert oder geprüft.

## Korrekturen

Fehler zu finden ist ausdrücklich erwünscht. Bitte ein
[Issue eröffnen](../../issues/new) mit:

- der betroffenen Stelle im Report,
- dem Originaldokument, das etwas anderes aussagt,
- gegebenenfalls der korrekten Angabe.

Berechtigte Korrekturen werden zeitnah und nachvollziehbar eingearbeitet; Änderungen am
Report werden im Änderungsverlauf dokumentiert. Wer als betroffene Stelle eine Richtigstellung
wünscht, kann das ebenfalls über ein Issue oder per E-Mail tun.

## Lizenz

- **Code:** MIT
- **Report und Texte:** CC BY 4.0
- **Schriften** (`docs/fonts/`): SIL Open Font License 1.1 — Archivo und IBM Plex,
  unverändert weitergegeben. Lizenztext und Copyright-Vermerke in
  [`docs/fonts/OFL.txt`](./docs/fonts/OFL.txt)
- **Zugrunde liegende Verwaltungsdokumente:** amtliche Werke, § 5 UrhG, Rechte bei der
  Stadt Bad Waldsee

---

Ein Projekt von [AmannLabs.eu](https://amannlabs.eu) · Alle Angaben und Insights ohne Gewähr
