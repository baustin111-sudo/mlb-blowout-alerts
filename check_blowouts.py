#!/usr/bin/env python3
"""
MLB Blowout Alerter
Checks live MLB games and sends a push notification via ntfy.sh whenever
a team is up by 8+ runs. Tracks already-alerted games in a JSON file so
you don't get spammed for the same game.
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone

# --- Config ---
RUN_THRESHOLD = int(os.environ.get("RUN_THRESHOLD", "8"))
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")  # e.g. "my-mlb-alerts-xyz123"
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
STATE_FILE = Path(os.environ.get("STATE_FILE", "alerted_games.json"))

# MLB StatsAPI - free, no key required
MLB_SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1&hydrate=linescore"
    "&date={date}"
)


def http_get(url):
    req = Request(url, headers={"User-Agent": "mlb-blowout-alerter/1.0"})
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post(url, data, headers=None):
    req = Request(url, data=data.encode("utf-8"), method="POST")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def prune_state(state, todays_game_pks):
    """Remove entries for games that aren't on today's slate anymore."""
    return {k: v for k, v in state.items() if k in todays_game_pks}


def send_ntfy(title, message, tags="baseball,fire"):
    if not NTFY_TOPIC:
        print(f"[dry-run] {title}: {message}")
        return
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    http_post(
        url,
        message,
        headers={
            "Title": title,
            "Tags": tags,
            "Priority": "default",
        },
    )


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = MLB_SCHEDULE_URL.format(date=today)

    try:
        data = http_get(url)
    except Exception as e:
        print(f"Failed to fetch MLB schedule: {e}", file=sys.stderr)
        return 1

    state = load_state()
    todays_pks = set()
    new_alerts = 0

    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            pk = str(game.get("gamePk"))
            todays_pks.add(pk)

            status = game.get("status", {}).get("abstractGameState", "")
            # Only care about live games
            if status != "Live":
                continue

            linescore = game.get("linescore", {}) or {}
            teams = linescore.get("teams", {}) or {}
            home_runs = (teams.get("home", {}) or {}).get("runs")
            away_runs = (teams.get("away", {}) or {}).get("runs")
            if home_runs is None or away_runs is None:
                continue

            diff = abs(home_runs - away_runs)
            if diff < RUN_THRESHOLD:
                continue

            game_teams = game.get("teams", {}) or {}
            home_name = (
                ((game_teams.get("home", {}) or {}).get("team", {}) or {}).get("name", "Home")
            )
            away_name = (
                ((game_teams.get("away", {}) or {}).get("team", {}) or {}).get("name", "Away")
            )

            if home_runs > away_runs:
                leader, trailer = home_name, away_name
            else:
                leader, trailer = away_name, home_name

            inning = linescore.get("currentInning")
            inning_half = linescore.get("inningHalf", "")
            inning_str = f"{inning_half} {inning}".strip() if inning else ""

            # Only alert once per game per threshold tier (8, 9, 10+, etc.)
            # Use the diff as the "tier" so a game going 8 -> 12 only alerts once at 8.
            already_alerted_at = state.get(pk, 0)
            if diff <= already_alerted_at:
                continue

            title = f"⚾ Blowout: {leader} up {diff}"
            message = (
                f"{away_name} {away_runs} @ {home_name} {home_runs}"
                + (f" ({inning_str})" if inning_str else "")
            )

            try:
                send_ntfy(title, message)
                state[pk] = diff
                new_alerts += 1
                print(f"ALERT: {title} — {message}")
            except Exception as e:
                print(f"Failed to send ntfy for game {pk}: {e}", file=sys.stderr)

    # Clean up state for games no longer on today's slate
    state = prune_state(state, todays_pks)
    save_state(state)

    print(f"Checked {len(todays_pks)} games. New alerts sent: {new_alerts}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
