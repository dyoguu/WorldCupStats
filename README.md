# WorldCupStats

A GitHub Pages dashboard focused on national-team competitions using StatsBomb Open Data.

## Architecture

- GitHub Pages serves the static web app.
- GitHub Actions runs `scripts/build_data.py`.
- The script generates analytical JSON files in `/data`.
- The dashboard consumes the generated `/data/*.json` files.
- Detailed match/event analysis can later fetch raw event files directly from StatsBomb Open Data.

## First version

This starter version generates:

- `data/competitions_national.json`

Then `index.html` loads that file and displays the available national competition/season rows.

## Manual data refresh

Go to:

Actions → Refresh StatsBomb Data → Run workflow

The workflow will run the Python script and commit updated files under `/data`.

## GitHub Pages

Recommended Pages setting:

Settings → Pages → Build and deployment → Source: Deploy from a branch

Branch: `main`
Folder: `/root`
