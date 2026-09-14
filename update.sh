#!/bin/zsh
# Holt die aktuellen Super-League-Daten von der Swisstxt-API und baut
# super-league-dashboard.html neu. Publiziert NICHT — das macht Claude
# (siehe README.md, Abschnitt "Aktualisieren").
#
# Exit-Code 0 = Daten haben sich geaendert (Dashboard sollte neu publiziert werden)
# Exit-Code 1 = Fehler
# Exit-Code 2 = keine Aenderung, nichts zu tun

cd "${0:A:h}" || exit 1
LOG="update.log"
PY="${PY:-/usr/bin/python3}"

# Log bei 200 KB rotieren, damit es nicht unbegrenzt waechst
if [[ -f "$LOG" ]] && [[ $(wc -c < "$LOG") -gt 204800 ]]; then
  mv "$LOG" "$LOG.1"
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S')"

  OUT=$("$PY" build.py 2>&1)
  STATUS=$?
  echo "$OUT"

  if [[ $STATUS -ne 0 ]]; then
    echo "-> Build fehlgeschlagen."
    exit 1
  fi

  if echo "$OUT" | grep -q '^CHANGED$'; then
    date '+%Y-%m-%d %H:%M:%S' > .needs-publish
    echo "-> Neue Daten. Marker .needs-publish gesetzt."
    exit 0
  fi

  echo "-> Keine neuen Daten."
  exit 2
} >> "$LOG" 2>&1
