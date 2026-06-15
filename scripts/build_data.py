import json
import urllib.request
from pathlib import Path


STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data"


def fetch_json(url: str):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_competitions_national():
    competitions_url = f"{STATSBOMB_BASE_URL}/competitions.json"
    competitions = fetch_json(competitions_url)

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

    output_path = OUTPUT_DIR / "competitions_national.json"
    write_json(output_path, national_competitions)

    print(f"Generated {output_path}")
    print(f"Rows: {len(national_competitions)}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_competitions_national()


if __name__ == "__main__":
    main()
