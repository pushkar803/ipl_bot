import json
import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH, CACHE_TTL_HOURS


def init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key   TEXT PRIMARY KEY,
                response    TEXT NOT NULL,
                fetched_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                match_id     INTEGER PRIMARY KEY,
                series_id    INTEGER,
                series_name  TEXT,
                title        TEXT,
                season       TEXT,
                team_id1     INTEGER,
                team_name1   TEXT,
                team_id2     INTEGER,
                team_name2   TEXT,
                ground_id    INTEGER,
                ground       TEXT,
                start_date   TEXT,
                day_type     TEXT,   -- 'today' | 'tomorrow' | 'previous'
                fetched_date TEXT
            );
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_cached(cache_key: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT response, fetched_at FROM api_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if row is None:
        return None
    age_hours = (time.time() - row["fetched_at"]) / 3600
    if age_hours > CACHE_TTL_HOURS:
        return None
    return json.loads(row["response"])


def set_cached(cache_key: str, data: dict):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache (cache_key, response, fetched_at) VALUES (?, ?, ?)",
            (cache_key, json.dumps(data), time.time()),
        )


def save_matches(matches: list[dict], day_type: str, fetched_date: str):
    with _conn() as conn:
        for m in matches:
            conn.execute(
                """INSERT OR REPLACE INTO matches
                   (match_id, series_id, series_name, title, season,
                    team_id1, team_name1, team_id2, team_name2,
                    ground_id, ground, start_date, day_type, fetched_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    m["matchId"], m["seriesId"], m["seriesName"], m["title"],
                    m["season"], m["teamId1"], m["teamName1"],
                    m["teamId2"], m["teamName2"], m["groundId"],
                    m["ground"], m["startDate"], day_type, fetched_date,
                ),
            )


def get_matches_by_day(day_type: str, fetched_date: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM matches WHERE day_type = ? AND fetched_date = ? ORDER BY start_date",
            (day_type, fetched_date),
        ).fetchall()
    return [dict(r) for r in rows]


def clear_old_cache():
    cutoff = time.time() - (CACHE_TTL_HOURS * 3600)
    with _conn() as conn:
        conn.execute("DELETE FROM api_cache WHERE fetched_at < ?", (cutoff,))
