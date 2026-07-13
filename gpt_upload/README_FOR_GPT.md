# WorldCupStats GPT Upload Package

This folder is generated independently from StatsBomb Open Data.

It does not depend on the website JSON files under `/data`.

Use these files as the source of truth for a Custom GPT focused on national-team football analytics.

## Files

### `match_index.csv`

One row per match.

Use for match metadata, competition filters, season filters, match dates, scores, stages, stadiums, referees, and match IDs.

Rows: 512

### `team_match_stats.csv`

One row per team per match.

Use for whole-match analytics, team comparisons, last-X-games analysis, and average metrics.

Rows: 1024

### `team_match_minute_stats.csv`

One row per team, match, period, and minute where at least one tracked metric occurred.

Use for period and minute-range questions.

Rows: 101306

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
