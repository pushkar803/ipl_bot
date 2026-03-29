#!/usr/bin/env python3
"""Cricket Match Prediction Engine — powered by Spoda AI APIs."""

import sys

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

import db
from config import OPENAI_API_KEY, SPODA_AUTH_COOKIE, BASE_URL, HEADERS, COOKIES
from api_client import SpodaAPI
from display import (
    print_banner,
    print_match_list,
    print_full_prediction,
    print_ai_analysis,
    console,
)
from analyzer import get_ai_analysis

_openai_available = False


def check_spoda_cookie() -> bool:
    if not SPODA_AUTH_COOKIE:
        console.print("  [red]SPODA_AUTH_COOKIE is not set in .env — cannot fetch data.[/red]")
        return False

    try:
        import requests
        resp = requests.get(
            f"{BASE_URL}/match-overview/matches",
            headers=HEADERS,
            cookies=COOKIES,
            timeout=15,
        )
        if resp.status_code == 401:
            console.print("  [red]Spoda auth cookie is expired or invalid (401). Please update .env.[/red]")
            return False
        if resp.status_code == 403:
            console.print("  [red]Spoda auth cookie was rejected (403). Please update .env.[/red]")
            return False
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            console.print(f"  [red]Spoda API error: {data.get('message', 'Unknown')}[/red]")
            return False
        console.print("  [green]Spoda API connection validated.[/green]")
        return True
    except requests.ConnectionError:
        console.print("  [red]Cannot connect to api.spoda.ai — check your internet.[/red]")
        return False
    except requests.Timeout:
        console.print("  [red]Connection to api.spoda.ai timed out.[/red]")
        return False
    except Exception as e:
        console.print(f"  [red]Spoda check failed: {e}[/red]")
        return False


def check_openai_key() -> bool:
    if not OPENAI_API_KEY:
        console.print("  [yellow]OPENAI_API_KEY not set in .env — AI analysis disabled.[/yellow]")
        return False

    try:
        from openai import OpenAI, AuthenticationError, APIConnectionError

        client = OpenAI(api_key=OPENAI_API_KEY)
        client.models.list()
        console.print("  [green]OpenAI API key validated.[/green]")
        return True
    except AuthenticationError:
        console.print("  [red]OpenAI API key is invalid — AI analysis disabled.[/red]")
        return False
    except APIConnectionError:
        console.print("  [red]Could not connect to OpenAI — AI analysis disabled.[/red]")
        return False
    except Exception as e:
        console.print(f"  [red]OpenAI check failed ({type(e).__name__}) — AI analysis disabled.[/red]")
        return False


def fetch_matches(api: SpodaAPI) -> dict:
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Fetching matches…"), console=console, transient=True):
        data = api.get_matches()
    return data


def build_match_dict(raw: dict) -> dict:
    return {
        "match_id": raw["matchId"],
        "series_id": raw["seriesId"],
        "series_name": raw["seriesName"],
        "title": raw["title"],
        "season": raw["season"],
        "team_id1": raw["teamId1"],
        "team_name1": raw["teamName1"],
        "team_id2": raw["teamId2"],
        "team_name2": raw["teamName2"],
        "ground_id": raw["groundId"],
        "ground": raw["ground"],
        "start_date": raw["startDate"],
    }


def run_prediction(api: SpodaAPI, match: dict):
    console.print()
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Fetching match data…"), console=console, transient=True):
        full_data = api.fetch_full_match_data(match)

    print_full_prediction(full_data)

    if _openai_available and Confirm.ask("\n  [bold]Run AI-powered deep analysis?[/bold]", default=True):
        with Progress(SpinnerColumn(), TextColumn("[bold green]Generating AI analysis…"), console=console, transient=True):
            analysis = get_ai_analysis(full_data)
        print_ai_analysis(analysis)
    elif not _openai_available:
        console.print("\n  [dim]AI analysis skipped (no valid OpenAI key).[/dim]")


def interactive_loop(api: SpodaAPI, today_matches: list[dict], tomorrow_matches: list[dict]):
    all_labeled: list[tuple[dict, str]] = []
    for m in today_matches:
        all_labeled.append((m, "today"))
    for m in tomorrow_matches:
        all_labeled.append((m, "tomorrow"))

    while True:
        console.print()
        console.rule("[bold blue]Main Menu[/bold blue]", style="blue")
        console.print()
        console.print("  [bold yellow]1[/bold yellow]  View Today's Matches")
        console.print("  [bold yellow]2[/bold yellow]  View Tomorrow's Matches")
        console.print("  [bold yellow]3[/bold yellow]  Pick a Match for Prediction")
        console.print("  [bold yellow]4[/bold yellow]  Refresh Matches from API")
        console.print("  [bold yellow]0[/bold yellow]  Exit")
        console.print()

        choice = Prompt.ask("  [bold]Choose an option[/bold]", choices=["0", "1", "2", "3", "4"], default="3")

        if choice == "0":
            console.print("\n  [dim]Goodbye![/dim]\n")
            break

        elif choice == "1":
            print_match_list(today_matches, "Today's Matches")

        elif choice == "2":
            print_match_list(tomorrow_matches, "Tomorrow's Matches")

        elif choice == "3":
            console.print()
            if today_matches:
                print_match_list(today_matches, "Today's Matches")
            if tomorrow_matches:
                print_match_list(tomorrow_matches, "Tomorrow's Matches")

            if not all_labeled:
                console.print("  [red]No matches available.[/red]")
                continue

            console.print(f"  [dim]Enter match number (1-{len(all_labeled)}) across today + tomorrow[/dim]")

            combined = []
            for m, _ in all_labeled:
                combined.append(m)

            valid = [str(i) for i in range(1, len(combined) + 1)]
            pick = Prompt.ask("  [bold]Match #[/bold]", choices=valid)
            idx = int(pick) - 1
            selected = combined[idx]

            run_prediction(api, selected)

        elif choice == "4":
            db.clear_old_cache()
            data = fetch_matches(api)
            today_matches = [build_match_dict(m) for m in data.get("todaysMatches", [])]
            tomorrow_matches = [build_match_dict(m) for m in data.get("tomorrowsMatches", [])]
            all_labeled = [(m, "today") for m in today_matches] + [(m, "tomorrow") for m in tomorrow_matches]
            console.print("  [green]Matches refreshed![/green]")


def main():
    global _openai_available

    db.init_db()
    api = SpodaAPI()

    print_banner()

    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Validating Spoda connection…"), console=console, transient=True):
        spoda_ok = check_spoda_cookie()
    if not spoda_ok:
        console.print("\n  [bold red]Cannot proceed without a valid Spoda connection.[/bold red]")
        console.print("  [dim]Update SPODA_AUTH_COOKIE in your .env file and try again.[/dim]\n")
        return

    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Validating OpenAI key…"), console=console, transient=True):
        _openai_available = check_openai_key()
    console.print()

    data = fetch_matches(api)
    today_matches = [build_match_dict(m) for m in data.get("todaysMatches", [])]
    tomorrow_matches = [build_match_dict(m) for m in data.get("tomorrowsMatches", [])]

    console.print(f"  [dim]Data date: {data.get('today', 'N/A')}[/dim]\n")

    if today_matches:
        print_match_list(today_matches, "Today's Matches")
    if tomorrow_matches:
        print_match_list(tomorrow_matches, "Tomorrow's Matches")

    if not today_matches and not tomorrow_matches:
        console.print("  [red]No upcoming matches found.[/red]\n")
        return

    interactive_loop(api, today_matches, tomorrow_matches)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n  [dim]Interrupted. Bye![/dim]\n")
        sys.exit(0)
