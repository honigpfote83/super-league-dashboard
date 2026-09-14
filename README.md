# Super League Dashboard

Punkteverlauf und abgeleitete Statistiken der Schweizer Super League, gerechnet aus
den Einzelresultaten des SRF Resultcenters.

**Live:** https://claude.ai/code/artifact/7996fa1d-ab32-48f8-93b3-84defa8d0bab

## Dateien

| Datei | Zweck |
|---|---|
| `build.py` | Holt die Daten, prüft sie und rendert das Dashboard. Einziges Skript, das man braucht. |
| `template.html` | Die Seite. Enthält den Platzhalter `__DATA__`, den `build.py` mit den Daten füllt. |
| `clubs.json` | Vereinsfarben (`ink`) und Logodateinamen. Von Hand gepflegt. |
| `logos/` | Original-Logodateien von FootyLogos.com. Werden nicht verändert. |
| `web-logos/` | Von `build.py` erzeugte, publizierbare Kopien (SVGs ohne DOCTYPE/Skripte). Nicht von Hand bearbeiten. |
| `data.json` | Letzter Datenstand inkl. Fingerabdruck für die Änderungserkennung. |
| `super-league-dashboard.html` | Das fertige Dashboard. Diese Datei wird publiziert. |
| `update.sh` | Ruft `build.py` auf und protokolliert nach `update.log`. Für den Zeitplan gedacht. |

## Aktualisieren

```sh
python3 build.py
```

Gibt am Ende `CHANGED` oder `UNCHANGED` aus. Bei `CHANGED` das Dashboard neu publizieren —
in Claude Code in diesem Ordner genügt:

> Publiziere das Dashboard neu.

Claude ruft dann das Artifact-Tool mit `file_path=super-league-dashboard.html` und der
oben genannten URL auf. Die Logos in `web-logos/` müssen nur mit, wenn sich dort etwas
geändert hat — sonst bleiben die bereits publizierten Dateien bestehen.

`update.sh` macht dasselbe wie `build.py`, schreibt aber zusätzlich `update.log` und legt
bei neuen Daten die Markerdatei `.needs-publish` an.

## Wie die Daten geholt werden

Die SRF-Seite rendert alles per JavaScript; ein einfacher Seitenabruf liefert nichts.
`build.py` spricht deshalb direkt die öffentliche Sport-API von Swisstxt an, die dahinter
steckt:

1. `GET /v1/football/super-league?lang=de` — liefert die Wettbewerbsstruktur. Daraus werden
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
