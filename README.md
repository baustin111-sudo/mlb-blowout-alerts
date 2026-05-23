# MLB Blowout Alerts ⚾

Sends you a push notification any time an MLB team is up by **8+ runs** in a live game. Free to run.

## How it works

- A GitHub Actions cron job runs every 5 minutes.
- It hits MLB's public Stats API (no key needed) for the day's games.
- For each live game where the run differential ≥ 8, it sends a push notification via [ntfy.sh](https://ntfy.sh).
- A small `alerted_games.json` file tracks which games (and at what margin) have already been alerted, so you don't get spammed. If a game goes 8 → 12, you'll get a second alert at 12.

## One-time setup (~5 minutes)

### 1. Install ntfy on your phone
- iOS: search "ntfy" in the App Store
- Android: Play Store, or F-Droid

### 2. Pick a topic name
Open the ntfy app → **Add subscription** → enter a hard-to-guess topic name like `mlb-blowouts-d7k2qx9p`. Anyone who knows this name can send notifications to your phone, so make it long and random. **Don't use a guessable name.**

### 3. Fork or upload this repo to GitHub
Create a new private repo, drop these files in.

### 4. Add your topic as a secret
In the repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `NTFY_TOPIC`
- Value: the topic name from step 2 (e.g. `mlb-blowouts-d7k2qx9p`)

### 5. Enable Actions
Go to the **Actions** tab and click "I understand my workflows, go ahead and enable them."

Done. The workflow will run every 5 minutes automatically. You can also run it manually from the Actions tab to test.

## Test it locally (optional)

```bash
# Dry run — prints what it would send, doesn't push
python3 check_blowouts.py

# Real run with a low threshold to confirm pushes work mid-game
NTFY_TOPIC=your-topic-name RUN_THRESHOLD=1 python3 check_blowouts.py
```

## Config

Set these as environment variables (locally) or as repo secrets (in Actions):

| Variable | Default | Purpose |
|---|---|---|
| `NTFY_TOPIC` | (none → dry run) | Your ntfy topic name |
| `NTFY_SERVER` | `https://ntfy.sh` | Use a self-hosted server if you want |
| `RUN_THRESHOLD` | `8` | Minimum run differential to alert on |

## Notes & caveats

- **GitHub cron is best-effort.** Runs can be delayed by a few minutes under load. For an MLB blowout alert this is totally fine.
- **Free tier is way more than enough.** Public repos get unlimited Actions minutes. Private repos get 2,000/month free; this job uses ~30 seconds per run × 288 runs/day ≈ 144 min/day. To stay safely under the cap, either make the repo public or change the cron to `*/10 * * * *` (10 min cadence, ~72 min/day).
- **ntfy.sh is free and public.** Notifications are end-to-end visible to anyone who guesses your topic — that's why you use a long random topic name. For real privacy, self-host ntfy or use Pushover instead.
- The script only alerts on games with `abstractGameState == "Live"`, so finals and pregame don't trigger.
