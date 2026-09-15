#!/usr/bin/env bash
#
# Wochenlauf — holt nach, was seit der letzten Ausgabe erschienen ist, baut alle
# Dokumente neu und veroeffentlicht das Ergebnis.
#
# Laeuft bewusst lokal und nicht auf einem GitHub-Runner: Das
# Ratsinformationssystem beantwortet Anfragen aus Rechenzentrumsnetzen mit
# HTTP 503. Von einem privaten Anschluss aus antwortet es normal. Diese
# Beschraenkung wird nicht umgangen.
#
#   ./scripts/wochenlauf.sh              # holen, bauen, committen, pushen
#   ./scripts/wochenlauf.sh --trocken    # nur holen und bauen, nichts committen
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
log "1/12  Sitzungen und Tagesordnungen laden"
uv run --quiet --with requests --with beautifulsoup4 python scripts/01_sitzungen_laden.py

log "2/12  Neue Protokolle laden"
uv run --quiet --with requests python scripts/02_protokolle_laden.py

log "3/12  Kennzahlen berechnen"
uv run --quiet --with pypdf python scripts/03_auswerten.py | head -3

log "4/12  Ausgaben erzeugen (alle Jahrgänge)"
uv run --quiet --with pypdf python scripts/05_ausgaben_bauen.py | tail -2

log "5/12  Tabellen und Suche erzeugen"
uv run --quiet --with pypdf python scripts/07_tabellen_bauen.py | tail -4
uv run --quiet --with pypdf python scripts/08_suche_bauen.py

log "6/12  Themenseiten erzeugen"
uv run --quiet python scripts/11_themen_bauen.py

log "7/12  Terminseite erzeugen"
uv run --quiet python scripts/12_termine_bauen.py

log "8/12  Erkenntnisse sammeln"
uv run --quiet --with lxml python scripts/09_befunde_bauen.py

log "9/12  Seite „Wer entscheidet was“ erzeugen"
uv run --quiet python scripts/10_gremien_bauen.py

log "10/12  Startseite erzeugen"
uv run --quiet python scripts/06_startseite_bauen.py

log "11/12  Report vorrendern"
node scripts/04_vorrendern.js | tail -1

log "12/12  Kennzahlen in die README eintragen"
uv run --quiet python scripts/13_readme_pflegen.py

# --- Pruefen ------------------------------------------------------------------
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
if [[ -z "$(git status --porcelain)" ]]; then
  log "Nichts Neues — keine Aenderung gegenueber dem letzten Lauf."
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
