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
