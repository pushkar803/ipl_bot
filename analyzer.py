import json

from openai import OpenAI

from config import OPENAI_API_KEY

SYSTEM_PROMPT = """You are an elite cricket analyst and match predictor with deep expertise in T20 cricket, IPL, PSL, and international tournaments. You provide sharp, data-backed predictions.

You MUST structure your response using EXACTLY these markdown sections with ## headers. Do not skip any section. Do not add extra sections.

## Match Winner Prediction
State the predicted winner clearly. Include a confidence percentage (e.g. 70%). One short sentence on why.

## Key Factors
- Use bullet points (3-5 items)
- Each point should be one concise sentence backed by a stat

## Players to Watch
- **Batter:** Name — one sentence on why, with a stat
- **Bowler:** Name — one sentence on why, with a stat

## Venue Impact
2-3 sentences on how the ground shapes this match. Reference par score, batting first/second advantage.

## Predicted Score Range
State the first innings score range (e.g. "175-190"). One sentence justification.

## Toss Decision
State whether to bat or bowl first. One sentence reason backed by venue win %.

## Betting Insights
- **Total Runs:** one-line pick
- **Top Scorer:** one-line pick
- **Top Wicket-Taker:** one-line pick

Be concise but insightful. Use the stats provided to back up every claim. Write in an engaging, authoritative tone. Take a clear stance — no hedging."""


def build_analysis_prompt(data: dict) -> str:
    match = data["match"]
    t1 = match.get("team_name1", "Team 1")
    t2 = match.get("team_name2", "Team 2")
    ground = match.get("ground", "Unknown")
    series = match.get("series_name", "")

    parts = [f"## Match: {t1} vs {t2}", f"Series: {series}", f"Venue: {ground}\n"]

    ws = data.get("winner_stats")
    if ws and ws.get("stats"):
        parts.append("## Winner Stats")
        for s in ws["stats"]:
            parts.append(f"- {s['title']}: {s['value']}")
        parts.append("")

    for label, key in [("team1", "win_prob_team1"), ("team2", "win_prob_team2")]:
        wp = data.get(key)
        team = t1 if label == "team1" else t2
        if wp and wp.get("probability") is not None:
            parts.append(f"Win Probability for {team}: {wp['probability'] * 100:.1f}%")

    wpct = data.get("winning_pct")
    if wpct:
        wd = wpct.get("widgets", {}).get("widgets_data", [])
        for item in wd:
            for d in item.get("data", []):
                parts.append(f"\nVenue Win %: Batting First {d.get('Batting First', '?')}%, Batting Second {d.get('Batting Second', '?')}%")

    ps = data.get("par_score")
    if ps:
        pd_list = ps.get("widgets", {}).get("widgets_data", [])
        for item in pd_list:
            for d in item.get("data", []):
                parts.append(f"Par Score Batting First: {d.get('Batting First', '?')}")

    tb = data.get("top_batsmen")
    if tb and tb.get("probability"):
        parts.append("\n## Top Batsmen (20+ runs probability)")
        for p in sorted(tb["probability"], key=lambda x: x.get("probability", 0), reverse=True)[:8]:
            parts.append(f"- {p['playerLongName']} ({p['teamName']}): {p['probability']:.1f}%")

    tbl = data.get("top_bowlers")
    if tbl and tbl.get("probability"):
        parts.append("\n## Top Bowlers (2+ wickets probability)")
        for p in sorted(tbl["probability"], key=lambda x: x.get("probability", 0), reverse=True)[:8]:
            parts.append(f"- {p['playerLongName']} ({p['teamName']}): {p['probability']:.1f}%")

    bs = data.get("batsmen_stats")
    if bs and bs.get("stats"):
        parts.append("\n## Batsman Fun Facts")
        for s in bs["stats"]:
            parts.append(f"- {s['value']}")

    bos = data.get("bowler_stats")
    if bos and bos.get("stats"):
        parts.append("\n## Bowler Fun Facts")
        for s in bos["stats"]:
            parts.append(f"- {s['value']}")

    ta = data.get("team_analysis")
    if ta:
        for widget in ta:
            wname = widget.get("widgetName", "")
            widgets = widget.get("widgets", {})
            if wname == "team_runs_in_ground":
                batting = widgets.get("Batting", [])
                parts.append("\n## Team Batting Avg at Venue")
                for td in batting:
                    parts.append(f"  {td.get('title', '')}:")
                    for e in td.get("data", []):
                        if e.get("value") is not None:
                            parts.append(f"    {e['match']}: {e['value']}")

            elif wname == "team_average_run_scored":
                last5 = widgets.get("Last_5_matches", {})
                parts.append("\n## Phase-wise Runs (Last 5 matches avg)")
                for phase_key, label in [("powerPlay", "Powerplay"), ("middleOver", "Middle"), ("deathOver", "Death")]:
                    pd_data = last5.get(phase_key, [])
                    if pd_data:
                        entries = pd_data[0].get("data", [])
                        for team_name in [t1, t2]:
                            avg = sum(e.get(team_name, 0) for e in entries) / max(len(entries), 1)
                            parts.append(f"  {team_name} {label}: {avg:.1f}")

    return "\n".join(parts)


def get_ai_analysis(data: dict) -> str:
    if not OPENAI_API_KEY:
        return "[dim]Set OPENAI_API_KEY in .env to enable AI analysis.[/dim]"

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = build_analysis_prompt(data)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
    )
    return resp.choices[0].message.content
