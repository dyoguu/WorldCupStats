# WorldCupStats

A GitHub Pages dashboard focused on national-team competitions using StatsBomb Open Data.

## Current architecture

WorldCupStats uses a hybrid approach:

1. **Preprocessed analytics data**
   - GitHub Actions runs `scripts/build_data.py`.
   - The script generates analytical JSON files in `/data`.
   - The dashboard uses these files for fast filtering and averages.

2. **Direct raw event loading**
   - When the user opens a match detail, the frontend fetches the raw event file directly from StatsBomb Open Data.
   - This avoids storing all raw event files in this repo.

## Generated data files

The workflow generates:

- `data/competitions_national.json`
- `data/match_index.json`
- `data/team_match_stats.json`
- `data/team_match_minute_stats.json`
- `data/data_dictionary.json`

## Included functionality

- National-team competitions only
- Configurable competition list in `scripts/build_data.py`
- Multi-select filters with an `All` option
- Competition filter
- Season filter
- Team filter
- Last X games filter
- Period filter
- Minute start/end range
- Whole-match analytics
- Period/minute-range analytics
- Average metrics table
- KPI cards
- Team comparison table
- Match list used in the calculation
- Raw event explorer loaded directly from StatsBomb Open Data

## Manual data refresh

Go to:

Actions → Refresh StatsBomb Data → Run workflow

The workflow will run the Python script and commit updated files under `/data`.

## GitHub Pages

Recommended Pages setting:

Settings → Pages → Build and deployment → Source: Deploy from a branch

Branch: `main`
Folder: `/root`
