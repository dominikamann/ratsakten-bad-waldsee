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

➡️ **[Ratsanalyse 2024–2026](./docs/amannlabs-ratsanalyse-bad-waldsee-2026-09-09.html)** — die einmalige Vollauswertung
➡️ **[Waldseer Aktenlage, KW 37/2026](./docs/amannlabs-aktenlage-bad-waldsee-2026-kw37.html)** — die wöchentliche Ausgabe

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

## Belegbarkeit

Jede Aussage im Report ist auf ein Originaldokument zurückführbar:

- Die 50 Fundstücke nennen **Datum, Gremium und Vorlagennummer** (`SV-000/JJJJ`).
  Damit ist jeder Vorgang im Ratsinformationssystem unter „Vorlagen“ eindeutig auffindbar.
- Die kritischen Beobachtungen nennen zusätzlich Seitenzahl beziehungsweise Beschlussdatum.
- Auf feste Direktlinks zu PDFs wurde verzichtet: Die Dokument-URLs enthalten
  sitzungsgebundene Token und sind nicht dauerhaft gültig. Die Vorlagennummer bleibt stabil.

## Aufbau des Repositories

```
├── docs/       fertige Dokumente — GitHub Pages zeigt diesen Ordner
├── src/        Vorlagen (bauen Diagramme und Listen per JavaScript auf)
├── scripts/    die Verarbeitungskette, Schritt 01 bis 04
└── data/       Rohdaten und die 74 heruntergeladenen Protokolle
```

## Auswertung selbst nachvollziehen

```bash
uv run --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py
uv run --with requests                       python scripts/02_protokolle_laden.py
uv run --with pypdf                          python scripts/03_auswerten.py
npm install jsdom && node scripts/04_vorrendern.js
```

Schritt 3 gibt sämtliche Kennzahlen des Reports auf der Konsole aus und schreibt
sie nach `data/kennzahlen.json`. Wer eine Angabe im Report nachrechnen will,
findet die Rechenregel in `scripts/03_auswerten.py` — jede Zahl entsteht dort
und nur dort.

Die Abfragen sind bewusst mit Pausen versehen, um die Server der Stadt nicht zu
belasten.

## Geplant

- [ ] Wöchentliche Aktualisierung des Reports
- [ ] Archiv der bisherigen Ausgaben
- [ ] Rohdaten als CSV/JSON zum Nachrechnen
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
- **Zugrunde liegende Verwaltungsdokumente:** amtliche Werke, § 5 UrhG, Rechte bei der
  Stadt Bad Waldsee

---

Ein Projekt von [AmannLabs.eu](https://amannlabs.eu) · Alle Angaben und Insights ohne Gewähr
