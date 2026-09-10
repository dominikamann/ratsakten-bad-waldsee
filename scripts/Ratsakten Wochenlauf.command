#!/usr/bin/env bash
#
# Doppelklick-Starter für den Wochenlauf.
#
# Liegt auf dem Schreibtisch und öffnet ein Terminalfenster. Von Hand gestartet
# gilt der Zugriffsschutz von macOS nicht — anders als beim zeitgesteuerten Lauf
# über launchd, der auf ~/Documents nicht zugreifen darf.
#
PROJEKT="$HOME/Documents/AmannLabs/ratsakten-bad-waldsee"

cd "$PROJEKT" 2>/dev/null || {
  echo "Projektordner nicht gefunden: $PROJEKT"
  echo "Pfad in dieser Datei anpassen."
  read -r -p "Eingabetaste zum Schließen "
  exit 1
}

printf '\033[1m Ratsakten Bad Waldsee — Wochenlauf \033[0m\n'
printf ' %s\n\n' "$(date '+%A, %d. %B %Y, %H:%M')"

./scripts/wochenlauf.sh
ERGEBNIS=$?

echo
if [ $ERGEBNIS -eq 0 ]; then
  printf '\033[32m Fertig.\033[0m\n'
else
  printf '\033[31m Abgebrochen (Code %s). Meldung oben lesen.\033[0m\n' "$ERGEBNIS"
fi
read -r -p " Eingabetaste zum Schließen "
