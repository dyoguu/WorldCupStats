import json
import urllib.request
from collections import defaultdict
from pathlib import Path


STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data"

# First analytics version.
# Keep this list small while we validate the metric logic.
# Later we can expand it to all international competitions.
INCLUDED_COMPETITIONS = {
    "FIFA World Cup",
}


def fetch_json(url: str):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


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


def increment_metric(stats, team_name, metric, value=1):
    if team_name:
        stats[team_name][metric] += value


def build_empty_stats():
    return {
        "goals": 0,
        "own_goals": 0,
        "shots": 0,
        "passes": 0,
        "dribbles": 0,
        "fouls": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "corners": 0,
        "free_kicks": 0,
        "goal_kicks": 0,
        "throw_ins": 0,
        "penalty_shots": 0,
        "offsides": 0,
    }


def calculate_team_match_stats(events, home_team, away_team):
    stats = defaultdict(build_empty_stats)

    # Ensure both teams exist even if one team has zero values for a metric.
    stats[home_team]
    stats[away_team]

    for event in events:
        event_type = safe_name(event.get("type"))
        team_name = get_team_name_from_event(event)

        if not team_name:
            continue

        if event_type == "Shot":
            increment_metric(stats, team_name, "shots")

            if is_goal(event):
                increment_metric(stats, team_name, "goals")

            if is_penalty_shot(event):
                increment_metric(stats, team_name, "penalty_shots")

        elif event_type == "Pass":
            increment_metric(stats, team_name, "passes")

            pass_data = event.get("pass") or {}
            pass_type = pass_data.get("type") or {}
            pass_type_name = pass_type.get("name")

            if pass_type_name == "Corner":
                increment_metric(stats, team_name, "corners")
            elif pass_type_name == "Free Kick":
                increment_metric(stats, team_name, "free_kicks")
            elif pass_type_name == "Goal Kick":
                increment_metric(stats, team_name, "goal_kicks")
            elif pass_type_name == "Throw-in":
                increment_metric(stats, team_name, "throw_ins")

        elif event_type == "Dribble":
            increment_metric(stats, team_name, "dribbles")

        elif event_type == "Foul Committed":
            increment_metric(stats, team_name, "fouls")

            card_name = get_card_name(event)

            if card_name in {"Yellow Card", "Second Yellow"}:
                increment_metric(stats, team_name, "yellow_cards")

            if card_name in {"Red Card", "Second Yellow"}:
                increment_metric(stats, team_name, "red_cards")

        elif event_type == "Bad Behaviour":
            card_name = get_card_name(event)

            if card_name in {"Yellow Card", "Second Yellow"}:
                increment_metric(stats, team_name, "yellow_cards")

            if card_name in {"Red Card", "Second Yellow"}:
                increment_metric(stats, team_name, "red_cards")

        elif event_type == "Offside":
            increment_metric(stats, team_name, "offsides")

        elif event_type == "Own Goal Against":
            # This event is assigned to the team that scored against itself.
            increment_metric(stats, team_name, "own_goals")

    return stats


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

    national_competitions.sort(
        key=lambda row: (
            row.get("competition_name") or "",
            row.get("season_name") or "",
        )
    )

    selected_competitions = [
        c
        for c in national_competitions
        if c.get("competition_name") in INCLUDED_COMPETITIONS
    ]

    match_index = []
    team_match_stats = []

    for competition in selected_competitions:
        competition_id = competition["competition_id"]
        season_id = competition["season_id"]

        print(
            f"Loading matches: {competition['competition_name']} "
            f"{competition['season_name']} "
            f"({competition_id}/{season_id})"
        )

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

            if not match_id or not home_team or not away_team:
                continue

            stage = (match.get("competition_stage") or {}).get("name")
            stadium = (match.get("stadium") or {}).get("name")
            referee = (match.get("referee") or {}).get("name")

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
                "stage": stage,
                "stadium": stadium,
                "referee": referee,
                "event_source_url": f"{STATSBOMB_BASE_URL}/events/{match_id}.json",
            }

            match_index.append(match_record)

            events_url = f"{STATSBOMB_BASE_URL}/events/{match_id}.json"

            try:
                events = fetch_json(events_url)
            except Exception as exc:
                print(f"Could not load events for match {match_id}: {exc}")
                continue

            stats_by_team = calculate_team_match_stats(events, home_team, away_team)

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
                team_match_stats.append(row)

    match_index.sort(
        key=lambda row: (
            row.get("match_date") or "",
            row.get("match_id") or 0,
        )
    )

    team_match_stats.sort(
        key=lambda row: (
            row.get("match_date") or "",
            row.get("match_id") or 0,
            row.get("team") or "",
        )
    )

    write_json(OUTPUT_DIR / "competitions_national.json", national_competitions)
    write_json(OUTPUT_DIR / "match_index.json", match_index)
    write_json(OUTPUT_DIR / "team_match_stats.json", team_match_stats)

    print("Generated data files:")
    print(f"- competitions_national.json: {len(national_competitions)} rows")
    print(f"- match_index.json: {len(match_index)} rows")
    print(f"- team_match_stats.json: {len(team_match_stats)} rows")


def main():
    build_data()


if __name__ == "__main__":
    main()
