from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ─────────────────────────────
#  SCORING ENGINE
# ─────────────────────────────
def calculate_points(stats):
    pts, breakdown = 0, []
    runs      = int(stats.get("runs", 0) or 0)
    fours     = int(stats.get("fours", 0) or 0)
    sixes     = int(stats.get("sixes", 0) or 0)
    wickets   = int(stats.get("wickets", 0) or 0)
    maidens   = int(stats.get("maidens", 0) or 0)
    catches   = int(stats.get("catches", 0) or 0)
    stumpings = int(stats.get("stumpings", 0) or 0)
    runouts   = int(stats.get("runouts", 0) or 0)
    hattrick  = bool(stats.get("hattrick", False))

    if runs > 0:     pts += runs;         breakdown.append(f"{runs}R +{runs}")
    if fours > 0:    pts += fours;        breakdown.append(f"{fours}x4 +{fours}")
    if sixes > 0:    pts += sixes * 2;    breakdown.append(f"{sixes}x6 +{sixes*2}")
    if runs >= 100:  pts += 40;           breakdown.append("100 bonus +40")
    elif runs >= 50: pts += 30;           breakdown.append("50 bonus +30")

    if wickets >= 1:
        base = min(wickets, 3)
        pts += base * 20
        breakdown.append(f"{base}wkt +{base*20}")
    if wickets >= 3:  pts += 10;          breakdown.append("3+wkt bonus +10")
    if wickets >= 4:  pts += 30;          breakdown.append("4th wkt +30")
    if wickets >= 5:  pts += 50;          breakdown.append("5th wkt +50")
    if maidens > 0:   pts += maidens*10;  breakdown.append(f"{maidens} maiden +{maidens*10}")
    if hattrick:      pts += 50;          breakdown.append("hattrick +50")

    if catches > 0:   pts += catches*10;    breakdown.append(f"{catches} catch +{catches*10}")
    if stumpings > 0: pts += stumpings*10;  breakdown.append(f"{stumpings} stump +{stumpings*10}")
    if runouts > 0:   pts += runouts*10;    breakdown.append(f"{runouts} ro +{runouts*10}")

    return pts, " · ".join(breakdown) if breakdown else "DNP"

# ─────────────────────────────
#  SCORECARD PARSER
# ─────────────────────────────
def fetch_and_parse(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.espncricinfo.com/",
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    players = {}

    def get_or_create(name):
        if name not in players:
            players[name] = {"runs":0,"fours":0,"sixes":0,"wickets":0,"maidens":0,
                             "catches":0,"stumpings":0,"runouts":0,"hattrick":False}
        return players[name]

    for table in soup.select("table"):
        for row in table.select("tr"):
            cells = [td.get_text(strip=True) for td in row.select("td")]
            if len(cells) < 5: continue
            name_el = row.select_one("td a")
            if not name_el: continue
            name = name_el.get_text(strip=True)
            if not name or name in ("Extras","Total","Fall of wickets"): continue

            # Batting row
            try:
                runs_v  = cells[2] if len(cells) > 2 else ""
                balls_v = cells[3] if len(cells) > 3 else ""
                if runs_v.lstrip('-').isdigit() and balls_v.isdigit():
                    p = get_or_create(name)
                    p["runs"]  = max(p["runs"],  max(int(runs_v), 0))
                    p["fours"] = max(p["fours"], int(cells[4]) if cells[4].isdigit() else 0)
                    p["sixes"] = max(p["sixes"], int(cells[5]) if len(cells)>5 and cells[5].isdigit() else 0)
                    d = cells[1].lower() if len(cells) > 1 else ""
                    if "c " in d and " b " in d:
                        f = re.sub(r'^c\s+','', d.split(" b ")[0]).strip()
                        for pn in list(players):
                            if pn.lower().split()[-1] in f or f in pn.lower():
                                players[pn]["catches"] += 1; break
                    elif "st " in d and " b " in d:
                        f = re.sub(r'^st\s+','', d.split(" b ")[0]).strip()
                        for pn in list(players):
                            if pn.lower().split()[-1] in f or f in pn.lower():
                                players[pn]["stumpings"] += 1; break
                    elif "run out" in d:
                        m2 = re.search(r'\(([^)]+)\)', d)
                        if m2:
                            f = m2.group(1).strip()
                            for pn in list(players):
                                if pn.lower().split()[-1] in f or f in pn.lower():
                                    players[pn]["runouts"] += 1; break
            except: pass

            # Bowling row
            try:
                overs_v = cells[1] if len(cells) > 1 else ""
                if re.match(r'^\d+(\.\d)?$', overs_v):
                    p = get_or_create(name)
                    p["wickets"] += int(cells[4]) if cells[4].isdigit() else 0
                    p["maidens"] += int(cells[2]) if cells[2].isdigit() else 0
            except: pass

    return players

def find_player(name, all_players):
    nl = name.lower().strip()
    for p in all_players:
        if p.lower() == nl: return p
    last = nl.split()[-1]
    for p in all_players:
        if last in p.lower(): return p
    first = nl.split()[0]
    for p in all_players:
        if first in p.lower(): return p
    return None

# ─────────────────────────────
#  ENDPOINTS
# ─────────────────────────────
@app.route("/")
def home():
    return jsonify({"status": "IPL Fantasy Calculator API is running! 🏏"})

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

@app.route("/calculate", methods=["POST", "OPTIONS"])
def calculate():
    if request.method == "OPTIONS":
        return make_response("", 204)
    try:
        body = request.get_json(force=True)
        url  = body.get("url", "")
        chotu_players  = body.get("chotu", [])
        dhakan_players = body.get("dhakan", [])
        if not url:
            return jsonify({"error": "No URL provided"}), 400

        all_players = fetch_and_parse(url)

        def process(plist):
            results, total = [], 0
            for name in plist:
                if not name: continue
                matched = find_player(name, all_players)
                pts, detail = calculate_points(all_players[matched]) if matched else (0, "Not found/DNP")
                total += pts
                results.append({"name": name, "pts": pts, "detail": detail})
            return results, total

        c_brk, c_tot = process(chotu_players)
        d_brk, d_tot = process(dhakan_players)
        return jsonify({
            "success": True,
            "chotu":  {"total": c_tot, "breakdown": c_brk},
            "dhakan": {"total": d_tot, "breakdown": d_brk}
        })
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Scorecard fetch failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
