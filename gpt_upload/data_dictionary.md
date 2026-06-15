# WorldCupStats Data Dictionary

## Metric definitions

### `goals`

Shot events where shot.outcome.name is Goal.

### `own_goals`

Own Goal Against events assigned to the team that scored against itself.

### `shots`

Shot events.

### `passes`

Pass events.

### `dribbles`

Dribble events.

### `fouls`

Foul Committed events.

### `yellow_cards`

Yellow Card and Second Yellow card events found in foul_committed or bad_behaviour.

### `red_cards`

Red Card and Second Yellow card events found in foul_committed or bad_behaviour.

### `corners`

Pass events where pass.type.name is Corner.

### `free_kicks`

Pass events where pass.type.name is Free Kick.

### `goal_kicks`

Pass events where pass.type.name is Goal Kick.

### `throw_ins`

Pass events where pass.type.name is Throw-in.

### `penalty_shots`

Shot events where shot.type.name is Penalty. Used as first-version proxy for penalty awarded.

### `offsides`

Offside events.

## Tables

### `match_index.csv`

One row per match. Use this for match metadata, match dates, teams, scores, stages, stadiums, referees, and match IDs.

### `team_match_stats.csv`

One row per team per match. Use this for whole-match analytics and last-X-games calculations.

### `team_match_minute_stats.csv`

One row per team, match, period, and minute where at least one tracked metric occurred. Use this for period/minute-range analysis.

## Notes and caveats

- `penalty_shots` is used as the first-version proxy for penalty awarded because it is directly identifiable from StatsBomb shot events.
- Minute-level data only contains rows where at least one tracked metric occurred.
- For last-X-games questions, sort rows by `match_date` descending and apply the limit separately per team.
- For whole-match questions, use `team_match_stats.csv`.
- For period or minute-range questions, use `team_match_minute_stats.csv`.
