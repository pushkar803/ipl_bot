from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box

console = Console()


def print_banner():
    banner = Text()
    banner.append("  CRICKET MATCH PREDICTOR  ", style="bold white on blue")
    console.print()
    console.print(Panel(banner, style="bold blue", expand=False))
    console.print()


def print_match_list(matches: list[dict], label: str):
    if not matches:
        console.print(f"  [dim]No {label.lower()} matches found.[/dim]\n")
        return

    table = Table(
        title=f"[bold cyan]{label}[/bold cyan]",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold",
        header_style="bold magenta",
        expand=False,
    )
    table.add_column("#", style="bold yellow", justify="center", width=4)
    table.add_column("Match", style="bold white", min_width=35)
    table.add_column("Series", style="cyan", min_width=15)
    table.add_column("Venue", style="green", min_width=20)
    table.add_column("Time (IST)", style="yellow", justify="center", width=12)

    for i, m in enumerate(matches, 1):
        dt_str = m.get("start_date") or m.get("startDate", "")
        try:
            dt = datetime.fromisoformat(dt_str)
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            time_str = dt_str

        title = m.get("title", f"{m.get('team_name1', '')} vs {m.get('team_name2', '')}")
        series = m.get("series_name") or m.get("seriesName", "")
        ground = m.get("ground", "")

        table.add_row(str(i), title, series, ground, time_str)

    console.print(table)
    console.print()


def print_section(title: str):
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]", style="cyan")
    console.print()


def print_winner_stats(data: dict | None):
    if not data or not data.get("stats"):
        return
    print_section("Match Winner Insights")
    for stat in data["stats"]:
        title = stat.get("title", "")
        value = stat.get("value", "")
        console.print(f"  [bold yellow]{title}[/bold yellow]")
        console.print(f"  {value}\n")


def print_win_probability(prob1: dict | None, prob2: dict | None, match: dict):
    print_section("Win Probability (Default Scenario)")
    t1 = match.get("team_name1", "Team 1")
    t2 = match.get("team_name2", "Team 2")

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold magenta", expand=False)
    table.add_column("Team", style="bold white", min_width=25)
    table.add_column("Win Probability", justify="center", min_width=15)

    p1 = prob1.get("probability", "N/A") if prob1 else "N/A"
    p2 = prob2.get("probability", "N/A") if prob2 else "N/A"

    p1_str = f"{p1 * 100:.1f}%" if isinstance(p1, (int, float)) else str(p1)
    p2_str = f"{p2 * 100:.1f}%" if isinstance(p2, (int, float)) else str(p2)

    style1 = "bold green" if isinstance(p1, (int, float)) and isinstance(p2, (int, float)) and p1 > p2 else "white"
    style2 = "bold green" if isinstance(p2, (int, float)) and isinstance(p1, (int, float)) and p2 > p1 else "white"

    table.add_row(f"[{style1}]{t1}[/{style1}]", f"[{style1}]{p1_str}[/{style1}]")
    table.add_row(f"[{style2}]{t2}[/{style2}]", f"[{style2}]{p2_str}[/{style2}]")

    console.print(table)


def print_top_players(data: dict | None, label: str, metric: str, top_n: int = 10):
    if not data or not data.get("probability"):
        return
    print_section(f"Top {label} ({metric} Probability)")

    players = sorted(data["probability"], key=lambda x: x.get("probability", 0), reverse=True)[:top_n]

    table = Table(box=box.ROUNDED, header_style="bold magenta", expand=False)
    table.add_column("#", style="dim", justify="center", width=4)
    table.add_column("Player", style="bold white", min_width=25)
    table.add_column("Team", style="cyan", min_width=20)
    table.add_column("Role", style="yellow", justify="center", width=8)
    table.add_column("Probability", justify="center", min_width=12)

    for i, p in enumerate(players, 1):
        prob = p.get("probability", 0)
        if prob >= 60:
            prob_style = "bold green"
        elif prob >= 40:
            prob_style = "bold yellow"
        else:
            prob_style = "white"

        table.add_row(
            str(i),
            p.get("playerLongName", p.get("playerName", "")),
            p.get("teamName", ""),
            p.get("playingRoles", ""),
            f"[{prob_style}]{prob:.1f}%[/{prob_style}]",
        )

    console.print(table)

    squad = data.get("squadAnnounced")
    if squad is not None:
        status = "[green]Announced[/green]" if squad else "[yellow]Not Yet Announced[/yellow]"
        console.print(f"  Squad Status: {status}")


def print_player_stats(data: dict | None, label: str):
    if not data or not data.get("stats"):
        return
    print_section(f"{label} Fun Facts")
    for stat in data["stats"]:
        title = stat.get("title", "")
        value = stat.get("value", "")
        console.print(f"  [bold yellow]{title}[/bold yellow]")
        console.print(f"  {value}\n")


def print_team_analysis(data: list | None, match: dict):
    if not data:
        return
    print_section("Team Form Analysis")

    t1 = match.get("team_name1", "Team 1")
    t2 = match.get("team_name2", "Team 2")

    for widget in data:
        widget_name = widget.get("widgetName", "")
        widgets = widget.get("widgets", {})

        if widget_name == "team_runs_in_ground":
            _print_ground_batting(widgets, t1, t2)
        elif widget_name == "team_boundaries_percentage":
            _print_boundaries_pct(widgets, t1, t2)
        elif widget_name == "team_average_run_scored":
            _print_phase_form(widgets, t1, t2, "Avg Runs Scored")
        elif widget_name == "team_wickets_taken":
            _print_phase_form(widgets, t1, t2, "Wickets Taken")


def _print_ground_batting(widgets: dict, t1: str, t2: str):
    batting = widgets.get("Batting", [])
    if not batting:
        return

    console.print("  [bold]Batting Average at This Venue[/bold]\n")
    table = Table(box=box.SIMPLE, header_style="bold magenta", expand=False)
    table.add_column("Team", style="bold white", min_width=25)
    table.add_column("1st Innings Avg", justify="center", min_width=15)
    table.add_column("2nd Innings Avg", justify="center", min_width=15)

    for team_data in batting:
        title = team_data.get("title", "")
        entries = team_data.get("data", [])
        first = second = "-"
        for entry in entries:
            match_label = entry.get("match", "")
            val = entry.get("value")
            if val is not None:
                if "First Innings" in match_label:
                    first = str(val)
                elif "Second Innings" in match_label:
                    second = str(val)
        table.add_row(title, first, second)

    console.print(table)


def _print_boundaries_pct(widgets: dict, t1: str, t2: str):
    batting = widgets.get("Batting", [])
    if not batting:
        return

    console.print("  [bold]Boundary Percentages[/bold]\n")
    table = Table(box=box.SIMPLE, header_style="bold magenta", expand=False)
    table.add_column("Team", style="bold white", min_width=25)
    table.add_column("Fours %", justify="center", min_width=10)
    table.add_column("Sixes %", justify="center", min_width=10)

    for team_data in batting:
        title = team_data.get("title", "")
        entries = team_data.get("data", [])
        fours = sixes = "-"
        for entry in entries:
            match_label = entry.get("match", "")
            val = entry.get("value")
            if val is not None:
                if "4" in match_label and "6" not in match_label:
                    fours = f"{val}%"
                elif "6" in match_label:
                    sixes = f"{val}%"
        table.add_row(title, fours, sixes)

    console.print(table)


def _print_phase_form(widgets: dict, t1: str, t2: str, metric: str):
    last5 = widgets.get("Last_5_matches")
    if not last5:
        return

    console.print(f"\n  [bold]{metric} — Last 5 Matches by Phase[/bold]\n")
    table = Table(box=box.SIMPLE, header_style="bold magenta", expand=False)
    table.add_column("Phase", style="bold yellow", min_width=15)
    table.add_column(t1, justify="center", min_width=12)
    table.add_column(t2, justify="center", min_width=12)

    for phase_key, phase_label in [("powerPlay", "Powerplay"), ("middleOver", "Middle Overs"), ("deathOver", "Death Overs")]:
        phase_data = last5.get(phase_key, [])
        if not phase_data:
            continue
        entries = phase_data[0].get("data", [])
        t1_total = sum(e.get(t1, 0) for e in entries)
        t2_total = sum(e.get(t2, 0) for e in entries)
        t1_avg = t1_total / len(entries) if entries else 0
        t2_avg = t2_total / len(entries) if entries else 0
        table.add_row(phase_label, f"{t1_avg:.1f}", f"{t2_avg:.1f}")

    console.print(table)


def print_ground_stats(winning_pct: dict | None, par_score: dict | None):
    if not winning_pct and not par_score:
        return
    print_section("Venue Analysis")

    if winning_pct:
        wdata = winning_pct.get("widgets", {}).get("widgets_data", [])
        for item in wdata:
            ground_name = item.get("title", "")
            for d in item.get("data", []):
                bf = d.get("Batting First", "?")
                bs = d.get("Batting Second", "?")
                console.print(f"  [bold]{ground_name}[/bold] — Winning %")
                console.print(f"    Batting First:  [yellow]{bf}%[/yellow]")
                console.print(f"    Batting Second: [yellow]{bs}%[/yellow]\n")

    if par_score:
        pdata = par_score.get("widgets", {}).get("widgets_data", [])
        for item in pdata:
            ground_name = item.get("title", "")
            for d in item.get("data", []):
                bf = d.get("Batting First", "?")
                console.print(f"  [bold]{ground_name}[/bold] — Par Score")
                console.print(f"    Batting First Par: [cyan]{bf}[/cyan]\n")


def print_ai_analysis(analysis: str):
    print_section("AI-Powered Deep Analysis")
    console.print(Panel(analysis, border_style="green", padding=(1, 2)))


def print_full_prediction(data: dict):
    match = data["match"]
    title = match.get("title", f"{match.get('team_name1', '')} vs {match.get('team_name2', '')}")
    ground = match.get("ground", "")
    series = match.get("series_name", "")

    header = Text()
    header.append(f"\n  {title}\n", style="bold white")
    header.append(f"  {series} • {ground}", style="dim")
    console.print(Panel(header, border_style="blue", expand=False))

    print_winner_stats(data.get("winner_stats"))
    print_win_probability(data.get("win_prob_team1"), data.get("win_prob_team2"), match)
    print_ground_stats(data.get("winning_pct"), data.get("par_score"))
    print_team_analysis(data.get("team_analysis"), match)
    print_top_players(data.get("top_batsmen"), "Batsmen", "20+ Runs")
    print_player_stats(data.get("batsmen_stats"), "Batsman")
    print_top_players(data.get("top_bowlers"), "Bowlers", "2+ Wickets")
    print_player_stats(data.get("bowler_stats"), "Bowler")
