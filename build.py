#!/usr/bin/env python3
"""Holt die Super-League-Daten von der oeffentlichen Swisstxt-Sport-API,
baut data.json und rendert daraus super-league-dashboard.html.

Alles wird ab einem einzigen Einstiegspunkt entdeckt (Runden-Phasen und
Ranking-IDs), damit der Lauf auch nach einem Saisonwechsel oder nach der
Teilung in Championship-/Relegation-Group noch funktioniert.

Exit-Code 0 = fertig. Stdout endet auf "CHANGED" oder "UNCHANGED".
"""
import json, os, re, shutil, sys, time, urllib.request, urllib.error, hashlib

BASE = "https://sport.api.swisstxt.ch/v1"
CONTEST = os.environ.get("SL_CONTEST", "super-league")
HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 25
RETRIES = 3


def get(url):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "super-league-dashboard/1.0 (personal stats page)",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                if r.status == 204:
                    return None
                raw = r.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except Exception as e:                      # noqa: BLE001
            last = e
            if attempt < RETRIES - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("Abruf fehlgeschlagen: %s (%s)" % (url, last))


def walk_rounds(phase, trail, out):
    """Sammelt rekursiv alle Phasen vom Typ 'Round'."""
    for sub in phase.get("phases") or []:
        if sub.get("type") == "Round":
            out.append({"id": sub["id"], "name": sub.get("displayName", ""),
                        "group": trail, "state": sub.get("state")})
        else:
            walk_rounds(sub, sub.get("displayName", trail), out)


def collect_rankings(phase, out):
    for r in phase.get("rankings") or []:
        out.append(r)
    for sub in phase.get("phases") or []:
        collect_rankings(sub, out)


# ---------- Kontrastpruefung fuer die Vereinsfarben ----------
def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


LOGO_SRC = "logos"
LOGO_OUT = "web-logos"


def prepare_logo(filename, warnings):
    """Legt eine publizierbare Kopie des Logos in web-logos/ an.

    SVGs werden von DTD-Deklarationen, Kommentaren, Skripten und Event-Attributen
    befreit — der Artifact-Upload weist Dateien mit DOCTYPE/ENTITY sonst ab.
    Gibt den Pfad relativ zur Seite zurueck oder None.
    """
    src = os.path.join(HERE, LOGO_SRC, filename)
    if not os.path.exists(src):
        warnings.append("Logodatei fehlt: %s" % os.path.join(LOGO_SRC, filename))
        return None
    out_dir = os.path.join(HERE, LOGO_OUT)
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, filename)

    if filename.lower().endswith(".svg"):
        raw = open(src, encoding="utf-8", errors="replace").read()
        cleaned = re.sub(r"<!DOCTYPE[^>\[]*(\[.*?\])?\s*>", "", raw, flags=re.S | re.I)
        cleaned = re.sub(r"<!ENTITY.*?>", "", cleaned, flags=re.S | re.I)
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.S)
        cleaned = re.sub(r"<script\b.*?</script\s*>", "", cleaned, flags=re.S | re.I)
        cleaned = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", cleaned, flags=re.I)
        cleaned = cleaned.lstrip()
        if "<!DOCTYPE" in cleaned.upper() or "<!ENTITY" in cleaned.upper():
            warnings.append("SVG liess sich nicht bereinigen: %s" % filename)
            return None
        with open(dst, "w", encoding="utf-8") as f:
            f.write(cleaned)
    else:
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copyfile(src, dst)
    return LOGO_OUT + "/" + filename


def main():
    warnings = []

    contest = get("%s/football/%s?lang=de" % (BASE, CONTEST))
    if not contest:
        raise RuntimeError("Wettbewerb %s nicht gefunden" % CONTEST)

    rounds = []
    rankings_meta = []
    for phase in contest.get("phases") or []:
        walk_rounds(phase, phase.get("displayName", ""), rounds)
        collect_rankings(phase, rankings_meta)
    if not rounds:
        raise RuntimeError("Keine Runden gefunden")

    # Spiele je Runde
    matches = []
    for idx, rnd in enumerate(rounds, start=1):
        items = get("%s/eventItems?phaseIds=%s&lang=de" % (BASE, rnd["id"])) or []
        for x in items:
            if x.get("$type") != "Game" and x.get("type") != "Game":
                continue
            c1, c2 = x.get("competitor1") or {}, x.get("competitor2") or {}
            if not c1.get("name") or not c2.get("name"):
                continue
            sc = x.get("scores") or {}
            m = {
                "id": x.get("id"), "round": idx, "roundName": rnd["name"],
                "group": rnd["group"],
                "dt": (x.get("dateTimeInfo") or {}).get("fullDateTime"),
                "home": c1["name"], "homeShort": c1.get("shortName") or c1["name"],
                "away": c2["name"], "awayShort": c2.get("shortName") or c2["name"],
                "state": x.get("state"),
            }
            if x.get("state") == "Finished":
                main_s = sc.get("main") or {}
                fh = sc.get("firstHalf") or {}
                m["hg"] = main_s.get("competitor1")
                m["ag"] = main_s.get("competitor2")
                m["hg1"] = fh.get("competitor1")
                m["ag1"] = fh.get("competitor2")
                if m["hg"] is None or m["ag"] is None:
                    m["state"] = "Planned"          # Resultat fehlt -> nicht als gespielt zaehlen
                else:
                    if m["hg1"] is None or m["ag1"] is None:
                        m["hg1"], m["ag1"] = 0, 0
                        warnings.append("Halbzeitstand fehlt: %s - %s" % (m["home"], m["away"]))
                    sp = x.get("spectators")
                    m["spectators"] = int(sp) if sp and str(sp).isdigit() else None
                    m["stadium"] = x.get("stadium")
                    m["city"] = x.get("city")
                    m["referee"] = x.get("referees")
            matches.append(m)
    matches.sort(key=lambda m: (m["dt"] or "", m["round"]))

    # Rankings: offizielle Tabelle (zum Abgleich) und Torschuetzen
    main_rank = next((r for r in rankings_meta if r.get("type") == "Main"), None)
    scorer_rank = next((r for r in rankings_meta if r.get("type") == "Scorer"), None)

    official, remark = [], ""
    if main_rank:
        data = get("%s/rankings/%s?lang=de" % (BASE, main_rank["id"]))
        if data:
            remark = data.get("remark") or main_rank.get("remark") or ""
            for it in data.get("rankingItems") or []:
                c = it.get("competitor") or {}
                official.append({
                    "rank": it.get("rank"), "team": c.get("name"),
                    "games": it.get("games"), "points": it.get("points"),
                    "w": it.get("gamesWon"), "d": it.get("gamesDraw"), "l": it.get("gamesLost"),
                    "gf": it.get("goalPlus"), "ga": it.get("goalMinus"),
                    "gd": it.get("goalDifference"),
                })

    scorers = []
    if scorer_rank:
        data = get("%s/rankings/%s?lang=de" % (BASE, scorer_rank["id"]))
        for it in (data or {}).get("rankingItems") or []:
            c = it.get("competitor") or {}
            team = c.get("team") or {}
            scorers.append({
                "rank": it.get("rank"),
                "name": ((c.get("firstName") or "") + " " + (c.get("name") or "")).strip(),
                "team": team.get("shortName") or team.get("name") or "",
                "teamFull": team.get("name") or "",
                "goals": it.get("scorerGoals") or it.get("points") or 0,
                "country": c.get("countryName"),
            })

    # Teams aus den Spielen ableiten (nicht aus der Tabelle) -> ueberlebt Saisonstart
    names = sorted({m["home"] for m in matches} | {m["away"] for m in matches})
    shorts = {}
    for m in matches:
        shorts[m["home"]] = m["homeShort"]
        shorts[m["away"]] = m["awayShort"]
    teams = [{"name": n, "short": shorts.get(n, n)} for n in names]

    # Vereinsfarben anhaengen
    cfg = json.load(open(os.path.join(HERE, "clubs.json"), encoding="utf-8"))
    club_map, fallback = cfg["clubs"], cfg["fallback"]
    SURFACE_LIGHT, SURFACE_DARK = "#fdfcfc", "#1b1a19"
    for t in teams:
        club = club_map.get(t["name"])
        if club is None:
            club = dict(fallback)
            warnings.append("Kein Eintrag fuer '%s' in clubs.json — Platzhalter benutzt" % t["name"])
        club = dict(club)
        if club.get("logo"):
            web = prepare_logo(club["logo"], warnings)
            if web:
                club["logo"] = web
            else:
                club.pop("logo", None)
        else:
            warnings.append("Kein Logo hinterlegt fuer '%s'" % t["name"])
        t["club"] = club
        cl = contrast(club["ink"][0], SURFACE_LIGHT)
        cd = contrast(club["ink"][1], SURFACE_DARK)
        if cl < 3.0:
            warnings.append("Kontrast zu schwach (hell, %.2f:1) fuer %s" % (cl, t["name"]))
        if cd < 3.0:
            warnings.append("Kontrast zu schwach (dunkel, %.2f:1) fuer %s" % (cd, t["name"]))

    finished = [m for m in matches if m["state"] == "Finished"]

    # Eigene Tabelle rechnen und gegen die offizielle pruefen
    calc = {}
    for t in teams:
        calc[t["name"]] = {"sp": 0, "pts": 0, "gf": 0, "ga": 0}
    for m in finished:
        h, a = calc[m["home"]], calc[m["away"]]
        h["sp"] += 1; a["sp"] += 1
        h["gf"] += m["hg"]; h["ga"] += m["ag"]
        a["gf"] += m["ag"]; a["ga"] += m["hg"]
        if m["hg"] > m["ag"]:
            h["pts"] += 3
        elif m["hg"] < m["ag"]:
            a["pts"] += 3
        else:
            h["pts"] += 1; a["pts"] += 1
    mismatches = []
    for o in official:
        c = calc.get(o["team"])
        if not c:
            continue
        if (c["sp"], c["pts"], c["gf"], c["ga"]) != (o["games"], o["points"], o["gf"], o["ga"]):
            mismatches.append("%s: berechnet %s/%s %s:%s, offiziell %s/%s %s:%s" % (
                o["team"], c["sp"], c["pts"], c["gf"], c["ga"],
                o["games"], o["points"], o["gf"], o["ga"]))
    if mismatches:
        warnings.append("Tabelle weicht von SRF ab: " + " | ".join(mismatches))

    out = {
        "season": contest.get("year"),
        "competition": contest.get("displayName", "Super League"),
        "source": "SRF Resultcenter / sport.api.swisstxt.ch",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "teams": teams, "matches": matches, "scorers": scorers,
        "official": official, "remark": remark,
        "rounds": [{"index": i, "name": r["name"], "group": r["group"]}
                   for i, r in enumerate(rounds, start=1)],
        "verified": not mismatches and bool(official),
        "warnings": warnings,
    }

    # Fingerabdruck nur ueber die Substanz, nicht ueber den Zeitstempel
    payload = json.dumps({k: v for k, v in out.items() if k not in ("updated", "warnings")},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    out["fingerprint"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    prev_fp, prev_updated = None, None
    data_path = os.path.join(HERE, "data.json")
    if os.path.exists(data_path):
        try:
            prev = json.load(open(data_path, encoding="utf-8"))
            prev_fp, prev_updated = prev.get("fingerprint"), prev.get("updated")
        except Exception:                            # noqa: BLE001
            pass

    changed = out["fingerprint"] != prev_fp
    out["checked"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    if not changed and prev_updated:
        out["updated"] = prev_updated               # Stand = letzte echte Aenderung

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    html_path = os.path.join(HERE, "super-league-dashboard.html")
    tpl_path = os.path.join(HERE, "template.html")
    tpl = open(tpl_path, encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    # Auch neu rendern, wenn das Template neuer ist als die Ausgabe oder diese fehlt
    stale = (not os.path.exists(html_path)
             or os.path.getmtime(tpl_path) > os.path.getmtime(html_path))
    if changed or stale:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        changed = True

    print("Runden: %d | Spiele: %d (%d gespielt) | Teams: %d | Tabelle geprueft: %s"
          % (len(rounds), len(matches), len(finished), len(teams),
             "ja" if out["verified"] else "NEIN"))
    for w in warnings:
        print("  WARNUNG: %s" % w, file=sys.stderr)
    print("CHANGED" if changed else "UNCHANGED")


if __name__ == "__main__":
    main()
