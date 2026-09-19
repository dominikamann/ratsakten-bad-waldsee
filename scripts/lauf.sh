#!/usr/bin/env bash
#
# Lauf — holt nach, was seit dem letzten Mal erschienen ist, baut alle Dokumente
# neu und veroeffentlicht das Ergebnis.
#
# Hiess bis September 2026 „wochenlauf.sh". Der Lauf findet seit der Umstellung
# taeglich statt, weil die Stadt unregelmaessig veroeffentlicht — die Ausgabe
# bleibt die Wochenausgabe und waechst taeglich mit. Der Name nennt deshalb
# keine Haeufigkeit mehr; die steht in scripts/launchd/, wo sie hingehoert.
#
# Laeuft bewusst lokal und nicht auf einem GitHub-Runner: Das
# Ratsinformationssystem beantwortet Anfragen aus Rechenzentrumsnetzen mit
# HTTP 503. Von einem privaten Anschluss aus antwortet es normal. Diese
# Beschraenkung wird nicht umgangen.
#
#   ./scripts/lauf.sh              # holen, bauen, committen, pushen
#   ./scripts/lauf.sh --trocken    # nur holen und bauen, nichts committen
#
set -euo pipefail

cd "$(dirname "$0")/.."
TROCKEN=0
[[ "${1:-}" == "--trocken" ]] && TROCKEN=1

log() { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
fehler() { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

command -v uv   >/dev/null || fehler "uv fehlt — https://docs.astral.sh/uv/"
command -v node >/dev/null || fehler "node fehlt"
[[ -d node_modules/jsdom ]] || { log "jsdom installieren"; npm install --no-save jsdom >/dev/null; }

# --- Erreichbarkeit zuerst pruefen -------------------------------------------
# Ohne diesen Test scheitert Schritt 1 nach drei Versuchen mit einer Meldung,
# die man leicht fuer einen Programmfehler haelt.
log "Ratsinformationssystem erreichbar?"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 https://ris.bad-waldsee.de/termine || echo 000)
case "$CODE" in
  200) echo "   HTTP 200 — in Ordnung" ;;
  503) fehler "HTTP 503 — der Server weist diese Verbindung ab. Aus einem Rechenzentrums-
        netz (VPN, Cloud, GitHub Actions) ist das zu erwarten. Ueber einen normalen
        Anschluss erneut versuchen." ;;
  000) fehler "keine Verbindung — Netzwerk pruefen" ;;
  *)   fehler "unerwarteter HTTP-Status $CODE" ;;
esac

# --- Verarbeitungskette -------------------------------------------------------
log "1/14  Sitzungen und Tagesordnungen laden"
uv run --quiet --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py

log "2/14  Neue Protokolle laden"
uv run --quiet --with requests python scripts/02_protokolle_laden.py

# Vorlagen werden oft erst nach der Einladung nachgereicht — SV-152/2026
# ("Dorfmitte Osterhofen") stand am 15.09.2026 nur im Gesamtpaket und kam erst
# einen Tag spaeter einzeln dazu. Solange dieser Schritt ein Handgriff war,
# blieb so etwas bis zum naechsten manuellen Aufruf unsichtbar.
log "3/14  Neue Sitzungsvorlagen laden"
uv run --quiet --with requests --with pypdf python scripts/15_vorlagen_laden.py | tail -1

log "4/14  Kennzahlen berechnen"
uv run --quiet --with pypdf python scripts/03_auswerten.py | head -3

log "5/14  Ausgaben erzeugen (alle Jahrgänge)"
uv run --quiet --with pypdf python scripts/05_ausgaben_bauen.py | tail -2

log "6/14  Tabellen und Suche erzeugen"
uv run --quiet --with pypdf python scripts/07_tabellen_bauen.py | tail -4
uv run --quiet --with pypdf python scripts/08_suche_bauen.py

log "7/14  Themenseiten erzeugen"
uv run --quiet python scripts/11_themen_bauen.py

log "8/14  Terminseite erzeugen"
uv run --quiet python scripts/12_termine_bauen.py

log "9/14  Erkenntnisse sammeln"
uv run --quiet --with lxml python scripts/09_befunde_bauen.py

log "10/14  Seite „Wer entscheidet was“ erzeugen"
uv run --quiet python scripts/10_gremien_bauen.py

log "11/14  Startseite erzeugen"
uv run --quiet python scripts/06_startseite_bauen.py

# Vor dem Vorrendern, nicht danach: Schritt 04 liest den Quelltext des Reports
# und schreibt ihn unter dem Stichtag als Dateinamen nach docs/report/.
log "12/14  Kennzahlen in den Report eintragen"
uv run --quiet python scripts/16_report_pflegen.py

log "13/14  Report vorrendern"
node scripts/04_vorrendern.js | tail -1

log "14/14  Kennzahlen in die README eintragen"
uv run --quiet python scripts/13_readme_pflegen.py

# --- Pruefen ------------------------------------------------------------------
# Der Code zuerst, dann das Ergebnis. ruff findet unbenutzte Importe, tote
# Variablen und Schleifenvariablen, die ein Lambda erst spaeter nachschlaegt —
# Dinge, die eine erzeugte Seite nicht verraet, weil sie noch stimmt. Was
# geprueft wird, steht in ruff.toml; ohne diese Datei waere es die
# Vorgabeauswahl der jeweiligen ruff-Version.
log "Code pruefen"
uv run --quiet --with ruff ruff check scripts/

log "Pruefung"
uv run --quiet --with lxml python scripts/pruefen.py

# Die Browserpruefung lief bisher nur, wenn jemand daran dachte — und daran
# dachte lange niemand. Sie ist die einzige Stelle, an der die Seiten in einer
# echten Engine geoeffnet werden: Ueberlauf, Tippgroessen und das JavaScript
# der Tagesmarke sieht sonst nichts.
#
# Sie darf den Lauf aber nicht aufhalten. Zu pruefen, ob sich playwright
# *importieren* laesst, genuegt dafuer nicht: Die Browser selbst liegen in
# ~/Library/Caches/ms-playwright und wandern nicht mit, wenn `--with
# playwright` eine neuere Version aufloest. Der Import gelingt dann, der Start
# scheitert — und mit `set -e` waere der ganze Lauf zu Ende, nach dem Bauen
# und vor dem Veroeffentlichen. Deshalb wird der Rueckgabewert abgefangen.
log "Browserpruefung (Chromium und WebKit)"
set +e
uv run --quiet --with playwright python scripts/pruefe_mobil.py
RC=$?
set -e
case $RC in
  0) ;;
  2) # Nur dieser Fall ist ein Einrichtungsstand: Das Skript meldet ihn mit
     # Exit 2, wenn sich kein Browser starten laesst.
     echo "   uebersprungen — die Seiten selbst sind davon unberuehrt."
     echo "   Die Pruefung nachholen, sobald die Browser wieder bereitstehen." ;;
  *) # Alles andere ist ein Befund an den Seiten. Ihn als „uebersprungen" zu
     # melden und trotzdem zu veroeffentlichen waere das Gegenteil der
     # Wahrheit — der Lauf endet hier.
     fehler "Browserpruefung fehlgeschlagen (Code $RC) — nicht veroeffentlicht." ;;
esac

# --- Veroeffentlichen ---------------------------------------------------------
# „Nichts Neues" war toter Code, seit der Seitenfuss auf jeder Seite den Tag
# des Laufs nennt: Ab Mitternacht unterscheiden sich alle rund 150 Dokumente,
# auch wenn die Stadt nichts veroeffentlicht hat. Bei einem taeglichen Lauf
# haette das jeden Tag einen Commit erzeugt, dessen einzige Aenderung ein
# Datum in der Fusszeile ist — und die Historie waere binnen eines Jahres
# unbrauchbar.
#
# Gezaehlt werden deshalb nur Zeilen, die etwas anderes sagen als „aktualisiert
# am". Bleibt keine uebrig, wird der Lauf verworfen: Die Dokumente sind
# inhaltlich dieselben wie beim letzten Mal.
if [[ -z "$(git status --porcelain)" ]]; then
  log "Nichts Neues — keine Aenderung gegenueber dem letzten Lauf."
  exit 0
fi

INHALTLICH=$(git diff -U0 | grep -E '^[-+][^-+]' | grep -cv 'aktualisiert am' || true)
if [[ "$INHALTLICH" -eq 0 && -z "$(git status --porcelain --untracked-files=all | grep -v '^ M')" ]]; then
  if [[ $TROCKEN -eq 1 ]]; then
    # Ein Trockenlauf aendert nichts — auch nicht durch Aufraeumen. Ohne
    # diese Abfrage haette „--trocken" den Arbeitsstand verworfen, sobald
    # zufaellig nur Fusszeilendaten abwichen: genau das Gegenteil dessen,
    # was ein Trockenlauf zusagt.
    log "Trockenlauf — nur das Datum in den Fusszeilen weicht ab. Nichts veraendert."
    exit 0
  fi
  log "Nichts Neues — nur das Datum in den Fusszeilen. Aenderungen verworfen."
  git checkout -- .
  exit 0
fi

if [[ $TROCKEN -eq 1 ]]; then
  log "Trockenlauf — folgende Aenderungen waeren zu committen:"
  git status --short
  exit 0
fi

AUSGABE=$(uv run --quiet python -c "
import json
r = json.load(open('data/ausgaben.json'))
jahr = max(r, key=int); kw = max(r[jahr], key=int)
print(f'KW {int(kw)}/{jahr}')")

log "Committen und pushen — $AUSGABE"
git add -A
git commit -q -F - <<EOF
Aktenlage aktualisiert: $AUSGABE

Lauf vom $(date +%d.%m.%Y). Neu geladen wurden Sitzungen, Tagesordnungen und
seither veroeffentlichte Beschlussprotokolle; Ausgaben, Archiv, Startseite und
Tabellen wurden daraus neu erzeugt.

Aeltere Ausgaben koennen sich mitveraendert haben, wenn ein Protokoll
nachgereicht wurde.
EOF
git push -q origin main
echo "   fertig — $(git log --oneline -1)"
