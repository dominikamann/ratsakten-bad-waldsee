"""Fachbegriffe aus dem Amtsdeutsch, je einmal erklaert.

Die Ausgaben uebernehmen den Beschlusswortlaut woertlich — das ist ihre
Staerke und zugleich ihr Problem: Mit dem Wortlaut kommt die Amtssprache mit.
„Der Gemeinderat versagte das gemeindliche Einvernehmen" ist richtig und wird
von den meisten Lesern trotzdem falsch verstanden, naemlich als endgueltige
Ablehnung.

Deshalb die Regel: Jeder Fachbegriff, den eine Ausgabe uebernimmt, wird einmal
erklaert — neutral, in einem Satz, mit Fundstelle. Ausgegeben wird nur, was in
der jeweiligen Ausgabe tatsaechlich vorkommt.

Diese Texte sind keine Deutung. Sie geben geltendes Recht oder die
Hauptsatzung wieder und tragen deshalb die Marke „Beleg".
"""

from __future__ import annotations

import re

# Reihenfolge = Ausgabereihenfolge. Das Muster entscheidet, ob ein Begriff in
# einer Ausgabe vorkommt; es wird auf Titel und Beschlusstexte angewandt.
BEGRIFFE: list[dict[str, str]] = [
    {
        "name": "Gemeindliches Einvernehmen",
        "muster": r"Einvernehmen",
        "satz": (
            "Über die Zulässigkeit eines Bauvorhabens entscheidet nicht die Stadt, "
            "sondern die Baugenehmigungsbehörde — „im Einvernehmen mit der Gemeinde“. "
            "Die Stadt wird also beteiligt und erteilt oder versagt ihr Einvernehmen. "
            "Versagt sie es, ist das Vorhaben damit nicht zwingend erledigt: Ein "
            "<b>rechtswidrig</b> versagtes Einvernehmen kann die nach Landesrecht "
            "zuständige Behörde ersetzen."),
        "fundstelle": "§ 36 Abs. 1 Satz 1 und Abs. 2 Satz 3 Baugesetzbuch",
    },
    {
        "name": "Gemeinsamer Ausschuss",
        "muster": r"Gemeinsame[rn]? Ausschuss|Verwaltungsgemeinschaft",
        "satz": (
            "Bad Waldsee und Bergatreute bilden eine Vereinbarte "
            "Verwaltungsgemeinschaft. Deren Erfüllungsaufgabe ist die vorbereitende "
            "Bauleitplanung — also der Flächennutzungsplan. Darüber entscheidet "
            "nicht der Gemeinderat allein, sondern ein gemeinsamer Ausschuss "
            "beider Gemeinden."),
        "fundstelle": "§ 61 Abs. 4 Gemeindeordnung für Baden-Württemberg",
    },
    {
        "name": "Flächennutzungsplan",
        "muster": r"Flächennutzungsplan",
        "satz": (
            "Der Flächennutzungsplan legt für das ganze Gemeindegebiet in Grundzügen "
            "fest, welche Flächen künftig wofür vorgesehen sind — Wohnen, Gewerbe, "
            "Landwirtschaft, Freiraum. Er begründet noch kein Baurecht; das entsteht "
            "erst über den Bebauungsplan."),
        "fundstelle": "§ 5 Abs. 1 Satz 1 und § 1 Abs. 2 Baugesetzbuch",
    },
    {
        "name": "Abwägung",
        "muster": r"Abwägung|abgewogen|Einwend|Stellungnahmen",
        "satz": (
            "Vor dem Beschluss über einen Bauleitplan müssen die eingegangenen "
            "Einwendungen behandelt werden: „Bei der Aufstellung der Bauleitpläne "
            "sind die öffentlichen und privaten Belange gegeneinander und "
            "untereinander gerecht abzuwägen.“ In der Abwägungsvorlage steht zu "
            "jedem Einwand, ob ihm gefolgt wird und warum."),
        "fundstelle": "§ 1 Abs. 7 Baugesetzbuch",
    },
    {
        "name": "Satzungsbeschluss",
        "muster": r"Satzungsbeschluss|als Satzung",
        "satz": (
            "Der letzte Schritt eines Bebauungsplanverfahrens: „Die Gemeinde "
            "beschließt den Bebauungsplan als Satzung.“ Danach wird er ortsüblich "
            "bekannt gemacht und tritt in Kraft — ab dann gilt er als Ortsrecht."),
        "fundstelle": "§ 10 Abs. 1 und Abs. 3 Baugesetzbuch",
    },
    {
        "name": "Ortschaftsrat",
        "muster": r"Ortschaftsrat|Ortsvorsteher",
        "satz": (
            "Jede der vier Ortschaften hat einen eigenen Rat. Er berät die örtliche "
            "Verwaltung und ist zu wichtigen Angelegenheiten seiner Ortschaft zu "
            "hören. Darüber hinaus sind ihm bestimmte Entscheidungen übertragen, "
            "etwa die Bewirtschaftung von Haushaltsmitteln über 3.000 € bis 26.000 € "
            "im Einzelfall."),
        "fundstelle": "§ 16 Hauptsatzung der Stadt Bad Waldsee",
    },
    {
        "name": "Ohne Beschlussfassung",
        "muster": r"Ohne Beschlussfassung|Kenntnis genommen|zur Kenntnis",
        "satz": (
            "Der Punkt stand auf der Tagesordnung und wurde behandelt, aber nicht "
            "abgestimmt. Das Protokoll führt ihn dann als „Ohne Beschlussfassung“ "
            "oder als Kenntnisnahme. Über den Inhalt sagt das nichts — wohl aber, "
            "dass das Gremium darüber nicht entschieden hat."),
        "fundstelle": "Schreibweise der Beschlussprotokolle des Ratsinformationssystems",
    },
    {
        "name": "Bebauungsplan",
        # Vor dem Flaechennutzungsplan-Eintrag ausgeben waere falsch herum:
        # Der Bebauungsplan wird aus ihm entwickelt. Die Reihenfolge der Liste
        # ist die Ausgabereihenfolge.
        "muster": r"Bebauungsplan",
        "satz": (
            "Der Plan, der für ein bestimmtes Gebiet verbindlich festlegt, was dort "
            "gebaut werden darf — Art und Maß der Bebauung, überbaubare Flächen, "
            "Verkehrsflächen. Anders als der Flächennutzungsplan, der nur die "
            "Grundzüge für das ganze Stadtgebiet umreißt, begründet er unmittelbar "
            "Baurecht: Ein Vorhaben ist dort zulässig, wenn es seinen Festsetzungen "
            "nicht widerspricht <b>und die Erschließung gesichert ist</b>."),
        "fundstelle": "§ 1 Abs. 2, § 8 Abs. 1 und § 30 Abs. 1 Baugesetzbuch",
    },
    {
        "name": "Aufstellungsbeschluss",
        "muster": r"Aufstellungsbeschluss|Aufstellung des Bebauungsplans",
        "satz": (
            "Der erste Schritt eines Bauleitplanverfahrens — das Gegenstück zum "
            "Satzungsbeschluss am Ende. Er entscheidet noch nichts über den Inhalt, "
            "sondern eröffnet das Verfahren. Zwischen beiden liegen Entwurf, "
            "Beteiligung der Öffentlichkeit und Abwägung; bei größeren Vorhaben "
            "vergehen dabei mehrere Jahre und der Plan kommt mehrfach auf die "
            "Tagesordnung."),
        "fundstelle": "§ 2 Abs. 1 Satz 2 Baugesetzbuch",
    },
    {
        "name": "Feststellungsbeschluss",
        "muster": r"Feststellungsbeschluss|Feststellung des Flächennutzungsplans",
        "satz": (
            "Der Abschluss eines Flächennutzungsplan-Verfahrens. Was beim "
            "Bebauungsplan der Satzungsbeschluss ist, ist hier der "
            "Feststellungsbeschluss — mit einem Unterschied: Der "
            "Flächennutzungsplan wird damit noch nicht wirksam. Er bedarf der "
            "Genehmigung der höheren Verwaltungsbehörde, und wirksam wird er erst, "
            "wenn deren Erteilung ortsüblich bekannt gemacht ist."),
        "fundstelle": "§ 6 Abs. 1 und Abs. 5 Baugesetzbuch",
    },
    {
        "name": "Jahresabschluss und Entlastung",
        "muster": r"Jahresabschluss|Entlastung",
        "satz": (
            "Die Rechnung über ein abgelaufenes Haushaltsjahr. Der Gemeinderat "
            "stellt sie fest und entscheidet über die Entlastung — eine Aussage "
            "darüber, dass die Mittel wie beschlossen verwendet wurden. Das Gesetz "
            "kennt dafür zwei Fristen: sechs Monate für die Aufstellung durch die "
            "Verwaltung und zwölf Monate für die Feststellung durch den Gemeinderat."),
        "fundstelle": "§ 95b Gemeindeordnung für Baden-Württemberg",
    },
    {
        "name": "Über- und außerplanmäßige Ausgaben",
        "muster": r"außerplanmäßig|überplanmäßig|ausserplanmäßig",
        "satz": (
            "Ausgaben, die im beschlossenen Haushaltsplan nicht oder nicht in dieser "
            "Höhe vorgesehen waren. Sie sind zulässig, brauchen aber eine eigene "
            "Zustimmung. Sie kann vorab als einzelner Tagesordnungspunkt erfolgen "
            "oder nachträglich gesammelt im Jahresabschluss."),
        "fundstelle": "Beschlussprotokolle; § 16 Abs. 4.2 Hauptsatzung für die Ortschaftsräte",
    },
]

for _b in BEGRIFFE:
    _b["regex"] = re.compile(_b["muster"], re.IGNORECASE)


def begriffe_finden(text: str) -> list[dict[str, str]]:
    """Die Begriffe zurueckgeben, die in diesem Text vorkommen."""
    return [b for b in BEGRIFFE if b["regex"].search(text)]


# --- Erklaerung im Text statt als Kapitel ------------------------------------

def markieren(text: str, schon_erklaert: set[str]) -> str:
    """Den ersten Treffer jedes Begriffs im Text mit seiner Erklaerung versehen.

    Vorher standen die Erklaerungen als eigener Abschnitt am Ende der Ausgabe.
    Wer beim Lesen ueber „Abwaegungs- und Satzungsbeschluss" stolperte, fand
    die Antwort erst, wenn er ohnehin schon weitergelesen hatte — und musste
    dafuer die Stelle verlassen, an der die Frage aufkam.

    Jetzt steht die Erklaerung dort, wo das Wort steht. Der Begriff ist
    gepunktet unterstrichen; die Erklaerung erscheint beim Zeigen mit der Maus
    und beim Antippen. Fuer beides genuegt CSS — das Wort ist ueber `tabindex`
    fokussierbar, damit es auch ohne Zeigegeraet erreichbar bleibt.

    **Erwartet maskierten Text ohne eigenes Markup.** Sonst geriete die
    Ersetzung in ein Attribut oder zerschnitte ein Tag.

    Gesucht wird auf dem **unveraenderten** Text und erst danach ersetzt, von
    hinten nach vorn. Wuerde man Treffer fuer Treffer ersetzen, suchte der
    naechste Begriff bereits im eingefuegten Erklaerungstext — „Abwaegung"
    erklaert den Bauleitplan, und „Bebauungsplan" haette sich mitten in dieses
    Markup gesetzt.

    `schon_erklaert` verhindert, dass derselbe Begriff in einer Ausgabe
    mehrfach aufgemacht wird; einmal reicht.
    """
    treffer = []
    for b in BEGRIFFE:
        if b["name"] in schon_erklaert:
            continue
        m = b["regex"].search(text)
        if not m:
            continue
        # Ueberschneidungen verwerfen: „Bebauungsplan" und „Aufstellung des
        # Bebauungsplans" koennen dieselbe Stelle treffen.
        if any(m.start() < e and a < m.end() for a, e, _ in treffer):
            continue
        treffer.append((m.start(), m.end(), b))

    for anfang, ende, b in sorted(treffer, reverse=True):
        wort = text[anfang:ende]
        schon_erklaert.add(b["name"])
        text = (text[:anfang]
                + f'<span class="erklaert" tabindex="0">{wort}'
                + '<span class="tooltip" role="note">'
                + f'<b>{b["name"]}</b> {b["satz"]}'
                + f'<span class="fundstelle">{b["fundstelle"]}</span>'
                + '</span></span>'
                + text[ende:])
    return text
