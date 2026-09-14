# Super League Dashboard

Punkteverlauf und abgeleitete Statistiken der Schweizer Super League, gerechnet aus
den Einzelresultaten des SRF Resultcenters.

**Live:** https://claude.ai/code/artifact/7996fa1d-ab32-48f8-93b3-84defa8d0bab

## Aktualisieren

Claude Code in diesem Ordner starten und sagen:

> Aktualisiere das Dashboard.

Das ist alles. Claude ruft `python3 build.py` auf und publiziert bei neuen Daten neu.

Von Hand geht es genauso:

```sh
python3 build.py
```

Die letzte Ausgabezeile ist `CHANGED` oder `UNCHANGED`. Bei `CHANGED` muss
`super-league-dashboard.html` mit dem Artifact-Werkzeug auf die obige URL publiziert
werden (`file_path` und `url` setzen, sonst nichts — die bereits publizierten Logos
unter `web-logos/` bleiben dann erhalten).

Es läuft bewusst **kein** Zeitplan und keine Automatik.

## Dateien

| Datei | Zweck |
|---|---|
| `build.py` | Holt die Daten, prüft sie und rendert das Dashboard. Einziges Skript, das man braucht. |
| `template.html` | Die Seite. Enthält den Platzhalter `__DATA__`, den `build.py` mit den Daten füllt. |
| `clubs.json` | Vereinsfarben (`ink`) und Logodateinamen. Von Hand gepflegt. |
| `logos/` | Original-Logodateien von FootyLogos.com. Werden nie verändert. |
| `web-logos/` | Von `build.py` erzeugte, publizierbare Kopien (SVGs ohne DOCTYPE/Skripte). Nicht von Hand bearbeiten. |
| `data.json` | Letzter Datenstand inkl. Fingerabdruck für die Änderungserkennung. |
| `super-league-dashboard.html` | Das fertige Dashboard. Diese Datei wird publiziert. |

Ein neues Logo austauschen: Datei in `logos/` legen, den Namen in `clubs.json` eintragen,
`build.py` laufen lassen. Beim Publizieren muss die geänderte Datei aus `web-logos/` dann
einmal mitgegeben werden.

## Spieler, die die Liga verlassen

Wechselt ein Spieler waehrend der Saison aus der Liga, bleiben seine Tore in der Wertung,
aber die API nennt irgendwann keinen Verein mehr. Solche Spieler erscheinen weiterhin in
der Torschuetzenliste, mit ihrem letzten bekannten Verein und der Markierung `(ehem.)`.

`build.py` erkennt das auf zwei Wegen:

1. **Automatisch**, wenn die API keinen Verein mehr nennt. Das ist nur ein Indiz — die API
   laesst das Feld gelegentlich auch bei aktiven Spielern kurzzeitig weg. Die Markierung
   verschwindet daher von selbst wieder, sobald ein Verein zurueckkommt.
2. **Von Hand** ueber die Liste `departed` in `clubs.json`. Namen dort werden immer als
   ehemalig markiert, unabhaengig davon, was die API sagt. Name genau so schreiben wie in
   der Torschuetzenliste; Tippfehler meldet `build.py` als Warnung.

```json
"departed": ["Joël Monteiro", "Layton Stewart"]
```

Der letzte bekannte Verein stammt aus `data.json` des vorherigen Laufs. Loescht man
`data.json`, geht er verloren und der Spieler erscheint ohne Verein — dann aus der
Git-Historie zurueckholen.

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
