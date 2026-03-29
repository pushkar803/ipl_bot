#!/usr/bin/env python3
"""Flask web server for Cricket Match Prediction Engine."""

import markdown
import requests as req_lib

from flask import Flask, render_template, redirect, url_for, jsonify

import db
from config import OPENAI_API_KEY, SPODA_AUTH_COOKIE, BASE_URL, HEADERS, COOKIES, SECRET_KEY, FLASK_DEBUG
from api_client import SpodaAPI
from analyzer import get_ai_analysis

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0 if FLASK_DEBUG else 31536000
db.init_db()
api = SpodaAPI()


def validate_spoda_connection() -> dict:
    """Check if the Spoda auth cookie is set and the API responds."""
    if not SPODA_AUTH_COOKIE:
        return {"ok": False, "error": "SPODA_AUTH_COOKIE is not set in your .env file."}

    try:
        resp = req_lib.get(
            f"{BASE_URL}/match-overview/matches",
            headers=HEADERS,
            cookies=COOKIES,
            timeout=15,
        )
        if resp.status_code == 401:
            return {"ok": False, "error": "Spoda auth cookie is expired or invalid (401 Unauthorized)."}
        if resp.status_code == 403:
            return {"ok": False, "error": "Spoda auth cookie was rejected (403 Forbidden)."}
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            return {"ok": False, "error": f"Spoda API returned error code {data.get('code')}: {data.get('message', 'Unknown error')}"}
        return {"ok": True, "error": None}
    except req_lib.ConnectionError:
        return {"ok": False, "error": "Cannot connect to api.spoda.ai. Check your internet connection."}
    except req_lib.Timeout:
        return {"ok": False, "error": "Connection to api.spoda.ai timed out."}
    except Exception as e:
        return {"ok": False, "error": f"Spoda connection check failed: {e}"}


_spoda_status = validate_spoda_connection()


@app.context_processor
def inject_status():
    return {
        "spoda_ok": _spoda_status["ok"],
        "spoda_error": _spoda_status["error"],
        "openai_available": bool(OPENAI_API_KEY),
    }

TEAM_COLORS = {
    "Mumbai Indians": {"bg": "#004BA0", "text": "#fff", "abbr": "MI"},
    "Chennai Super Kings": {"bg": "#FFCB05", "text": "#000", "abbr": "CSK"},
    "Kolkata Knight Riders": {"bg": "#3A225D", "text": "#fff", "abbr": "KKR"},
    "Royal Challengers Bengaluru": {"bg": "#D4213D", "text": "#fff", "abbr": "RCB"},
    "Rajasthan Royals": {"bg": "#EA1A85", "text": "#fff", "abbr": "RR"},
    "Sunrisers Hyderabad": {"bg": "#FF822A", "text": "#000", "abbr": "SRH"},
    "Delhi Capitals": {"bg": "#004C93", "text": "#fff", "abbr": "DC"},
    "Punjab Kings": {"bg": "#ED1B24", "text": "#fff", "abbr": "PBKS"},
    "Gujarat Titans": {"bg": "#1C1C2B", "text": "#fff", "abbr": "GT"},
    "Lucknow Super Giants": {"bg": "#A72056", "text": "#fff", "abbr": "LSG"},
}

TEAM_DEFAULT = {"bg": "#374151", "text": "#fff", "abbr": "??"}


def team_meta(name: str) -> dict:
    return TEAM_COLORS.get(name, {**TEAM_DEFAULT, "abbr": name[:3].upper()})


def build_match(raw: dict) -> dict:
    t1 = raw["teamName1"]
    t2 = raw["teamName2"]
    return {
        "match_id": raw["matchId"],
        "series_name": raw["seriesName"],
        "title": raw["title"],
        "team_name1": t1,
        "team_name2": t2,
        "team_id1": raw["teamId1"],
        "team_id2": raw["teamId2"],
        "ground_id": raw["groundId"],
        "ground": raw["ground"],
        "start_date": raw["startDate"],
        "season": raw["season"],
        "series_id": raw["seriesId"],
        "team1_meta": team_meta(t1),
        "team2_meta": team_meta(t2),
    }


@app.route("/")
def index():
    if not _spoda_status["ok"]:
        return render_template("index.html", today=[], tomorrow=[], data_date="")

    try:
        data = api.get_matches()
    except Exception as e:
        _spoda_status["ok"] = False
        _spoda_status["error"] = f"Failed to fetch matches: {e}"
        return render_template("index.html", today=[], tomorrow=[], data_date="")

    today = [build_match(m) for m in data.get("todaysMatches", [])]
    tomorrow = [build_match(m) for m in data.get("tomorrowsMatches", [])]
    return render_template(
        "index.html",
        today=today,
        tomorrow=tomorrow,
        data_date=data.get("today", ""),
    )


@app.route("/predict/<int:match_id>")
def predict(match_id: int):
    if not _spoda_status["ok"]:
        return render_template("error.html", title="Spoda Connection Error",
                               message=_spoda_status["error"])

    try:
        data = api.get_matches()
    except Exception as e:
        return render_template("error.html", title="API Error",
                               message=f"Failed to fetch match data: {e}")

    all_matches = data.get("todaysMatches", []) + data.get("tomorrowsMatches", [])
    raw = next((m for m in all_matches if m["matchId"] == match_id), None)

    if not raw:
        return redirect(url_for("index"))

    match = build_match(raw)
    full = api.fetch_full_match_data({
        "match_id": match["match_id"],
        "series_id": match["series_id"],
        "series_name": match["series_name"],
        "title": match["title"],
        "season": match["season"],
        "team_id1": match["team_id1"],
        "team_name1": match["team_name1"],
        "team_id2": match["team_id2"],
        "team_name2": match["team_name2"],
        "ground_id": match["ground_id"],
        "ground": match["ground"],
        "start_date": match["start_date"],
    })

    prob1 = full.get("win_prob_team1", {})
    prob2 = full.get("win_prob_team2", {})
    p1 = prob1.get("probability", 0) if prob1 else 0
    p2 = prob2.get("probability", 0) if prob2 else 0

    winner_stats = []
    ws = full.get("winner_stats")
    if ws and ws.get("stats"):
        winner_stats = ws["stats"]

    top_batsmen = []
    tb = full.get("top_batsmen")
    if tb and tb.get("probability"):
        top_batsmen = sorted(tb["probability"], key=lambda x: x.get("probability", 0), reverse=True)[:12]

    batsmen_stats = []
    bs = full.get("batsmen_stats")
    if bs and bs.get("stats"):
        batsmen_stats = bs["stats"]

    top_bowlers = []
    tbl = full.get("top_bowlers")
    if tbl and tbl.get("probability"):
        top_bowlers = sorted(tbl["probability"], key=lambda x: x.get("probability", 0), reverse=True)[:12]

    bowler_stats = []
    bos = full.get("bowler_stats")
    if bos and bos.get("stats"):
        bowler_stats = bos["stats"]

    venue_win_pct = {}
    wp = full.get("winning_pct")
    if wp:
        wd = wp.get("widgets", {}).get("widgets_data", [])
        if wd and wd[0].get("data"):
            d = wd[0]["data"][0]
            venue_win_pct = {
                "name": wd[0].get("title", ""),
                "bat_first": d.get("Batting First", 0),
                "bat_second": d.get("Batting Second", 0),
            }

    par_score = None
    ps = full.get("par_score")
    if ps:
        pd = ps.get("widgets", {}).get("widgets_data", [])
        if pd and pd[0].get("data"):
            par_score = pd[0]["data"][0].get("Batting First")

    phase_form = _extract_phase_form(full.get("team_analysis"), match["team_name1"], match["team_name2"])
    ground_batting = _extract_ground_batting(full.get("team_analysis"))
    boundary_pct = _extract_boundary_pct(full.get("team_analysis"))

    return render_template(
        "prediction.html",
        match=match,
        prob1=p1,
        prob2=p2,
        winner_stats=winner_stats,
        top_batsmen=top_batsmen,
        batsmen_stats=batsmen_stats,
        top_bowlers=top_bowlers,
        bowler_stats=bowler_stats,
        venue_win_pct=venue_win_pct,
        par_score=par_score,
        phase_form=phase_form,
        ground_batting=ground_batting,
        boundary_pct=boundary_pct,
        ai_available=bool(OPENAI_API_KEY),
    )


@app.route("/api/ai-analysis/<int:match_id>", methods=["POST"])
def ai_analysis(match_id: int):
    data = api.get_matches()
    all_matches = data.get("todaysMatches", []) + data.get("tomorrowsMatches", [])
    raw = next((m for m in all_matches if m["matchId"] == match_id), None)

    if not raw:
        return "<p class='text-error'>Match not found.</p>"

    match = build_match(raw)
    full = api.fetch_full_match_data({
        "match_id": match["match_id"],
        "series_id": match["series_id"],
        "series_name": match["series_name"],
        "title": match["title"],
        "season": match["season"],
        "team_id1": match["team_id1"],
        "team_name1": match["team_name1"],
        "team_id2": match["team_id2"],
        "team_name2": match["team_name2"],
        "ground_id": match["ground_id"],
        "ground": match["ground"],
        "start_date": match["start_date"],
    })

    analysis_md = get_ai_analysis(full)
    sections = _parse_ai_sections(analysis_md)
    return render_template("partials/ai_analysis.html", sections=sections)


SECTION_META = {
    "Match Winner Prediction": {
        "icon": "🏆",
        "border": "border-l-success",
        "badge": "badge-success",
    },
    "Key Factors": {
        "icon": "🔑",
        "border": "border-l-info",
        "badge": "badge-info",
    },
    "Players to Watch": {
        "icon": "⭐",
        "border": "border-l-warning",
        "badge": "badge-warning",
    },
    "Venue Impact": {
        "icon": "🏟️",
        "border": "border-l-secondary",
        "badge": "badge-secondary",
    },
    "Predicted Score Range": {
        "icon": "📊",
        "border": "border-l-primary",
        "badge": "badge-primary",
    },
    "Toss Decision": {
        "icon": "🪙",
        "border": "border-l-accent",
        "badge": "badge-accent",
    },
    "Betting Insights": {
        "icon": "💰",
        "border": "border-l-error",
        "badge": "badge-error",
    },
}

SECTION_DEFAULT_META = {"icon": "📌", "border": "border-l-base-content", "badge": "badge-ghost"}


def _parse_ai_sections(md_text: str) -> list[dict]:
    import re
    sections = []
    current_title = None
    current_lines: list[str] = []

    for line in md_text.split("\n"):
        header_match = re.match(r"^##\s+(.+)$", line.strip())
        if header_match:
            if current_title is not None:
                body = "\n".join(current_lines).strip()
                body_html = markdown.markdown(body, extensions=["tables", "fenced_code"])
                meta = SECTION_META.get(current_title, SECTION_DEFAULT_META)
                sections.append({"title": current_title, "html": body_html, **meta})
            current_title = header_match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_title is not None:
        body = "\n".join(current_lines).strip()
        body_html = markdown.markdown(body, extensions=["tables", "fenced_code"])
        meta = SECTION_META.get(current_title, SECTION_DEFAULT_META)
        sections.append({"title": current_title, "html": body_html, **meta})

    return sections


def _extract_phase_form(team_analysis, t1, t2):
    if not team_analysis:
        return []
    results = []
    for widget in team_analysis:
        if widget.get("widgetName") != "team_average_run_scored":
            continue
        last5 = widget.get("widgets", {}).get("Last_5_matches", {})
        for key, label in [("powerPlay", "Powerplay"), ("middleOver", "Middle Overs"), ("deathOver", "Death Overs")]:
            phase = last5.get(key, [])
            if not phase:
                continue
            entries = phase[0].get("data", [])
            if not entries:
                continue
            a1 = sum(e.get(t1, 0) for e in entries) / len(entries)
            a2 = sum(e.get(t2, 0) for e in entries) / len(entries)
            results.append({"phase": label, "team1_avg": round(a1, 1), "team2_avg": round(a2, 1)})
    return results


def _extract_ground_batting(team_analysis):
    if not team_analysis:
        return []
    for widget in team_analysis:
        if widget.get("widgetName") != "team_runs_in_ground":
            continue
        batting = widget.get("widgets", {}).get("Batting", [])
        results = []
        for td in batting:
            team = td.get("title", "")
            first = second = None
            for e in td.get("data", []):
                if e.get("value") is not None:
                    if "First Innings" in e.get("match", ""):
                        first = e["value"]
                    elif "Second Innings" in e.get("match", ""):
                        second = e["value"]
            results.append({"team": team, "first": first, "second": second})
        return results
    return []


def _extract_boundary_pct(team_analysis):
    if not team_analysis:
        return []
    for widget in team_analysis:
        if widget.get("widgetName") != "team_boundaries_percentage":
            continue
        batting = widget.get("widgets", {}).get("Batting", [])
        results = []
        for td in batting:
            team = td.get("title", "")
            fours = sixes = None
            for e in td.get("data", []):
                val = e.get("value")
                label = e.get("match", "")
                if val is not None:
                    if "4" in label and "6" not in label:
                        fours = val
                    elif "6" in label:
                        sixes = val
            results.append({"team": team, "fours": fours, "sixes": sixes})
        return results
    return []


@app.route("/api/recheck-spoda", methods=["POST"])
def recheck_spoda():
    global _spoda_status
    _spoda_status = validate_spoda_connection()
    if _spoda_status["ok"]:
        return '<script>window.location.href="/";</script>'
    return render_template("partials/spoda_error_banner.html")


if __name__ == "__main__":
    print("\n  Cricket Prediction Engine -> http://localhost:5050\n")
    app.run(debug=FLASK_DEBUG, port=5050)
