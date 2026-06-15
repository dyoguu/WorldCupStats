import csv
import json
import urllib.request
from collections import defaultdict
from pathlib import Path


STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GPT_UPLOAD_DIR = PROJECT_ROOT / "gpt_upload"

# Independent GPT export config.
# This script fetches directly from StatsBomb Open Data and does not depend on /data JSON files.
INCLUDED_COMPETITIONS = {
    "FIFA World Cup",
    "UEFA Euro",
    "Copa America",
    "African Cup of Nations",
    "Women's World Cup",
    "UEFA Women's Euro",
    "FIFA U20 World Cup",
}

# Optional team filter. Leave as None to include all teams from the included competitions.
INCLUDED_TEAMS = None

METRIC_KEYS = [
    "goals",
    "own_goals",
    "shots",
    "passes",
    "dribbles",
    "fouls",
    "yellow_cards",
    "red_cards",
    "corners",
    "free_kicks",
    "goal_kicks",
    "throw_ins",
    "penalty_shots",
    "offsides",
]

DATA_DICTIONARY = {
    "goals": "Shot events where shot.outcome.name is Goal.",
    "own_goals": "Own Goal Against events assigned to the team that scored against itself.",
    "shots": "Shot events.",
    "passes": "Pass events.",
    "dribbles": "Dribble events.",
    "fouls": "Foul Committed events.",
    "yellow_cards": "Yellow Card and Second Yellow card events found in foul_committed or bad_behaviour.",
    "red_cards": "Red Card and Second Yellow card events found in foul_committed or bad_behaviour.",
    "corners": "Pass events where pass.type.name is Corner.",
    "free_kicks": "Pass events where pass.type.name is Free Kick.",
    "goal_kicks": "Pass events where pass.type.name is Goal Kick.",
    "throw_ins": "Pass events where pass.type.name is Throw-in.",
    "penalty_shots": "Shot events where shot.type.name is Penalty. Used as first-version proxy for penalty awarded.",
    "offsides": "Offside events.",
}


def fetch_json(url: str):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def safe_name(value):
    if isinstance(value, dict):
        return value.get("name")
    return value


def get_team_name_from_event(event):
    team = event.get("team")
    if isinstance(team, dict):
        return team.get("name")
    return None


def get_card_name(event):
    foul = event.get("foul_committed") or {}
    bad_behaviour = event.get("bad_behaviour") or {}
    card = foul.get("card") or bad_behaviour.get("card")
    if isinstance(card, dict):
        return card.get("name")
    return None


def is_goal(event):
    if safe_name(event.get("type")) != "Shot":
        return False
    shot = event.get("shot") or {}
    outcome = shot.get("outcome") or {}
    return outcome.get("name") == "Goal"


def is_penalty_shot(event):
    if safe_name(event.get("type")) != "Shot":
        return False
    shot = event.get("shot") or {}
    shot_type = shot.get("type") or {}
    return shot_type.get("name") == "Penalty"


def build_empty_stats():
    return {key: 0 for key in METRIC_KEYS}


def event_to_metric_updates(event):
    event_type = safe_name(event.get("type"))
    updates = []

    if event_type == "Shot":
        updates.append("shots")
        if is_goal(event):
            updates.append("goals")
        if is_penalty_shot(event):
            updates.append("penalty_shots")

    elif event_type == "Pass":
        updates.append("passes")
        pass_data = event.get("pass") or {}
        pass_type = pass_data.get("type") or {}
        pass_type_name = pass_type.get("name")
        if pass_type_name == "Corner":
            updates.append("corners")
        elif pass_type_name == "Free Kick":
            updates.append("free_kicks")
        elif pass_type_name == "Goal Kick":
            updates.append("goal_kicks")
        elif pass_type_name == "Throw-in":
            updates.append("throw_ins")

    elif event_type == "Dribble":
        updates.append("dribbles")

    elif event_type == "Foul Committed":
        updates.append("fouls")
        card_name = get_card_name(event)
        if card_name in {"Yellow Card", "Second Yellow"}:
            updates.append("yellow_cards")
        if card_name in {"Red Card", "Second Yellow"}:
            updates.append("red_cards")

    elif event_type == "Bad Behaviour":
        card_name = get_card_name(event)
        if card_name in {"Yellow Card", "Second Yellow"}:
            updates.append("yellow_cards")
        if card_name in {"Red Card", "Second Yellow"}:
            updates.append("red_cards")

    elif event_type == "Offside":
        updates.append("offsides")

    elif event_type == "Own Goal Against":
        updates.append("own_goals")

    return updates


def team_allowed(home_team, away_team):
    if INCLUDED_TEAMS is None:
        return True
    return home_team in INCLUDED_TEAMS or away_team in INCLUDED_TEAMS


def calculate_team_match_stats(events, home_team, away_team):
    stats = defaultdict(build_empty_stats)
    stats[home_team]
    stats[away_team]

    for event in events:
        team_name = get_team_name_from_event(event)
        if not team_name:
            continue
        for metric in event_to_metric_updates(event):
            stats[team_name][metric] += 1

    return stats


def calculate_team_match_minute_stats(events):
    minute_stats = {}

    for event in events:
        team_name = get_team_name_from_event(event)
        if not team_name:
            continue

        period = event.get("period")
        minute = event.get("minute")
        second = event.get("second")

        if period is None or minute is None:
            continue

        key = (team_name, int(period), int(minute))

        if key not in minute_stats:
            minute_stats[key] = {
                "team": team_name,
                "period": int(period),
                "minute": int(minute),
                "first_second_in_minute": int(second or 0),
                **build_empty_stats(),
            }

        if second is not None:
            minute_stats[key]["first_second_in_minute"] = min(
                minute_stats[key]["first_second_in_minute"],
                int(second),
            )

        for metric in event_to_metric_updates(event):
            minute_stats[key][metric] += 1

    return list(minute_stats.values())


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    seen = set(fieldnames)

    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_readme(match_rows, team_match_rows, minute_rows):
    return f"""# WorldCupStats GPT Upload Package

This folder is generated independently from StatsBomb Open Data.

It does not depend on the website JSON files under `/data`.

Use these files as the source of truth for a Custom GPT focused on national-team football analytics.

## Files

### `match_index.csv`

One row per match.

Use for match metadata, competition filters, season filters, match dates, scores, stages, stadiums, referees, and match IDs.

Rows: {len(match_rows)}

### `team_match_stats.csv`

One row per team per match.

Use for whole-match analytics, team comparisons, last-X-games analysis, and average metrics.

Rows: {len(team_match_rows)}

### `team_match_minute_stats.csv`

One row per team, match, period, and minute where at least one tracked metric occurred.

Use for period and minute-range questions.

Rows: {len(minute_rows)}

### `data_dictionary.md`

Metric definitions and caveats.

### `GPT_INSTRUCTIONS.md`

Suggested text to paste into the GPT Builder instructions field.

## Calculation guidance

For numerical questions, rankings, comparisons, last-X-games, period, or minute-range questions, use Data Analysis / Python to filter and aggregate the CSV files.

Do not rely only on semantic retrieval for calculations.

Always state:

1. filters applied,
2. metric definition,
3. number of matches or team-match rows used,
4. final result.
"""


def build_data_dictionary():
    lines = ["# WorldCupStats Data Dictionary", "", "## Metric definitions", ""]
    for key, definition in DATA_DICTIONARY.items():
        lines.append(f"### `{key}`")
        lines.append("")
        lines.append(definition)
        lines.append("")

    lines.extend([
        "## Tables",
        "",
        "### `match_index.csv`",
        "",
        "One row per match. Use this for match metadata, match dates, teams, scores, stages, stadiums, referees, and match IDs.",
        "",
        "### `team_match_stats.csv`",
        "",
        "One row per team per match. Use this for whole-match analytics and last-X-games calculations.",
        "",
        "### `team_match_minute_stats.csv`",
        "",
        "One row per team, match, period, and minute where at least one tracked metric occurred. Use this for period/minute-range analysis.",
        "",
        "## Notes and caveats",
        "",
        "- `penalty_shots` is used as the first-version proxy for penalty awarded because it is directly identifiable from StatsBomb shot events.",
        "- Minute-level data only contains rows where at least one tracked metric occurred.",
        "- For last-X-games questions, sort rows by `match_date` descending and apply the limit separately per team.",
        "- For whole-match questions, use `team_match_stats.csv`.",
        "- For period or minute-range questions, use `team_match_minute_stats.csv`.",
    ])
    return "\n".join(lines) + "\n"


def build_gpt_instructions():
    return """# Suggested GPT Instructions: WorldCupStats Analyst

You are WorldCupStats Analyst, a football data analytics assistant focused on national-team competitions using the uploaded StatsBomb Open Data analytical files.

Use the uploaded files as the source of truth.

## Available files

- `match_index.csv`: one row per match, containing match metadata.
- `team_match_stats.csv`: one row per team per match, for whole-match analytics.
- `team_match_minute_stats.csv`: one row per team, match, period, and minute, for period/minute-range analytics.
- `data_dictionary.md`: metric definitions and caveats.
- `README_FOR_GPT.md`: package overview and usage notes.

## Calculation rules

For numerical, ranking, comparison, last-X-games, period, or minute-range questions, use Data Analysis / Python to filter and aggregate the uploaded CSV files.

Do not guess numerical answers.

Do not rely only on semantic retrieval when a calculation is needed.

## Which file to use

Use `team_match_stats.csv` for:
- whole-match averages
- team comparisons
- competition and season aggregates
- last-X-games analysis
- goals, shots, passes, dribbles, fouls, cards, corners, free kicks, goal kicks, throw-ins, penalty shots, offsides

Use `team_match_minute_stats.csv` for:
- period filters
- minute-range filters
- first-half / second-half comparisons
- questions like "between minutes 0 and 15"
- questions like "how many matches had a foul in minute 0"

Use `match_index.csv` for:
- match metadata
- home/away teams
- scores
- match dates
- stages
- stadiums
- referees
- match IDs

Use `data_dictionary.md` for metric definitions.

## Response format

When answering analytical questions, state:
1. filters applied,
2. metric definition,
3. number of matches or team-match rows used,
4. final result.

If the uploaded files do not contain enough information to answer, say so clearly and explain what data would be needed.

For last-X-games questions involving multiple teams, apply the last-X filter separately per team, not globally.
"""


def build_gpt_data():
    GPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    competitions = fetch_json(f"{STATSBOMB_BASE_URL}/competitions.json")
    national_competitions = [c for c in competitions if c.get("competition_international") is True]

    if INCLUDED_COMPETITIONS is None:
        selected_competitions = national_competitions
    else:
        selected_competitions = [
            c for c in national_competitions
            if c.get("competition_name") in INCLUDED_COMPETITIONS
        ]

    match_index_rows = []
    team_match_rows = []
    minute_rows = []

    for competition in selected_competitions:
        competition_id = competition.get("competition_id")
        season_id = competition.get("season_id")

        print(
            f"Loading matches: {competition.get('competition_name')} "
            f"{competition.get('season_name')} "
            f"({competition_id}/{season_id})"
        )

        try:
            matches = fetch_json(f"{STATSBOMB_BASE_URL}/matches/{competition_id}/{season_id}.json")
        except Exception as exc:
            print(f"Could not load matches for {competition_id}/{season_id}: {exc}")
            continue

        for match in matches:
            match_id = match.get("match_id")
            home_team = (match.get("home_team") or {}).get("home_team_name")
            away_team = (match.get("away_team") or {}).get("away_team_name")

            if not match_id or not home_team or not away_team:
                continue

            if not team_allowed(home_team, away_team):
                continue

            match_record = {
                "match_id": match_id,
                "competition_id": competition_id,
                "season_id": season_id,
                "competition_name": competition.get("competition_name"),
                "season_name": competition.get("season_name"),
                "country_name": competition.get("country_name"),
                "competition_gender": competition.get("competition_gender"),
                "match_date": match.get("match_date"),
                "kick_off": match.get("kick_off"),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": match.get("home_score"),
                "away_score": match.get("away_score"),
                "stage": (match.get("competition_stage") or {}).get("name"),
                "stadium": (match.get("stadium") or {}).get("name"),
                "referee": (match.get("referee") or {}).get("name"),
                "event_source_url": f"{STATSBOMB_BASE_URL}/events/{match_id}.json",
            }
            match_index_rows.append(match_record)

            try:
                events = fetch_json(f"{STATSBOMB_BASE_URL}/events/{match_id}.json")
            except Exception as exc:
                print(f"Could not load events for match {match_id}: {exc}")
                continue

            stats_by_team = calculate_team_match_stats(events, home_team, away_team)
            match_minute_rows = calculate_team_match_minute_stats(events)

            for row in match_minute_rows:
                minute_rows.append({
                    "match_id": match_id,
                    "competition_id": competition_id,
                    "season_id": season_id,
                    "competition_name": competition.get("competition_name"),
                    "season_name": competition.get("season_name"),
                    "match_date": match.get("match_date"),
                    **row,
                })

            for team_name in [home_team, away_team]:
                opponent_name = away_team if team_name == home_team else home_team
                home_away = "home" if team_name == home_team else "away"

                row = {
                    "match_id": match_id,
                    "competition_id": competition_id,
                    "season_id": season_id,
                    "competition_name": competition.get("competition_name"),
                    "season_name": competition.get("season_name"),
                    "match_date": match.get("match_date"),
                    "team": team_name,
                    "opponent": opponent_name,
                    "home_away": home_away,
                }

                row.update(stats_by_team[team_name])
                team_match_rows.append(row)

    match_index_rows.sort(key=lambda r: (r.get("match_date") or "", r.get("match_id") or 0))
    team_match_rows.sort(key=lambda r: (r.get("match_date") or "", r.get("match_id") or 0, r.get("team") or ""))
    minute_rows.sort(key=lambda r: (r.get("match_date") or "", r.get("match_id") or 0, r.get("team") or "", r.get("period") or 0, r.get("minute") or 0))

    write_csv(GPT_UPLOAD_DIR / "match_index.csv", match_index_rows)
    write_csv(GPT_UPLOAD_DIR / "team_match_stats.csv", team_match_rows)
    write_csv(GPT_UPLOAD_DIR / "team_match_minute_stats.csv", minute_rows)
    write_text(GPT_UPLOAD_DIR / "README_FOR_GPT.md", build_readme(match_index_rows, team_match_rows, minute_rows))
    write_text(GPT_UPLOAD_DIR / "data_dictionary.md", build_data_dictionary())
    write_text(GPT_UPLOAD_DIR / "GPT_INSTRUCTIONS.md", build_gpt_instructions())

    print("Generated GPT upload files:")
    print(f"- match_index.csv: {len(match_index_rows)} rows")
    print(f"- team_match_stats.csv: {len(team_match_rows)} rows")
    print(f"- team_match_minute_stats.csv: {len(minute_rows)} rows")
    print("- README_FOR_GPT.md")
    print("- data_dictionary.md")
    print("- GPT_INSTRUCTIONS.md")


def main():
    build_gpt_data()


if __name__ == "__main__":
    main()
