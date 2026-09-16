# Super League Dashboard

Punkteverlauf und abgeleitete Statistiken der Schweizer Super League, gerechnet aus
den Einzelresultaten des SRF Resultcenters.

**Live:** https://honigpfote83.github.io/super-league-dashboard/

## Wie die Seite aktuell bleibt

Alles läuft von selbst über GitHub Actions (`.github/workflows/update.yml`):

1. Der Workflow startet alle 10 Minuten. `due.py` schaut in `data.json`, ob gerade ein
   Spiel läuft oder in den nächsten 10 Minuten beginnt (Anstoss −10 bis +150 Min.). Nur dann
   wird die API abgefragt. Unabhängig davon gibt es einen stündlichen Lauf (Minute 7).
2. `build.py` holt die Daten wie bisher und prüft sie. Warnungen erscheinen als gelbe
   Hinweise im Actions-Protokoll.
3. Hat sich der Fingerabdruck geändert, committet der Workflow `data.json` und
   veröffentlicht die Seite neu auf GitHub Pages. Mit `index.html` wird eine kleine
   `version.json` ausgeliefert.
4. Die geöffnete Seite fragt beim Laden, alle 3 Minuten und beim Zurückwechseln in den Tab
   `version.json` ab. Gibt es einen neuen Stand, lädt sie sich neu und behält dabei die
   ausgewählten Teams, die x-Achse und die Scrollposition.

Jeder Push auf `main` (z.B. eine Änderung an `template.html` oder `clubs.json`) baut und
veröffentlicht sofort. Von Hand anstossen: Actions → „Dashboard aktualisieren“ → *Run workflow*,
oder `gh workflow run update.yml`.

Lokal ansehen:

```sh
python3 build.py
open super-league-dashboard.html
```

Die letzte Ausgabezeile ist `CHANGED` oder `UNCHANGED`. Die erzeugte HTML-Datei wird nicht
mehr eingecheckt, sie entsteht im Workflow.

**Hinweis:** GitHub deaktiviert zeitgesteuerte Workflows in öffentlichen Repos nach 60 Tagen
ohne Aktivität im Repo. In der Saison committet der Workflow laufend selbst. Nach einer
langen Pause (Sommer) im Tab *Actions* prüfen, ob der Workflow noch aktiv ist.

## Dateien

| Datei | Zweck |
|---|---|
| `build.py` | Holt die Daten, prüft sie und rendert das Dashboard. |
| `due.py` | Entscheidet ohne API-Abruf, ob ein Lauf gerade nötig ist. |
| `.github/workflows/update.yml` | Zeitplan, Build, Commit von `data.json`, Deploy auf Pages. |
| `template.html` | Die Seite. Enthält den Platzhalter `__DATA__`, den `build.py` mit den Daten füllt. |
| `clubs.json` | Vereinsfarben (`ink`) und Logodateinamen. Von Hand gepflegt. |
| `logos/` | Original-Logodateien von FootyLogos.com. Werden nie verändert. |
| `web-logos/` | Von `build.py` erzeugte, publizierbare Kopien (SVGs ohne DOCTYPE/Skripte). Nicht eingecheckt. |
| `goals.json` | Tore je Spiel (Spieler, Team, Minute). Grundlage fuer die Vereinszuordnung der Torschuetzen. Wird vom Workflow committet. |
| `data.json` | Letzter Datenstand inkl. Fingerabdruck für die Änderungserkennung. Wird vom Workflow committet. |

Ein neues Logo austauschen: Datei in `logos/` legen, den Namen in `clubs.json` eintragen,
committen und pushen.

## Spieler, die die Liga verlassen

Wechselt ein Spieler waehrend der Saison aus der Liga, bleiben seine Tore in der Wertung.
Solche Spieler erscheinen weiterhin in der Torschuetzenliste, mit ihrem letzten Verein und
der Markierung `(ehem.)`: Logo abgeschwaecht, Balken heller, Name gedaempft.

Verbindlich ist allein die Liste `departed` in `clubs.json`:

```json
"departed": ["Joël Monteiro", "Layton Stewart"]
```

Name genau so schreiben wie in der Torschuetzenliste; Tippfehler meldet `build.py` als
Warnung. Es gibt **keine** automatische Erkennung — siehe naechster Abschnitt.

## Vorsicht bei der Vereinszuordnung der Torschuetzen

Der Endpunkt `/v1/rankings/<Torschuetzen-ID>` ist bei der Vereinszuordnung unzuverlaessig.
Beobachtet am 14.09.2026 innerhalb weniger Minuten:

- Zan Celar wurde mal als Lugano, mal als Basel gemeldet.
- Layton Stewart und Joël Monteiro hatten zeitweise gar kein Team, kurz darauf wieder eines.
- Innerhalb eines Bursts von 20 Abrufen war die Antwort dagegen jedes Mal identisch — die
  Daten werden also stromaufwaerts umgeschrieben, sie flackern nicht pro Anfrage.

Daraus folgt: **Aus einem fehlenden Verein laesst sich nicht schliessen, dass ein Spieler
die Liga verlassen hat.** Eine frueher eingebaute Heuristik in diese Richtung wurde wieder
entfernt, weil sie nachweislich falsche Treffer produziert hat.

Den Verein bestimmt deshalb nicht diese Liste, sondern die Spiele selbst:
`/v1/games/<Spiel-ID>/incidents` nennt zu jedem Tor den Spieler und das Team, fuer das
es gezaehlt hat. Das ist eine Tatsache des Spiels und flackert nicht. Beim ersten Abgleich
(16.09.2026) ergaben die Tore aller 46 Spiele genau die Resultate, und die Anzahl je Spieler
stimmte mit der Torschuetzenliste ueberein.

`build.py` legt den Verein eines Torschuetzen in dieser Reihenfolge fest:

1. **`scorerClubs` in `clubs.json`**: nur fuer Ausnahmen, normalerweise leer.
2. **Das Team, fuer das er zuletzt getroffen hat.** Ein Transfer wird damit automatisch
   sichtbar, sobald der Spieler fuer den neuen Verein trifft; vorher steht er beim alten
   Verein, fuer den seine Tore ja auch zaehlen.
3. **Letzter bekannter Stand aus `data.json`**, danach erst die API.

Die Tore je Spiel liegen in `goals.json` (vom Workflow mit committet). Ein Spiel wird dort
nur gespeichert, wenn seine Tore das Resultat ergeben; Spiele der letzten 36 Stunden werden
bei jedem Lauf neu geholt, falls SRF nachtraeglich korrigiert. Zusaetzlich warnt `build.py`,
wenn die Toranzahl eines Spielers in der Liste nicht zu den Spielen passt.

Alle anderen Daten dieser Seite (Resultate, Tabelle, Tore, Zuschauer) stammen aus
`/v1/eventItems` und waren durchgehend stabil und mit dem offiziellen SRF-Klassement
deckungsgleich.

## Wie die Daten geholt werden

Die SRF-Seite rendert alles per JavaScript; ein einfacher Seitenabruf liefert nichts.
`build.py` spricht deshalb direkt die öffentliche Sport-API von Swisstxt an, die dahinter
steckt:

1. `GET /v1/football/super-league?lang=de` — die Wettbewerbsstruktur. Daraus werden
   **alle Runden-Phasen und die Ranking-IDs entdeckt**, nichts ist fest verdrahtet. Das
   überlebt einen Saisonwechsel und die Teilung in Championship-/Relegation-Group.
2. `GET /v1/eventItems?phaseIds=<Runde>&lang=de` — die Spiele je Runde, mit Halbzeitstand,
   Zuschauerzahl, Stadion und Schiedsrichter.
3. `GET /v1/rankings/<id>?lang=de` — offizielles Klassement (nur zum Abgleich) und
   Torschützenliste.

## Selbstkontrolle

`build.py` rechnet die Tabelle vollständig aus den Einzelresultaten neu und vergleicht sie
mit der offiziellen von SRF. Weichen Spiele, Punkte oder Tore ab, landet das als Warnung
auf stderr und `verified` in `data.json` wird `false`; die Seite weist dann im Fussbereich
darauf hin. Ebenfalls geprüft werden:

- fehlende Logodateien und Vereinseinträge,
- Kontrast der Vereinsfarben gegen helle und dunkle Seitenfläche (mindestens 3:1),
- fehlende Halbzeitstände.

## Farben

Die Diagrammfarben stammen aus einer auf Farbfehlsichtigkeit geprüften Palette und sind
bewusst **nicht** die Vereinsfarben — bei zwölf Teams mit vier Blautönen wäre nichts mehr
unterscheidbar. Vereinsfarben werden dort eingesetzt, wo pro Grafik nur eine Farbe nötig
ist: in den Einzelkacheln und als Balken in der Tabelle.

## Quellen

- Daten: SRF Resultcenter / `sport.api.swisstxt.ch`
- Vereinslogos: [FootyLogos.com](https://footylogos.com)
