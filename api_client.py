import requests

from config import BASE_URL, HEADERS, COOKIES
from db import get_cached, set_cached, save_matches


class SpodaAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.cookies.update(COOKIES)

    def _get(self, path: str, params: dict | None = None, cache_key: str | None = None):
        if cache_key:
            cached = get_cached(cache_key)
            if cached is not None:
                return cached

        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if cache_key:
            set_cached(cache_key, data)
        return data

    # ── Match Overview ──────────────────────────────────────────────

    def get_matches(self) -> dict:
        data = self._get("/match-overview/matches", cache_key="matches_overview")
        today = data.get("today", "")
        if data.get("todaysMatches"):
            save_matches(data["todaysMatches"], "today", today)
        if data.get("tomorrowsMatches"):
            save_matches(data["tomorrowsMatches"], "tomorrow", today)
        return data

    # ── Match Winner ────────────────────────────────────────────────

    def get_match_winner_stats(self, match_id: int) -> dict:
        return self._get(
            "/match-winner/stats",
            params={"matchId": match_id},
            cache_key=f"winner_stats_{match_id}",
        )

    def get_win_probability(self, match_id: int, team_id: int,
                            first_innings_score: int = 180,
                            death_over_runs: int = 50,
                            wickets_lost_pp: int = 1) -> dict:
        return self._get(
            "/match-winner/win-probability",
            params={
                "matchId": match_id,
                "teamId": team_id,
                "firstInningsScore": first_innings_score,
                "deathOverRuns": death_over_runs,
                "wicketsLostInPowerplay": wickets_lost_pp,
            },
            cache_key=f"win_prob_{match_id}_{team_id}_{first_innings_score}_{death_over_runs}_{wickets_lost_pp}",
        )

    def simulate_win_probability(self, match_id: int, team_id: int,
                                 first_innings_score: int,
                                 death_over_runs: int,
                                 wickets_lost_pp: int) -> dict:
        """Like get_win_probability but never caches — for interactive simulator."""
        return self._get(
            "/match-winner/win-probability",
            params={
                "matchId": match_id,
                "teamId": team_id,
                "firstInningsScore": first_innings_score,
                "deathOverRuns": death_over_runs,
                "wicketsLostInPowerplay": wickets_lost_pp,
            },
        )

    # ── Top Batsmen ─────────────────────────────────────────────────

    def get_top_batsmen_runs(self, match_id: int, min_runs: int = 20) -> dict:
        return self._get(
            "/top-bastman/runs-scored",
            params={"matchId": match_id, "minRunsScored": min_runs},
            cache_key=f"batsmen_runs_{match_id}_{min_runs}",
        )

    def get_batsmen_stats(self, match_id: int) -> dict:
        return self._get(
            "/top-bastman/stats",
            params={"matchId": match_id},
            cache_key=f"batsmen_stats_{match_id}",
        )

    # ── Top Bowlers ─────────────────────────────────────────────────

    def get_top_bowlers_wickets(self, match_id: int, min_wickets: int = 2) -> dict:
        return self._get(
            "/top-bowler/wickets",
            params={"matchId": match_id, "minWicketsTaken": min_wickets},
            cache_key=f"bowlers_wickets_{match_id}_{min_wickets}",
        )

    def get_bowler_stats(self, match_id: int) -> dict:
        return self._get(
            "/top-bowler/stats",
            params={"matchId": match_id},
            cache_key=f"bowler_stats_{match_id}",
        )

    # ── Team Analysis ───────────────────────────────────────────────

    def get_team_analysis(self, match_id: int, team1_id: int, team2_id: int) -> list:
        return self._get(
            "/match-team-analysis/team",
            params={
                "matchId": match_id,
                "teamOneId": team1_id,
                "teamTwoId": team2_id,
            },
            cache_key=f"team_analysis_{match_id}_{team1_id}_{team2_id}",
        )

    # ── Ground Analysis ─────────────────────────────────────────────

    def get_grounds(self, match_id: int, team1_id: int, team2_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/grounds/",
            params={"matchId": match_id, "teams": f"{team1_id},{team2_id}"},
            cache_key=f"grounds_{match_id}_{team1_id}_{team2_id}",
        )

    def get_par_score(self, match_id: int, ground_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/par-score",
            params={"matchId": match_id, "groundId": ground_id, "groundIdTwo": ""},
            cache_key=f"par_score_{match_id}_{ground_id}",
        )

    def get_winning_percentage(self, match_id: int, ground_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/winning-percentage",
            params={"matchId": match_id, "groundId": ground_id, "groundIdTwo": ""},
            cache_key=f"win_pct_{match_id}_{ground_id}",
        )

    def get_boundaries_per_game(self, match_id: int, ground_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/boundaries-per-game",
            params={"matchId": match_id, "groundId": ground_id, "groundIdTwo": ""},
            cache_key=f"boundaries_{match_id}_{ground_id}",
        )

    def get_economy_in_phase(self, match_id: int, ground_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/economy-in-phase",
            params={"matchId": match_id, "groundId": ground_id, "groundIdTwo": ""},
            cache_key=f"economy_phase_{match_id}_{ground_id}",
        )

    def get_runs_in_phase(self, match_id: int, ground_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/run-scored-in-phase",
            params={"matchId": match_id, "groundId": ground_id, "groundIdTwo": ""},
            cache_key=f"runs_phase_{match_id}_{ground_id}",
        )

    def get_wickets_per_innings(self, match_id: int, ground_id: int) -> dict:
        return self._get(
            "/match-ground-analysis/wickets-per-innings",
            params={"matchId": match_id, "groundId": ground_id, "groundIdTwo": ""},
            cache_key=f"wickets_innings_{match_id}_{ground_id}",
        )

    # ── Aggregate helper ────────────────────────────────────────────

    def fetch_full_match_data(self, match: dict) -> dict:
        mid = match["match_id"]
        t1 = match["team_id1"]
        t2 = match["team_id2"]
        gid = match["ground_id"]

        result = {"match": match}

        try:
            result["winner_stats"] = self.get_match_winner_stats(mid)
        except Exception:
            result["winner_stats"] = None

        for team_id, label in [(t1, "team1"), (t2, "team2")]:
            try:
                result[f"win_prob_{label}"] = self.get_win_probability(mid, team_id)
            except Exception:
                result[f"win_prob_{label}"] = None

        try:
            result["top_batsmen"] = self.get_top_batsmen_runs(mid)
        except Exception:
            result["top_batsmen"] = None

        try:
            result["batsmen_stats"] = self.get_batsmen_stats(mid)
        except Exception:
            result["batsmen_stats"] = None

        try:
            result["top_bowlers"] = self.get_top_bowlers_wickets(mid)
        except Exception:
            result["top_bowlers"] = None

        try:
            result["bowler_stats"] = self.get_bowler_stats(mid)
        except Exception:
            result["bowler_stats"] = None

        try:
            result["team_analysis"] = self.get_team_analysis(mid, t1, t2)
        except Exception:
            result["team_analysis"] = None

        try:
            result["par_score"] = self.get_par_score(mid, gid)
        except Exception:
            result["par_score"] = None

        try:
            result["winning_pct"] = self.get_winning_percentage(mid, gid)
        except Exception:
            result["winning_pct"] = None

        try:
            result["boundaries"] = self.get_boundaries_per_game(mid, gid)
        except Exception:
            result["boundaries"] = None

        try:
            result["economy_phase"] = self.get_economy_in_phase(mid, gid)
        except Exception:
            result["economy_phase"] = None

        try:
            result["runs_phase"] = self.get_runs_in_phase(mid, gid)
        except Exception:
            result["runs_phase"] = None

        try:
            result["wickets_innings"] = self.get_wickets_per_innings(mid, gid)
        except Exception:
            result["wickets_innings"] = None

        return result
