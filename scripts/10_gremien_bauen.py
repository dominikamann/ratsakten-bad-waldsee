"""Schritt 10 — die Seite „Wer entscheidet was" erzeugen.

Das Projekt zeigt Zahlen und Erkenntnisse, setzt aber bisher voraus, dass man
weiss, wer in einer Stadt worueber entscheidet. Ohne diesen Rahmen bleibt
jede Zahl nur eine Zahl — und die Erkenntnis zu den Ortschaftsraeten ist
ueberhaupt nur zu verstehen, wenn man weiss, dass ihnen Entscheidungen
uebertragen sind.

Jede Aussage dieser Seite stammt aus der Hauptsatzung der Stadt, der
Gemeindeordnung oder dem Baugesetzbuch und nennt ihre Fundstelle. Die
Sitzungszahlen kommen aus der eigenen Auswertung.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from seite import fuss, kopf, kurz

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "data"
DOCS = WURZEL / "docs"


EIGEN = """
/* Nur auf dieser Seite gebraucht: die Fundstellenzeile unter einem Abschnitt. */
.quelle{font-family:var(--mono);font-size:12px;line-height:1.5;
  color:var(--muted);border-top:1px solid var(--rule);padding-top:8px;
  margin:14px 0 30px;max-width:62ch}
"""


def beleg(text: str) -> str:
    return f'<p class="quelle">{text}</p>'


def main() -> None:
    kennzahlen = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))
    gremien = kennzahlen.get("gremien", {})

    def sitzungen(*teile: str) -> int:
        """Sitzungen aller Gremien, deren Name alle genannten Teile enthaelt.

        Die Auswertung fasst Gremien unter eigenen Namen zusammen — aus dem
        „Ausschuss fuer Umwelt, Technik und Nachhaltigkeit" wird dort
        „Ausschuss Umwelt/Technik". Ein Vergleich auf den Namensanfang lieferte
        deshalb still eine Null.
        """
        summe = 0
        for k, v in gremien.items():
            if all(t.lower() in k.lower() for t in teile):
                summe += v["sitzungen"]
        if not summe:
            raise SystemExit(
                f"Kein Gremium in kennzahlen.json enthaelt {teile!r} — "
                f"vorhanden: {sorted(gremien)}")
        return summe

    gr = sitzungen("Gemeinderat")
    va = sitzungen("Verwaltungsausschuss")
    ut = sitzungen("Ausschuss", "Umwelt")
    ga = sitzungen("Gemeinsamer Ausschuss")
    ortsch = sitzungen("Ortschaftsrat")
    zeitraum = kennzahlen.get("stichtag", dt.date.today().isoformat())

    t = [kopf("Wer entscheidet was · Ratsakten Bad Waldsee", hier="gremien",
              beschreibung="Gemeinderat, Ausschüsse, Ortschaftsräte, Verwaltung, "
                           "Landratsamt — wer in Bad Waldsee wofür zuständig ist.",
              eigen=EIGEN),
         '<div class="wrap">']

    t.append(f"""
<header>
  <p class="eyebrow">Grundlagen</p>
  <h1>Wer entscheidet was</h1>
  <p class="lede">In einer Stadt entscheidet nicht ein Gremium, sondern mehrere —
  und manches entscheidet die Stadt gar nicht. Diese Seite ordnet ein, wer in Bad
  Waldsee wofür zuständig ist. Sie ist die Lesehilfe für alles Übrige auf dieser
  Website.</p>
  <div class="issueline">
    <span><b>Gremien</b> {len(gremien)}</span>
    <span><b>Sitzungen</b> {sum(v["sitzungen"] for v in gremien.values())}</span>
    <span><b>Stand</b> {kurz(zeitraum)}</span>
    <span><b>Herkunft</b> Beleg &middot; Hauptsatzung, Gemeindeordnung, Baugesetzbuch</span>
  </div>
</header>

<h2 class="headline">Der Gemeinderat</h2>
<p>Der Gemeinderat ist nach der Hauptsatzung „die Vertretung der Bürger und das
Hauptorgan der Stadt". Er legt die Grundsätze für die Verwaltung fest und
entscheidet über alle Angelegenheiten der Stadt — <b>soweit er sie nicht den
Ausschüssen, den Ortschaftsräten oder dem Bürgermeister übertragen hat</b> oder
der Bürgermeister kraft Gesetzes zuständig ist. Er besteht aus dem Bürgermeister
als Vorsitzendem und den ehrenamtlichen Stadträten.</p>
<p>Im ausgewerteten Zeitraum tagte er {gr} Mal öffentlich.</p>
{beleg("§ 2 und § 3 Hauptsatzung der Stadt Bad Waldsee, Stand Juli 2024")}

<h2 class="headline">Die beschließenden Ausschüsse</h2>
<p>Bad Waldsee hat zwei davon: den <b>Verwaltungsausschuss</b> und den
<b>Ausschuss für Umwelt, Technik und Nachhaltigkeit</b>. Jeder besteht aus der
Hälfte der Gemeinderatsmitglieder und dem Bürgermeister.</p>
<div class="kasten">
  <p class="lab">Der wichtigste Satz für Leser</p>
  <p>Diese Ausschüsse „entscheiden im Rahmen ihrer Zuständigkeit selbständig an
  Stelle des Gemeinderats". Was dort beschlossen wird, ist also entschieden — es
  ist keine Empfehlung, die später noch einmal in den Gemeinderat kommt.</p>
</div>
<p>Die Geschäftskreise sind in der Hauptsatzung aufgezählt. Zum
<b>Verwaltungsausschuss</b> gehören unter anderem Personal, Finanz- und
Haushaltswirtschaft, Schulen und Kindergärten, Soziales, Vereins-, Jugend-,
Sport- und Kulturangelegenheiten sowie die Liegenschaften der Stadt. Zum
<b>Ausschuss für Umwelt, Technik und Nachhaltigkeit</b> gehören die
Bauleitplanung, Ver- und Entsorgung, Straßen, Feuerlöschwesen, Friedhöfe,
Grünanlagen, Umweltschutz sowie Nachhaltigkeit und Klimafolgenanpassung.</p>
<p>Im ausgewerteten Zeitraum tagte der Verwaltungsausschuss {va} Mal, der
Ausschuss für Umwelt, Technik und Nachhaltigkeit {ut} Mal. Dieser Ausschuss hieß
bis Juni 2024 „Ausschuss für Umwelt und Technik"; die Zahl umfasst beide
Bezeichnungen.</p>
{beleg("§ 4, § 5 Abs. 1 und 2, § 7 und § 8 Hauptsatzung")}

<h2 class="headline">Die Ortschaftsräte</h2>
<p>Bad Waldsee hat vier Ortschaften: Haisterkirch, Michelwinnaden, Mittelurbach
und Reute-Gaisbeuren. Jede hat einen eigenen Ortschaftsrat. Seine erste Aufgabe
ist die Beratung: Er ist zu wichtigen Angelegenheiten der Ortschaft zu hören und
hat ein Vorschlagsrecht.</p>
<p>Darüber hinaus sind ihm aber <b>Angelegenheiten zur Entscheidung übertragen</b>
— im Rahmen der im Haushaltsplan bereitgestellten Mittel:</p>
<div class="tablewrap"><table>
<caption>Übertragene Entscheidungen nach § 16 Abs. 4 Hauptsatzung</caption>
<thead><tr><th>Fundstelle</th><th>Gegenstand</th><th>Rahmen</th></tr></thead>
<tbody>
<tr><td class="mono">§ 16 Abs. 4.1</td><td>Bewirtschaftung von Haushaltsmitteln</td><td>über 3.000 € bis 26.000 € im Einzelfall</td></tr>
<tr><td class="mono">§ 16 Abs. 4.2</td><td>über- und außerplanmäßige Ausgaben</td><td>über 600 € bis 6.000 €</td></tr>
<tr><td class="mono">§ 16 Abs. 4.3</td><td>öffentliche Einrichtungen einschließlich Gemeindestraßen</td><td>Bedeutung nicht über die Ortschaft hinaus</td></tr>
<tr><td class="mono">§ 16 Abs. 4.5–4.7</td><td>Vereinsförderung, örtliche Feuerwehrabteilung, Straßenbenennung</td><td>—</td></tr>
<tr><td class="mono">§ 16 Abs. 4.8</td><td>Grundeigentum, Tausch, Vorkaufsrechte</td><td>über 3.000 € bis 52.000 € im Einzelfall</td></tr>
</tbody></table></div>
<p>Die vier Ortschaftsräte tagten im ausgewerteten Zeitraum zusammen {ortsch} Mal
öffentlich — etwa die Hälfte aller öffentlichen Sitzungen der Stadt. Zu keiner
dieser Sitzungen ist im Ratsinformationssystem eine Niederschrift abrufbar; das
ist die <a href="./befunde.html">erste Erkenntnis</a> dieses Projekts.</p>
{beleg("§ 13, § 14 und § 16 Hauptsatzung")}

<h2 class="headline">Die Ortsvorsteher</h2>
<p>Der Ortsvorsteher ist Vorsitzender des Ortschaftsrats und vertritt den
Bürgermeister beim Vollzug von dessen Beschlüssen und bei der Leitung der
örtlichen Verwaltung. In Haisterkirch, Michelwinnaden und Mittelurbach sind die
Ortsvorsteher Ehrenbeamte auf Zeit; für Reute-Gaisbeuren bestellt der
Gemeinderat im Einvernehmen mit dem Ortschaftsrat eine Beamtin oder einen
Beamten der Stadt.</p>
{beleg("§ 17 Hauptsatzung")}

<h2 class="headline">Der Gemeinsame Ausschuss</h2>
<p>Bad Waldsee und Bergatreute bilden eine Vereinbarte Verwaltungsgemeinschaft.
Deren Erfüllungsaufgabe ist nach der Gemeindeordnung die <b>vorbereitende
Bauleitplanung</b> — also der Flächennutzungsplan, der festlegt, wo in beiden
Gemeinden grundsätzlich gebaut, gewerbt oder freigehalten wird. Darüber
entscheidet nicht der Gemeinderat allein, sondern ein gemeinsamer Ausschuss
beider Gemeinden. In den Protokollen ist erkennbar, wie das zusammenwirkt: Der
Gemeinderat beauftragt seine Vertreter, im Gemeinsamen Ausschuss einer Änderung
zuzustimmen.</p>
<p>Im ausgewerteten Zeitraum tagte er {ga} Mal.</p>
{beleg("§ 61 Abs. 4 Gemeindeordnung für Baden-Württemberg; "
       "Beschlussprotokolle des Gemeinderats zu Änderungen des Flächennutzungsplans")}

<h2 class="headline">Was die Stadt <i>nicht</i> entscheidet</h2>
<p>Über die Zulässigkeit von Bauvorhaben — etwa Windkraftanlagen im Außenbereich —
entscheidet nicht die Stadt, sondern die Baugenehmigungsbehörde, und zwar „im
Einvernehmen mit der Gemeinde". Die Stadt wird also beteiligt und erteilt oder
versagt ihr Einvernehmen.</p>
<div class="kasten">
  <p class="lab">Häufiges Missverständnis</p>
  <p>Versagt der Gemeinderat das Einvernehmen, ist das Vorhaben damit nicht
  zwingend erledigt: Ein <b>rechtswidrig</b> versagtes Einvernehmen kann die nach
  Landesrecht zuständige Behörde ersetzen. Ob eine Versagung rechtmäßig war,
  entscheidet sich außerhalb des Ratsinformationssystems — dieses Projekt kann
  dazu nichts sagen.</p>
</div>
{beleg("§ 36 Abs. 1 Satz 1 und Abs. 2 Satz 3 Baugesetzbuch")}

<h2 class="headline">Was Sie selbst tun können</h2>
<p>Die Sitzungen der genannten Gremien sind öffentlich, soweit nicht ausdrücklich
in nichtöffentlicher Sitzung beraten wird. Jede und jeder kann hingehen; Termine
und Tagesordnungen stehen im <a href="https://ris.bad-waldsee.de/"
target="_blank" rel="noopener noreferrer">Ratsinformationssystem</a> der Stadt.</p>
<p>Über jede Sitzung ist eine Niederschrift zu fertigen, und
<b>Einwohner können sie einsehen</b>. Das gilt auch dort, wo im Internet nichts
abrufbar ist — etwa bei den Ortschaftsräten. Wer wissen will, was dort beraten
und entschieden wurde, kann die Einsicht bei der Stadt verlangen.</p>
{beleg("§ 38 Abs. 1 und Abs. 2 Satz 4 Gemeindeordnung für Baden-Württemberg")}

<div class="kasten">
  <p class="lab">Zu dieser Seite</p>
  <p>Sie enthält keine Auswertung und keine Deutung, sondern gibt geltendes Recht
  und die Hauptsatzung der Stadt wieder. Maßgeblich ist immer der Originaltext;
  die Hauptsatzung liegt im Ratsinformationssystem der Stadt aus. Stand der
  Auswertungszahlen: {kurz(zeitraum)}.</p>
</div>
""")

    t.append("</div>")
    t.append(fuss(meta=f"Stand {kurz(zeitraum)}"))

    ziel = DOCS / "gremien.html"
    ziel.write_text("\n".join(t), encoding="utf-8")
    print(f"  {ziel.relative_to(WURZEL)}  —  {ziel.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
