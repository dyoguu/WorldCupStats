import json
import urllib.request
from collections import defaultdict
from pathlib import Path

STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data"

# National-team competitions only. Set to None to include every StatsBomb
# competition where competition_international is true.
INCLUDED_COMPETITIONS = {
    "FIFA World Cup",
    "UEFA Euro",
    "Copa America",
    "African Cup of Nations",
    "Women's World Cup",
    "UEFA Women's Euro",
    "FIFA U20 World Cup",
}

# Optional team filter. Leave as None to include every team.
INCLUDED_TEAMS = None

METRIC_KEYS = [
    "goals", "own_goals", "shots", "passes", "dribbles", "fouls",
    "yellow_cards", "red_cards", "corners", "free_kicks", "goal_kicks",
    "throw_ins", "penalty_shots", "offsides",
]


def fetch_json(url: str):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def safe_name(value):
    return value.get("name") if isinstance(value, dict) else value


def get_team_name_from_event(event):
    team = event.get("team")
    return team.get("name") if isinstance(team, dict) else None


def get_card_name(event):
    foul = event.get("foul_committed") or {}
    bad_behaviour = event.get("bad_behaviour") or {}
    card = foul.get("card") or bad_behaviour.get("card")
    return card.get("name") if isinstance(card, dict) else None


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
        if is_goal(event): updates.append("goals")
        if is_penalty_shot(event): updates.append("penalty_shots")

    elif event_type == "Pass":
        updates.append("passes")
        pass_data = event.get("pass") or {}
        pass_type = pass_data.get("type") or {}
        pass_type_name = pass_type.get("name")
        if pass_type_name == "Corner": updates.append("corners")
        elif pass_type_name == "Free Kick": updates.append("free_kicks")
        elif pass_type_name == "Goal Kick": updates.append("goal_kicks")
        elif pass_type_name == "Throw-in": updates.append("throw_ins")

    elif event_type == "Dribble":
        updates.append("dribbles")

    elif event_type == "Foul Committed":
        updates.append("fouls")
        card_name = get_card_name(event)
        if card_name in {"Yellow Card", "Second Yellow"}: updates.append("yellow_cards")
        if card_name in {"Red Card", "Second Yellow"}: updates.append("red_cards")

    elif event_type == "Bad Behaviour":
        card_name = get_card_name(event)
        if card_name in {"Yellow Card", "Second Yellow"}: updates.append("yellow_cards")
        if card_name in {"Red Card", "Second Yellow"}: updates.append("red_cards")

    elif event_type == "Offside":
        updates.append("offsides")

    elif event_type == "Own Goal Against":
        updates.append("own_goals")

    return updates


def calculate_team_match_stats(events, home_team, away_team):
    stats = defaultdict(build_empty_stats)
    stats[home_team]
    stats[away_team]
    for event in events:
        team_name = get_team_name_from_event(event)
        if not team_name: continue
        for metric in event_to_metric_updates(event):
            stats[team_name][metric] += 1
    return stats


def calculate_team_match_minute_stats(events):
    minute_stats = {}
    for event in events:
        team_name = get_team_name_from_event(event)
        if not team_name: continue
        period = event.get("period")
        minute = event.get("minute")
        if period is None or minute is None: continue
        key = (team_name, int(period), int(minute))
        if key not in minute_stats:
            minute_stats[key] = {"team": team_name, "period": int(period), "minute": int(minute), **build_empty_stats()}
        for metric in event_to_metric_updates(event):
            minute_stats[key][metric] += 1
    return list(minute_stats.values())


def team_allowed(home_team, away_team):
    if INCLUDED_TEAMS is None:
        return True
    return home_team in INCLUDED_TEAMS or away_team in INCLUDED_TEAMS


def build_data():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    competitions = fetch_json(f"{STATSBOMB_BASE_URL}/competitions.json")

    national_competitions = [
        {
            "competition_id": c.get("competition_id"),
            "season_id": c.get("season_id"),
            "competition_name": c.get("competition_name"),
            "season_name": c.get("season_name"),
            "country_name": c.get("country_name"),
            "competition_gender": c.get("competition_gender"),
            "competition_youth": c.get("competition_youth"),
            "competition_international": c.get("competition_international"),
            "match_available": c.get("match_available"),
            "match_available_360": c.get("match_available_360"),
        }
        for c in competitions
        if c.get("competition_international") is True
    ]

    national_competitions.sort(key=lambda row: (row.get("competition_name") or "", row.get("season_name") or ""))

    if INCLUDED_COMPETITIONS is None:
        selected_competitions = national_competitions
    else:
        selected_competitions = [c for c in national_competitions if c.get("competition_name") in INCLUDED_COMPETITIONS]

    match_index = []
    team_match_stats = []
    team_match_minute_stats = []

    for competition in selected_competitions:
        competition_id = competition["competition_id"]
        season_id = competition["season_id"]
        print(f"Loading matches: {competition['competition_name']} {competition['season_name']} ({competition_id}/{season_id})")
        matches_url = f"{STATSBOMB_BASE_URL}/matches/{competition_id}/{season_id}.json"
        try:
            matches = fetch_json(matches_url)
        except Exception as exc:
            print(f"Could not load matches from {matches_url}: {exc}")
            continue

        for match in matches:
            match_id = match.get("match_id")
            home_team = (match.get("home_team") or {}).get("home_team_name")
            away_team = (match.get("away_team") or {}).get("away_team_name")
            if not match_id or not home_team or not away_team: continue
            if not team_allowed(home_team, away_team): continue

            match_record = {
                "match_id": match_id,
                "competition_id": competition_id,
                "season_id": season_id,
                "competition_name": competition.get("competition_name"),
                "season_name": competition.get("season_name"),
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
            match_index.append(match_record)

            try:
                events = fetch_json(f"{STATSBOMB_BASE_URL}/events/{match_id}.json")
            except Exception as exc:
                print(f"Could not load events for match {match_id}: {exc}")
                continue

            stats_by_team = calculate_team_match_stats(events, home_team, away_team)
            minute_rows = calculate_team_match_minute_stats(events)

            for minute_row in minute_rows:
                row = {
                    "match_id": match_id,
                    "competition_id": competition_id,
                    "season_id": season_id,
                    "competition_name": competition.get("competition_name"),
                    "season_name": competition.get("season_name"),
                    "match_date": match.get("match_date"),
                }
                row.update(minute_row)
                team_match_minute_stats.append(row)

            for team_name in [home_team, away_team]:
                opponent_name = away_team if team_name == home_team else home_team
                row = {
                    "match_id": match_id,
                    "competition_id": competition_id,
                    "season_id": season_id,
                    "competition_name": competition.get("competition_name"),
                    "season_name": competition.get("season_name"),
                    "match_date": match.get("match_date"),
                    "team": team_name,
                    "opponent": opponent_name,
                    "home_away": "home" if team_name == home_team else "away",
                }
                row.update(stats_by_team[team_name])
                team_match_stats.append(row)

    match_index.sort(key=lambda row: (row.get("match_date") or "", row.get("match_id") or 0))
    team_match_stats.sort(key=lambda row: (row.get("match_date") or "", row.get("match_id") or 0, row.get("team") or ""))
    team_match_minute_stats.sort(key=lambda row: (row.get("match_date") or "", row.get("match_id") or 0, row.get("team") or "", row.get("period") or 0, row.get("minute") or 0))

    data_dictionary = {
        "metric_definitions": {
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
            "penalty_shots": "Shot events where shot.type.name is Penalty. Used as first version proxy for penalty awarded.",
            "offsides": "Offside events.",
        },
        "notes": [
            "Penalty shots are used instead of penalty awarded because they are directly identifiable from StatsBomb shot events.",
            "Minute-level data contains only rows where at least one tracked metric exists.",
            "Raw event-level match detail is loaded directly from StatsBomb Open Data by the frontend.",
        ],
    }

    write_json(OUTPUT_DIR / "competitions_national.json", national_competitions)
    write_json(OUTPUT_DIR / "match_index.json", match_index)
    write_json(OUTPUT_DIR / "team_match_stats.json", team_match_stats)
    write_json(OUTPUT_DIR / "team_match_minute_stats.json", team_match_minute_stats)
    write_json(OUTPUT_DIR / "data_dictionary.json", data_dictionary)

    print("Generated data files:")
    print(f"- competitions_national.json: {len(national_competitions)} rows")
    print(f"- match_index.json: {len(match_index)} rows")
    print(f"- team_match_stats.json: {len(team_match_stats)} rows")
    print(f"- team_match_minute_stats.json: {len(team_match_minute_stats)} rows")
    print("- data_dictionary.json")


if __name__ == "__main__":
    build_data()
