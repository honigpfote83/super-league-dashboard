#!/usr/bin/env python3
"""Entscheidet, ob build.py jetzt laufen soll. Fragt selbst keine API ab.

Der Workflow startet alle 10 Minuten. Die Swisstxt-API wird aber nur dann
abgefragt, wenn gerade ein Spiel laeuft oder kurz bevorsteht — sonst genuegt
der stuendliche Lauf (eigener Cron-Eintrag, siehe update.yml).

Ausgabe fuer $GITHUB_OUTPUT: "run=true" oder "run=false".
"""
import datetime as dt, json, os, sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo("Europe/Zurich")          # Anstosszeiten der API sind Schweizer Ortszeit
BEFORE = dt.timedelta(minutes=10)
AFTER = dt.timedelta(minutes=150)       # 90 Min. + Pause + Nachspielzeit + Puffer


def match_window(now):
    try:
        data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    except Exception:                    # noqa: BLE001 — ohne Daten lieber laufen
        return "keine data.json"
    for m in data.get("matches") or []:
        if m.get("state") == "Finished" or not m.get("dt"):
            continue
        kickoff = dt.datetime.fromisoformat(m["dt"]).replace(tzinfo=TZ)
        if kickoff - BEFORE <= now <= kickoff + AFTER:
            return "%s - %s (%s)" % (m["home"], m["away"], m["dt"][11:16])
    return None


def main():
    if "--force" in sys.argv:
        reason = "erzwungen"
    else:
        reason = match_window(dt.datetime.now(TZ))
    print("run=%s" % ("true" if reason else "false"))
    print("Lauf: %s" % (reason or "nein, kein Spiel im Zeitfenster"), file=sys.stderr)


if __name__ == "__main__":
    main()
